"""omarchy-key-remap — remap keys and shortcuts on Omarchy, system-wide or per app.

    omarchy-key-remap                      the menu
    omarchy-key-remap add capslock esc     one remap, applied straight away
    omarchy-key-remap add ctrl+w noop --app chromium
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys

from . import __version__, keydconf, menu, privileged
from .config import CONFIG_FILE, KEYD_CONF, Config
from .keydconf import Remap
from .keys import COMMON_KEYS, KeyError_, describe, valid_keys

ICONS = {"key": "", "app": "", "add": "", "remove": "",
         "status": "", "off": ""}


# ---------------------------------------------------------------- applying

def apply(cfg: Config, quiet: bool = False) -> int:
    """Write the global remaps to keyd's config and reload it."""
    text = keydconf.generate(cfg.globals(), cfg.ids)
    try:
        privileged.install(text)
    except privileged.PrivilegeError as e:
        menu.notify("Key remap", str(e).splitlines()[0])
        print(f"omarchy-key-remap: {e}", file=sys.stderr)
        return 1
    if cfg.per_app():
        restart_watcher()
    if not quiet:
        n, a = len(cfg.globals()), len(cfg.per_app())
        print(f"Applied: {n} global remap{'s' if n != 1 else ''}"
              + (f", {a} per-app" if a else ""))
    return 0


def restart_watcher() -> None:
    """The per-app watcher holds the remaps in memory; a change means a restart."""
    if shutil.which("systemctl") is None:
        return
    subprocess.run(["systemctl", "--user", "restart", "omarchy-key-remap-apps.service"],
                   capture_output=True, check=False)


# ---------------------------------------------------------------- commands

def cmd_add(args) -> int:
    cfg = Config()
    remap = Remap(source=args.source, action=args.action, app=args.app, note=args.note or "")
    try:
        old = cfg.add(remap)
    except KeyError_ as e:
        print(f"omarchy-key-remap: {e}", file=sys.stderr)
        return 2
    cfg.save()
    where = f" in {remap.app}" if remap.app else ""
    if old:
        print(f"{describe(remap.source)} → {remap.action}{where} (was {old.action})")
    else:
        print(f"{describe(remap.source)} → {remap.action}{where}")
    return apply(cfg)


def cmd_remove(args) -> int:
    cfg = Config()
    gone = cfg.remove(args.source, args.app)
    if gone is None:
        print(f"omarchy-key-remap: {args.source} is not remapped"
              + (f" in {args.app}" if args.app else ""), file=sys.stderr)
        return 1
    cfg.save()
    print(f"Removed {describe(gone.source)} → {gone.action}")
    return apply(cfg)


def cmd_list(args) -> int:
    cfg = Config()
    if not cfg.remaps:
        print("No remaps yet. Add one with `omarchy-key-remap add <key> <action>`.")
        return 0
    width = max(len(describe(r.source)) for r in cfg.remaps)
    for r in cfg.remaps:
        where = f"   [{r.app}]" if r.app else ""
        note = f"   # {r.note}" if r.note else ""
        print(f"{describe(r.source):<{width}}  →  {r.action}{where}{note}")
    return 0


def cmd_apply(args) -> int:
    return apply(Config())


def cmd_clear(args) -> int:
    """Turn every remap off without forgetting them."""
    cfg = Config()
    text = keydconf.generate([], cfg.ids)
    try:
        privileged.install(text)
    except privileged.PrivilegeError as e:
        print(f"omarchy-key-remap: {e}", file=sys.stderr)
        return 1
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "stop", "omarchy-key-remap-apps.service"],
                       capture_output=True, check=False)
    print(f"All remaps are off. They are still in {CONFIG_FILE}; "
          f"`omarchy-key-remap apply` brings them back.")
    return 0


