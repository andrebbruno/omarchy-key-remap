import pytest

from okeyremap.keydconf import Remap, apps, binding, bindings_for_app, generate
from okeyremap.keys import KeyError_


def test_a_plain_remap_lands_in_main():
    out = generate([Remap("capslock", "esc")])
    assert "[ids]" in out and "\n*\n" in out
    assert "[main]" in out
    assert "capslock = esc" in out


def test_a_shortcut_lands_in_its_modifier_layer():
    out = generate([Remap("ctrl+shift+c", "C-insert")])
    assert "[control+shift]" in out
    assert "c = C-insert" in out
    assert "ctrl" not in out                       # the alias never reaches the file


def test_composite_layers_come_after_their_parts():
    """keyd refuses a composite layer defined before the layers it is made of."""
    out = generate([Remap("control+alt+h", "left"), Remap("control+j", "down"),
                    Remap("capslock", "esc")])
    order = [out.index(s) for s in ("[main]", "[control]", "[control+alt]")]
    assert order == sorted(order)


def test_a_note_is_kept_as_a_comment():
    out = generate([Remap("capslock", "esc", note="muscle memory from macOS")])
    assert "# muscle memory from macOS" in out
    assert out.index("# muscle memory") < out.index("capslock = esc")


def test_per_app_remaps_stay_out_of_the_global_file():
    out = generate([Remap("ctrl+w", "noop", app="chromium"), Remap("capslock", "esc")])
    assert "noop" not in out
    assert "capslock = esc" in out


def test_an_empty_config_is_still_valid_and_says_so():
    out = generate([])
    assert "[ids]" in out
    assert "No global remaps yet" in out


def test_the_file_warns_against_editing_it_and_names_the_escape_hatch():
    out = generate([Remap("capslock", "esc")])
    assert "Do not edit by hand" in out
    assert "backspace+escape+enter" in out


def test_the_ids_section_can_be_narrowed_to_one_keyboard():
    out = generate([Remap("capslock", "esc")], ids="046d:c31c")
    assert "046d:c31c" in out


# ---------------------------------------------------------------- bindings

def test_binding_for_a_plain_key():
    assert binding(Remap("capslock", "esc")) == "capslock = esc"


def test_binding_for_a_shortcut_uses_the_layer_prefix():
    assert binding(Remap("alt+rightbrace", "macro(C-tab)")) == "alt.rightbrace = macro(C-tab)"
    assert binding(Remap("ctrl+shift+c", "C-insert")) == "control+shift.c = C-insert"


def test_bindings_for_an_app_only_include_that_app():
    remaps = [Remap("ctrl+w", "noop", app="chromium"),
              Remap("ctrl+q", "noop", app="foot"),
              Remap("capslock", "esc")]
    assert bindings_for_app(remaps, "chromium") == ["control.w = noop"]
    assert bindings_for_app(remaps, "foot") == ["control.q = noop"]
    assert bindings_for_app(remaps, "firefox") == []


def test_the_window_class_is_matched_without_regard_to_case():
    remaps = [Remap("ctrl+w", "noop", app="Chromium")]
    assert bindings_for_app(remaps, "chromium") == ["control.w = noop"]


def test_apps_lists_each_one_once_in_the_order_they_appear():
    remaps = [Remap("a", "b", app="foot"), Remap("c", "d", app="chromium"),
              Remap("e", "f", app="foot"), Remap("g", "h")]
    assert apps(remaps) == ["foot", "chromium"]


# ---------------------------------------------------------------- validation

def test_an_unknown_key_is_refused_before_anything_is_written():
    with pytest.raises(KeyError_):
        generate([Remap("caps_lock", "esc")])


def test_an_unknown_modifier_is_refused():
    with pytest.raises(KeyError_):
        generate([Remap("hyper+c", "esc")])


def test_an_unbalanced_action_is_refused():
    with pytest.raises(KeyError_):
        generate([Remap("capslock", "macro(C-g n")])


def test_an_invented_action_is_refused():
    with pytest.raises(KeyError_):
        generate([Remap("capslock", "explode(everything)")])


def test_a_blank_app_is_refused_rather_than_silently_global():
    with pytest.raises(KeyError_):
        Remap("capslock", "esc", app="   ").validate()


def test_the_same_combination_spelled_differently_is_the_same_remap():
    a = Remap("ctrl+shift+c", "esc")
    b = Remap("Shift+Control+c", "tab")
    assert a.key == b.key


def test_remaps_in_different_apps_are_different_remaps():
    a = Remap("ctrl+w", "noop", app="chromium")
    b = Remap("ctrl+w", "noop", app="foot")
    assert a.key != b.key
