import json

import pytest

from okeyremap.config import Config
from okeyremap.keydconf import Remap


@pytest.fixture
def cfg(tmp_path):
    return Config(str(tmp_path / "remaps.json"))


def test_a_missing_file_is_an_empty_config(tmp_path):
    assert Config(str(tmp_path / "nothing.json")).remaps == []


def test_a_corrupt_file_does_not_take_the_tool_down(tmp_path):
    path = tmp_path / "remaps.json"
    path.write_text("{ this is not json", encoding="utf-8")
    assert Config(str(path)).remaps == []


def test_a_remap_survives_a_round_trip(cfg):
    cfg.add(Remap("capslock", "esc", note="from macOS"))
    cfg.save()
    again = Config(cfg.path)
    assert len(again.remaps) == 1
    assert again.remaps[0].source == "capslock"
    assert again.remaps[0].action == "esc"
    assert again.remaps[0].note == "from macOS"


def test_accents_are_written_readably(cfg, tmp_path):
    cfg.add(Remap("f9", "command(echo ação)"))
    cfg.save()
    assert "ação" in (tmp_path / "remaps.json").read_text(encoding="utf-8")


def test_adding_the_same_combination_replaces_it(cfg):
    cfg.add(Remap("capslock", "esc"))
    old = cfg.add(Remap("Caps + lock".replace(" + ", "").replace("caps", "caps"), "tab")) \
        if False else cfg.add(Remap("capslock", "tab"))
    assert old is not None and old.action == "esc"
    assert len(cfg.remaps) == 1
    assert cfg.remaps[0].action == "tab"


def test_replacing_can_be_refused(cfg):
    cfg.add(Remap("capslock", "esc"))
    with pytest.raises(ValueError):
        cfg.add(Remap("capslock", "tab"), replace=False)


def test_the_same_key_in_two_apps_is_two_remaps(cfg):
    cfg.add(Remap("ctrl+w", "noop", app="chromium"))
    cfg.add(Remap("ctrl+w", "noop", app="foot"))
    assert len(cfg.remaps) == 2


def test_removing_takes_the_app_into_account(cfg):
    cfg.add(Remap("ctrl+w", "noop", app="chromium"))
    cfg.add(Remap("ctrl+w", "esc"))
    assert cfg.remove("ctrl+w", app="chromium") is not None
    assert len(cfg.remaps) == 1
    assert cfg.remaps[0].app is None


def test_removing_something_that_is_not_there_says_so(cfg):
    assert cfg.remove("capslock") is None


def test_globals_and_per_app_are_kept_apart(cfg):
    cfg.add(Remap("capslock", "esc"))
    cfg.add(Remap("ctrl+w", "noop", app="chromium"))
    assert [r.source for r in cfg.globals()] == ["capslock"]
    assert [r.source for r in cfg.per_app()] == ["ctrl+w"]


def test_saving_is_atomic(cfg, tmp_path):
    """A half-written config is a config the next run cannot read."""
    cfg.add(Remap("capslock", "esc"))
    cfg.save()
    assert not (tmp_path / "remaps.json.tmp").exists()
    json.loads((tmp_path / "remaps.json").read_text(encoding="utf-8"))