def cmd_status(args) -> int:
    cfg = Config()
    state = privileged.service_state()
    print(f"keyd                {'installed' if privileged.keyd_installed() else 'NOT INSTALLED'}"
          f"   ({state['active']}, {state['enabled']})")
    print(f"remaps              {len(cfg.globals())} global, {len(cfg.per_app())} per-app")
    print(f"config              {CONFIG_FILE}")
    print(f"keyd config         {KEYD_CONF}", end="")
    try:
        with open(KEYD_CONF, encoding="utf-8") as f:
            print("   (ours)" if privileged.MARKER in f.read() else "   (NOT ours — "
                  "apply would back it up first)")
    except OSError:
        print("   (missing)")
    if cfg.per_app():
        r = subprocess.run(["systemctl", "--user", "is-active", "omarchy-key-remap-apps.service"],
                           capture_output=True, check=False)
        print(f"per-app watcher     {r.stdout.decode().strip() or 'unknown'}")
        group = "yes" if privileged.in_keyd_group() else "NO — run `omarchy-key-remap setup`"
        print(f"keyd group          {group}")
    ok, message = privileged.check(keydconf.generate(cfg.globals(), cfg.ids))
    print(f"generated config    {'valid' if ok else 'INVALID: ' + message}")
    return 0


def cmd_keys(args) -> int:
    keys = sorted(valid_keys())
    if args.source:                                   # used as a filter
        keys = [k for k in keys if args.source.lower() in k.lower()]
    print(" ".join(keys))
    return 0


def cmd_setup(args) -> int:
    """Everything that needs doing once: the service, the group, the user unit."""
    if not privileged.keyd_installed():
        print("keyd is not installed. On Omarchy:  sudo pacman -S keyd", file=sys.stderr)
        return 1
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    try:
        privileged.enable_service(add_to_group=user or None)
    except privileged.PrivilegeError as e:
        print(f"omarchy-key-remap: {e}", file=sys.stderr)
        return 1
    print("keyd is enabled and running.")
    if user:
        print(f"{user} was added to the keyd group — log out and back in for per-app remaps.")

    cfg = Config()
    if cfg.per_app() and shutil.which("systemctl"):
        subprocess.run(["systemctl", "--user", "enable", "--now",
                        "omarchy-key-remap-apps.service"], capture_output=True, check=False)
    return apply(cfg) if cfg.remaps else 0


