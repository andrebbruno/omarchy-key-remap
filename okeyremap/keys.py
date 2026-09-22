"""Key names, modifiers and the parsing of what the user typed.

keyd's own vocabulary is the source of truth: KEYD_KEYS below is `keyd list-keys`
as of keyd 2.6, and when keyd is installed the live list is preferred over it.
"""
from __future__ import annotations

import functools
import shutil
import subprocess

# Filled in from `keyd list-keys`; see tools/refresh_keys.py.
KEYD_KEYS: tuple[str, ...] = (
    'esc', 'escape', '1', '!', '2', '@', '3', '#', '4', '$', '5', '%', '6', '^', '7', '&',
    '8', '*', '9', '(', '0', ')', '-', 'minus', '_', '=', 'equal', '+', 'backspace', 'tab',
    'q', 'Q', 'w', 'W', 'e', 'E', 'r', 'R', 't', 'T', 'y', 'Y', 'u', 'U', 'i', 'I', 'o', 'O',
    'p', 'P', '[', 'leftbrace', '{', ']', 'rightbrace', '}', 'enter', 'leftcontrol', 'a', 'A',
    's', 'S', 'd', 'D', 'f', 'F', 'g', 'G', 'h', 'H', 'j', 'J', 'k', 'K', 'l', 'L', ';',
    'semicolon', ':', "'", 'apostrophe', '"', '`', 'grave', '~', 'leftshift', '\\',
    'backslash', '|', 'z', 'Z', 'x', 'X', 'c', 'C', 'v', 'V', 'b', 'B', 'n', 'N', 'm', 'M',
    ',', 'comma', '<', '.', 'dot', '>', '/', 'slash', '?', 'rightshift', 'kpasterisk',
    'leftalt', 'space', 'capslock', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
    'f10', 'numlock', 'scrolllock', 'kp7', 'kp8', 'kp9', 'kpminus', 'kp4', 'kp5', 'kp6',
    'kpplus', 'kp1', 'kp2', 'kp3', 'kp0', 'kpdot', 'iso-level3-shift', 'zenkakuhankaku',
    '102nd', 'f11', 'f12', 'ro', 'katakana', 'hiragana', 'henkan', 'katakanahiragana',
    'muhenkan', 'kpjpcomma', 'kpenter', 'rightcontrol', 'kpslash', 'sysrq', 'rightalt',
    'linefeed', 'home', 'up', 'pageup', 'left', 'right', 'end', 'down', 'pagedown', 'insert',
    'delete', 'macro', 'mute', 'volumedown', 'volumeup', 'power', 'kpequal', 'kpplusminus',
    'pause', 'scale', 'kpcomma', 'hangeul', 'hanja', 'yen', 'leftmeta', 'rightmeta',
    'compose', 'stop', 'again', 'props', 'undo', 'front', 'copy', 'open', 'paste', 'find',
    'cut', 'help', 'menu', 'calc', 'setup', 'sleep', 'wakeup', 'file', 'sendfile',
    'deletefile', 'xfer', 'scrolldown', 'scrollup', 'www', 'msdos', 'coffee', 'display',
    'cyclewindows', 'mail', 'favorites', 'bookmarks', 'computer', 'back', 'forward',
    'closecd', 'ejectcd', 'ejectclosecd', 'nextsong', 'playpause', 'previoussong', 'stopcd',
    'record', 'rewind', 'phone', 'iso', 'config', 'homepage', 'refresh', 'exit', 'move',
    'edit', 'zoom', 'mouseback', 'kpleftparen', 'kprightparen', 'new', 'redo', 'f13', 'f14',
    'f15', 'f16', 'f17', 'f18', 'f19', 'f20', 'f21', 'prog1', 'f22', 'prog2', 'f23', 'prog3',
    'f24', 'prog4', 'noop', 'playcd', 'pausecd', 'scrollleft', 'scrollright', 'dashboard',
    'suspend', 'close', 'play', 'fastforward', 'bassboost', 'print', 'hp', 'camera', 'sound',
    'question', 'email', 'chat', 'search', 'connect', 'finance', 'sport', 'shop',
    'voicecommand', 'cancel', 'brightnessdown', 'brightnessup', 'media', 'switchvideomode',
    'kbdillumtoggle', 'kbdillumdown', 'kbdillumup', 'send', 'reply', 'forwardmail', 'save',
    'documents', 'battery', 'bluetooth', 'wlan', 'uwb', 'unknown', 'next', 'prev', 'cycle',
    'auto', 'off', 'wwan', 'rfkill', 'micmute', 'leftmouse', 'middlemouse', 'rightmouse',
    'mouse1', 'mouse2', 'fn', 'mouseforward',
)

# keyd's modifier layers. The values on the right are what a layer is called in a
# config section; everything on the left is what a person is likely to type.
MODIFIER_ALIASES = {
    "ctrl": "control", "control": "control", "ctl": "control",
    "shift": "shift",
    "alt": "alt", "option": "alt", "opt": "alt",
    "meta": "meta", "super": "meta", "win": "meta", "windows": "meta",
    "cmd": "meta", "command": "meta", "mod": "meta",
    "altgr": "altgr", "rightalt": "altgr",
}
MODIFIER_ORDER = ("control", "shift", "alt", "meta", "altgr")

# What a modifier looks like on the right-hand side, as a chord prefix.
CHORD_PREFIX = {"control": "C", "shift": "S", "alt": "A", "meta": "M", "altgr": "G"}

