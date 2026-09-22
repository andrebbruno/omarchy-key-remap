from okeyremap.hypr import Watcher, parse_event
from okeyremap.keydconf import Remap


def test_activewindow_gives_the_class():
    assert parse_event("activewindow>>foot,cat /tmp/x") == ("focus", "foot")


def test_a_title_with_commas_does_not_confuse_the_class():
    assert parse_event("activewindow>>chromium,Hello, world, again") == ("focus", "chromium")


def test_focus_leaving_every_window_is_an_empty_class():
    assert parse_event("activewindow>>,") == ("focus", "")


def test_other_events_are_ignored():
    for line in ("workspace>>2", "openwindow>>abc,1,foot,title", "monitoradded>>DP-1", "", "junk"):
        assert parse_event(line) is None


class Recorder:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, expressions):
        self.calls.append(list(expressions))
        return True


def remaps():
    return [Remap("ctrl+w", "noop", app="chromium"),
            Remap("ctrl+q", "noop", app="foot"),
            Remap("capslock", "esc")]


def test_focusing_an_app_binds_only_its_remaps():
    bind = Recorder()
    Watcher(remaps(), bind=bind).focus("chromium")
    assert bind.calls == [["control.w = noop"]]


def test_moving_between_apps_replaces_the_bindings():
    bind = Recorder()
    w = Watcher(remaps(), bind=bind)
    w.focus("chromium")
    w.focus("foot")
    assert bind.calls == [["control.w = noop"], ["control.q = noop"]]


def test_an_app_with_no_remaps_still_clears_the_previous_ones():
    """Otherwise the last app's remap keeps firing in a window that never asked for it."""
    bind = Recorder()
    w = Watcher(remaps(), bind=bind)
    w.focus("chromium")
    w.focus("firefox")
    assert bind.calls[-1] == []


def test_the_same_window_twice_does_not_talk_to_keyd_again():
    bind = Recorder()
    w = Watcher(remaps(), bind=bind)
    w.focus("foot")
    w.focus("foot")
    assert len(bind.calls) == 1


def test_losing_focus_altogether_clears_the_bindings():
    bind = Recorder()
    w = Watcher(remaps(), bind=bind)
    w.focus("foot")
    w.focus("")
    assert bind.calls[-1] == []
