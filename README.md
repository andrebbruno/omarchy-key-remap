# Key Remap for Omarchy

Remap keys and shortcuts on [Omarchy](https://omarchy.org) — system-wide, or only inside one
app. A port of what [PowerToys Keyboard Manager](https://learn.microsoft.com/windows/powertoys/keyboard-manager)
does, built on [keyd](https://github.com/rvaiya/keyd), with the per-app half wired straight
into Hyprland.

*[Leia em português](README.pt-BR.md)*

```bash
omarchy-key-remap add capslock esc              # the classic
omarchy-key-remap add ctrl+w noop --app chromium  # stop closing that tab by accident
omarchy-key-remap                                # or just open the menu
```

## Why keyd, and why this on top

keyd remaps at the kernel's input layer, which is the only place on Linux where a remap works
*everywhere*: Wayland, X11, the TTY, the lock screen, games. What it does not have is a way in
for someone who does not want to learn its config file — and, on Hyprland, no per-app support
at all (keyd's own application mapper only speaks X11 and GNOME).

This fills both gaps:

- **A menu and a CLI** instead of `/etc/keyd/default.conf`. Your remaps live in
  `~/.config/omarchy-key-remap/remaps.json` and the keyd config is generated from them.
- **Per-app remaps on Hyprland.** A small watcher follows the compositor's own focus events
  and hands keyd the bindings for whatever window you are in — and, just as importantly,
  takes them away when you leave it.
- **Nothing is written that keyd has not accepted.** Every generated config goes through
  `keyd check` before it is installed, and a `default.conf` that was not written by this tool
  is backed up first.

## What you can remap

| | Example |
|---|---|
| A key | `omarchy-key-remap add capslock esc` |
| A shortcut | `omarchy-key-remap add ctrl+shift+c C-insert` |
| A key to a chord | `omarchy-key-remap add f13 M-v` |
| A key to a sequence | `omarchy-key-remap add f5 'macro(C-s C-r)'` |
| A key to a command | `omarchy-key-remap add f12 'command(omarchy-menu)'` |
| Nothing at all | `omarchy-key-remap add ctrl+w noop --app chromium` |
| Hold vs tap | `omarchy-key-remap add capslock 'overload(control, esc)'` |

Modifiers can be written the way you think of them — `ctrl`, `super`, `win`, `cmd`, `option` —
and are normalised to keyd's own names. The right-hand side is keyd's action language: a key,
a chord (`C-c`, `M-S-v`), or one of `macro()`, `command()`, `layer()`, `oneshot()`,
`overload()`, `toggle()`, `noop`. `man keyd` has the full list.

## Install

### Arch / Omarchy

```bash
sudo pacman -U omarchy-key-remap-*-any.pkg.tar.zst   # from Releases
omarchy-key-remap setup
```

`setup` enables the keyd service and adds you to the `keyd` group (needed for per-app remaps —
log out and back in once). Then:

```bash
omarchy-key-remap add capslock esc
systemctl --user enable --now omarchy-key-remap-apps.service   # only for per-app remaps
```

### Elsewhere

`pipx install git+https://github.com/andrebbruno/omarchy-key-remap`, with keyd installed and
running. Everything works on any compositor except the per-app watcher, which needs Hyprland's
event socket.

## Commands

```
omarchy-key-remap                        the menu
omarchy-key-remap add <key> <action>     add a remap and apply it
omarchy-key-remap remove <key>           take one away
omarchy-key-remap list                   what is remapped
omarchy-key-remap status                 keyd, the config, the watcher
omarchy-key-remap clear                  turn everything off, keep it for later
omarchy-key-remap apply                  write and reload (after editing the JSON by hand)
omarchy-key-remap capture                print the next key you press
omarchy-key-remap keys [filter]          every key name keyd accepts
```

`--app <class>` scopes any of them to one window class — the `class` column of
`hyprctl clients`. `--note "why"` keeps a reminder next to the remap.

A keybinding for the menu, if you want one, in `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + K", "Key remap", "omarchy-key-remap")
```

## ⚠️ Before you remap something important

- **A bad remap can lock you out of your own keyboard.** keyd's escape hatch is to hold
  **backspace + escape + enter** together: keyd exits and the keyboard goes back to normal.
  That line is also written at the top of every config this tool generates.
- **Remapping a modifier to itself, or a key you need to type your password**, will follow you
  to the lock screen and the TTY — that is the price of remapping at the kernel layer, and the
  reason for the escape hatch above.
- **Per-app remaps need the `keyd` group.** Without it `keyd bind` cannot reach keyd's socket;
  `omarchy-key-remap status` tells you if that is the problem.
- **Per-app remaps are Hyprland-only.** The global ones work anywhere keyd does.

## How the per-app part works

Hyprland publishes every focus change on `$XDG_RUNTIME_DIR/hypr/<instance>/.socket2.sock`.
The watcher reads `activewindow>>class,title` from it, and on every change runs
`keyd bind reset` followed by the bindings for that class. The reset is the important half:
it restores exactly what the config file says, so a remap can never outlive the window it
belongs to.

## Development

```bash
python -m pytest tests -q     # 69 tests, no keyd and no root needed
```

The config generator (`okeyremap/keydconf.py`) and the key parser (`okeyremap/keys.py`) are
pure functions, and the watcher takes its `keyd bind` as an argument so the focus logic can be
tested without either. The embedded key list is `keyd list-keys` from keyd 2.6; when keyd is
installed, the live list wins.

## License

MIT © Andre Bruno