# keyd actions that take arguments. The contents are keyd's business — `keyd check`
# has the final word — but the name and the parentheses are checked here so a typo
# is caught before anything touches /etc.
ACTIONS = {"macro", "command", "layer", "layerm", "oneshot", "oneshotm", "overload",
           "overloadt", "overloadt2", "overloadi", "toggle", "togglem", "setlayout",
           "clear", "clearm", "swap", "swapm", "timeout", "noop"}

# The keys worth showing in a menu, in the order someone would look for them.
COMMON_KEYS = (
    "capslock", "esc", "tab", "backspace", "enter", "space", "delete", "insert",
    "leftcontrol", "rightcontrol", "leftshift", "rightshift", "leftalt", "rightalt",
    "leftmeta", "rightmeta", "compose", "menu",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    *(f"f{n}" for n in range(1, 13)),
    *"abcdefghijklmnopqrstuvwxyz",
    *(str(n) for n in range(10)),
    "minus", "equal", "leftbrace", "rightbrace", "semicolon", "apostrophe",
    "grave", "backslash", "comma", "dot", "slash",
    "print", "scrolllock", "pause", "numlock",
    "volumeup", "volumedown", "mute", "micmute",
    "brightnessup", "brightnessdown",
    "playpause", "nextsong", "previoussong", "stopcd",
)


class KeyError_(ValueError):
    """A key name or combination that keyd would not understand."""


@functools.lru_cache(maxsize=1)
def valid_keys() -> frozenset[str]:
    """Every key name keyd accepts — asked of keyd itself when it is installed."""
    if shutil.which("keyd"):
        try:
            r = subprocess.run(["keyd", "list-keys"], capture_output=True, timeout=5, check=False)
            live = {line.strip() for line in r.stdout.decode("utf-8", "replace").splitlines()
                    if line.strip()}
            if len(live) > 50:                      # sanity: a real list, not an error message
                return frozenset(live)
        except (OSError, subprocess.SubprocessError):
            pass
    return frozenset(KEYD_KEYS)


def parse_combo(text: str) -> tuple[tuple[str, ...], str]:
    """"ctrl+shift+c" -> (("control", "shift"), "c").

    Modifiers come back in keyd's own order, deduplicated, so that two spellings of
    the same combination produce the same layer and cannot both be stored.
    """
    raw = (text or "").strip()
    if not raw:
        raise KeyError_("no key given")
    parts = [p.strip().lower() for p in raw.replace("-", "+").split("+") if p.strip()]

    # A trailing "+" or "-" is the key itself, not a separator: "ctrl+-" and a bare
    # "-" both end up with nothing after the last separator.
    if raw.endswith(("+", "-")):
        parts.append("minus" if raw.endswith("-") else "equal")
    if not parts:
        raise KeyError_(f"cannot read {text!r}")

    *mods, key = parts
    seen: list[str] = []
    for m in mods:
        name = MODIFIER_ALIASES.get(m)
        if name is None:
            raise KeyError_(f"{m!r} is not a modifier (use ctrl, shift, alt or super)")
        if name not in seen:
            seen.append(name)
    if key in MODIFIER_ALIASES and not mods:
        # "ctrl" alone: they mean the physical key, which keyd calls leftcontrol.
        key = {"control": "leftcontrol", "shift": "leftshift", "alt": "leftalt",
               "meta": "leftmeta", "altgr": "rightalt"}[MODIFIER_ALIASES[key]]
    keys = valid_keys()
    if keys and key not in keys:
        raise KeyError_(f"{key!r} is not a key name keyd knows (try `omarchy-key-remap keys`)")
    order = {m: i for i, m in enumerate(MODIFIER_ORDER)}
    return tuple(sorted(seen, key=lambda m: order[m])), key


def layer_for(mods: tuple[str, ...]) -> str:
    """The keyd section a combination belongs in: [main], [control], [control+alt]…"""
    return "+".join(mods) if mods else "main"


def canonical(text: str) -> str:
    """The one spelling of a combination that gets stored, so duplicates collide."""
    mods, key = parse_combo(text)
    return "+".join((*mods, key))


def validate_action(text: str) -> str:
    """Check the right-hand side as far as is safe without keyd; `keyd check` does the rest."""
    action = (text or "").strip()
    if not action:
        raise KeyError_("no action given")
    if action.count("(") != action.count(")"):
        raise KeyError_(f"unbalanced parentheses in {action!r}")

    head = action.split("(", 1)[0].strip()
    if "(" in action:
        if head not in ACTIONS:
            raise KeyError_(f"{head!r} is not a keyd action "
                            f"(macro, command, layer, oneshot, overload, toggle…)")
        return action

    # A plain key, or a chord such as C-c / M-S-v.
    bare = action
    while len(bare) > 2 and bare[0] in "CSAMG" and bare[1] == "-":
        bare = bare[2:]
    keys = valid_keys()
    if keys and bare not in keys and action not in ACTIONS:
        raise KeyError_(f"{bare!r} is not a key name keyd knows "
                        f"(a chord looks like C-c, a command like command(...))")
    return action


def describe(combo: str) -> str:
    """A combination written the way a person reads it: "ctrl+shift+c" -> "Ctrl + Shift + C"."""
    try:
        mods, key = parse_combo(combo)
    except KeyError_:
        return combo
    pretty = {"control": "Ctrl", "shift": "Shift", "alt": "Alt", "meta": "Super", "altgr": "AltGr"}
    parts = [pretty[m] for m in mods]
    parts.append(key.upper() if len(key) == 1 else key.capitalize())
    return " + ".join(parts)