def cmd_watch(args) -> int:
    """The per-app daemon. Run by omarchy-key-remap-apps.service, not by hand."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from .hypr import Watcher
    cfg = Config()
    if not cfg.per_app():
        logging.info("no per-app remaps configured; nothing to watch")
        return 0
    logging.info("%d per-app remap(s) across %s", len(cfg.per_app()),
                 ", ".join(keydconf.apps(cfg.per_app())))
    Watcher(cfg.per_app()).run()
    return 0


def cmd_capture(args) -> int:
    """Print the next key pressed, the way PowerToys' "Type the key" box works."""
    if not privileged.keyd_installed():
        print("omarchy-key-remap: keyd is not installed", file=sys.stderr)
        return 1
    print("Press the key…", file=sys.stderr)
    try:
        proc = subprocess.Popen(["keyd", "monitor"], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except OSError as e:
        print(f"omarchy-key-remap: {e}", file=sys.stderr)
        return 1
    try:
        for raw in proc.stdout:                       # "<device>\t<key> down"
            line = raw.decode("utf-8", "replace").strip()
            parts = line.split("\t")[-1].split()
            if len(parts) >= 2 and parts[-1] == "down":
                print(parts[0])
                return 0
    finally:
        proc.terminate()
    return 1


# ---------------------------------------------------------------- the menu

def cmd_menu(args) -> int:
    cfg = Config()
    rows = [
        (ICONS["add"], "Remap a key", "Add · one key becomes another"),
        (ICONS["add"], "Remap a shortcut", "Add · a combination becomes another"),
        (ICONS["app"], "Remap inside one app", "Add · only while that window has focus"),
    ]
    if cfg.remaps:
        rows.append((ICONS["remove"], "Remove a remap", f"Manage · {len(cfg.remaps)} configured"))
    rows.append((ICONS["status"], "Show the remaps", "Manage · what is active right now"))
    if cfg.remaps:
        rows.append((ICONS["off"], "Turn every remap off", "Manage · keeps them for later"))

    pick = menu.select("Key remap", rows, width=640)
    if not pick:
        return 1
    label = pick.split("\t")[0]
    if label == "Remap a key":
        return menu_add(cfg, shortcut=False, app=None)
    if label == "Remap a shortcut":
        return menu_add(cfg, shortcut=True, app=None)
    if label == "Remap inside one app":
        app = menu.ask("Window class (the app's class in `hyprctl clients`)")
        if not app:
            return 1
        return menu_add(cfg, shortcut=True, app=app)
    if label == "Remove a remap":
        return menu_remove(cfg)
    if label == "Show the remaps":
        rows = [(ICONS["key"], describe(r.source), f"{r.action}" + (f" · {r.app}" if r.app else ""))
                for r in cfg.remaps] or [(ICONS["status"], "Nothing remapped", "Add one first")]
        menu.select("Remaps", rows, width=640)
        return 0
    if label == "Turn every remap off":
        return cmd_clear(args)
    return 1


def menu_add(cfg: Config, shortcut: bool, app: str | None) -> int:
    prompt = "Which shortcut? (e.g. ctrl+shift+c)" if shortcut else "Which key?"
    source = (menu.ask(prompt) if shortcut
              else pick_key("Which key do you want to change?"))
    if not source:
        return 1
    action = menu.ask(f"{describe(source)} should do what? (a key, C-c, or macro(...))")
    if not action:
        return 1
    args = argparse.Namespace(source=source, action=action, app=app, note="")
    rc = cmd_add(args)
    if rc == 0:
        menu.notify("Key remap", f"{describe(source)} → {action}"
                    + (f" in {app}" if app else ""))
    return rc


def pick_key(prompt: str) -> str | None:
    rows = [(ICONS["key"], k, "key") for k in COMMON_KEYS]
    pick = menu.select(prompt, rows, width=520)
    return pick.split("\t")[0] if pick else None


def menu_remove(cfg: Config) -> int:
    rows = [(ICONS["key"], describe(r.source), f"{r.action}" + (f" · {r.app}" if r.app else ""))
            for r in cfg.remaps]
    pick = menu.select("Remove which remap?", rows, width=640)
    if not pick:
        return 1
    label = pick.split("\t")[0]
    for r in cfg.remaps:
        if describe(r.source) == label:
            return cmd_remove(argparse.Namespace(source=r.source, app=r.app))
    return 1


# ---------------------------------------------------------------- entry point

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="omarchy-key-remap",
        description="Remap keys and shortcuts on Omarchy, system-wide or inside one app.",
        epilog="With no command, the Omarchy menu opens.")
    p.add_argument("command", nargs="?",
                   help="add, remove, list, apply, clear, status, keys, capture, setup, watch")
    p.add_argument("source", nargs="?", help="the key or combination to change")
    p.add_argument("action", nargs="?", help="what it should do instead")
    p.add_argument("--app", help="only while a window of this class has focus")
    p.add_argument("--note", help="a reminder of why, kept with the remap")
    p.add_argument("-V", "--version", action="version", version=f"omarchy-key-remap {__version__}")
    args = p.parse_args(argv)

    commands = {"add": cmd_add, "remove": cmd_remove, "list": cmd_list, "apply": cmd_apply,
                "clear": cmd_clear, "status": cmd_status, "keys": cmd_keys,
                "capture": cmd_capture, "setup": cmd_setup, "watch": cmd_watch}
    if args.command is None:
        return cmd_menu(args)
    if args.command not in commands:
        print(f"omarchy-key-remap: unknown command {args.command!r}", file=sys.stderr)
        return 2
    if args.command == "add" and not (args.source and args.action):
        print("Usage: omarchy-key-remap add <key> <action> [--app CLASS]", file=sys.stderr)
        return 2
    if args.command == "remove" and not args.source:
        print("Usage: omarchy-key-remap remove <key> [--app CLASS]", file=sys.stderr)
        return 2
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
