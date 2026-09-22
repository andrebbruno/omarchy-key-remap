"""Per-app remaps: follow the focused window and hand keyd the right bindings.

keyd ships an application mapper of its own, but it only knows X11 and GNOME. On
Hyprland the answer is simpler than it is anywhere else: the compositor already
broadcasts every focus change on a socket, and keyd already accepts bindings at
runtime, so this is a loop between the two.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
import time

from .keydconf import Remap, bindings_for_app

log = logging.getLogger("omarchy-key-remap")


def event_socket_path() -> str | None:
    """$XDG_RUNTIME_DIR/hypr/<instance>/.socket2.sock, if Hyprland is running."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not runtime:
        return None
    base = os.path.join(runtime, "hypr")
    if not signature:
        try:
            entries = sorted(os.listdir(base))
        except OSError:
            return None
        signature = entries[0] if entries else None
    if not signature:
        return None
    path = os.path.join(base, signature, ".socket2.sock")
    return path if os.path.exists(path) else None


def parse_event(line: str) -> tuple[str, str] | None:
    """Hyprland writes "<name>>><data>"; we care about which window took focus.

    activewindow carries "class,title" and the title may itself contain commas, so
    only the first one separates. An empty class means the desktop has the focus.
    """
    if ">>" not in line:
        return None
    name, _, data = line.partition(">>")
    if name == "activewindow":
        return "focus", data.split(",", 1)[0]
    if name in ("activewindowv2", "closewindow") and not data.strip():
        return "focus", ""
    return None


def keyd_bind(expressions: list[str]) -> bool:
    """Replace the runtime bindings with these. `reset` restores what the file says."""
    try:
        r = subprocess.run(["keyd", "bind", "reset", *expressions],
                           capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("keyd bind failed: %s", e)
        return False
    if r.returncode != 0:
        detail = (r.stderr + r.stdout).decode("utf-8", "replace").strip()
        log.warning("keyd bind failed: %s", detail)
        return False
    return True


class Watcher:
    """Applies the per-app remaps as the focus moves. One socket, one process."""

    def __init__(self, remaps: list[Remap], bind=keyd_bind):
        self.remaps = remaps
        self.bind = bind
        self.current: str | None = None

    def focus(self, window_class: str) -> None:
        """Bind what this window needs — and do nothing when nothing changed."""
        if window_class == self.current:
            return
        self.current = window_class
        wanted = bindings_for_app(self.remaps, window_class) if window_class else []
        log.info("focus %s: %d remap(s)%s", window_class or "(none)", len(wanted),
                 ": " + "; ".join(wanted) if wanted else "")
        # An empty list still resets: leaving the previous app's bindings in place is
        # how a remap ends up firing in the wrong window.
        self.bind(wanted)

    def run(self, retry_seconds: float = 2.0) -> None:
        while True:
            path = event_socket_path()
            if path is None:
                log.info("waiting for Hyprland's event socket")
                time.sleep(retry_seconds)
                continue
            try:
                self._listen(path)
            except OSError as e:
                log.info("event socket closed (%s), reconnecting", e)
            self.current = None
            time.sleep(retry_seconds)

    def _listen(self, path: str) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(path)
            log.info("watching %s", path)
            buffer = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    return
                buffer += chunk
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    event = parse_event(line.decode("utf-8", "replace"))
                    if event:
                        self.focus(event[1])
