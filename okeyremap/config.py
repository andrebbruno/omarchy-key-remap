"""Where the remaps are kept, and how they are read back."""
from __future__ import annotations

import json
import os

from .keydconf import Remap

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                          "omarchy-key-remap")
CONFIG_FILE = os.path.join(CONFIG_DIR, "remaps.json")
KEYD_CONF = "/etc/keyd/default.conf"


class Config:
    def __init__(self, path: str | None = None):
        self.path = path or CONFIG_FILE
        self.remaps: list[Remap] = []
        self.ids = "*"
        self.load()

    def load(self) -> "Config":
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        self.remaps = [Remap.from_json(r) for r in data.get("remaps", [])]
        self.ids = data.get("ids", "*")
        return self

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {"ids": self.ids, "remaps": [r.to_json() for r in self.remaps]}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, self.path)

    # ------------------------------------------------------------------ editing
    def add(self, remap: Remap, replace: bool = True) -> Remap | None:
        """Store a remap. Returns the one it replaced, if any."""
        remap.validate()
        old = None
        for i, existing in enumerate(self.remaps):
            if existing.key == remap.key:
                if not replace:
                    raise ValueError(f"{remap.source} is already remapped"
                                     + (f" in {remap.app}" if remap.app else ""))
                old = self.remaps[i]
                self.remaps[i] = remap
                break
        else:
            self.remaps.append(remap)
        return old

    def remove(self, source: str, app: str | None = None) -> Remap | None:
        probe = Remap(source=source, action="noop", app=app)
        for i, existing in enumerate(self.remaps):
            if existing.key == probe.key:
                return self.remaps.pop(i)
        return None

    def globals(self) -> list[Remap]:
        return [r for r in self.remaps if not r.app]

    def per_app(self) -> list[Remap]:
        return [r for r in self.remaps if r.app]
