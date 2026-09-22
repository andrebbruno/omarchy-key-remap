import pytest

from okeyremap.keys import (COMMON_KEYS, KEYD_KEYS, KeyError_, canonical, describe,
                            layer_for, parse_combo, valid_keys, validate_action)


def test_a_bare_key():
    assert parse_combo("capslock") == ((), "capslock")


def test_modifiers_are_normalised_to_keyds_names():
    assert parse_combo("ctrl+c") == (("control",), "c")
    assert parse_combo("super+v") == (("meta",), "v")
    assert parse_combo("win+v") == (("meta",), "v")
    assert parse_combo("cmd+v") == (("meta",), "v")
    assert parse_combo("option+f") == (("alt",), "f")


def test_modifiers_come_back_in_a_fixed_order():
    assert parse_combo("shift+ctrl+c")[0] == ("control", "shift")
    assert parse_combo("ctrl+shift+c")[0] == ("control", "shift")


def test_a_repeated_modifier_is_not_counted_twice():
    assert parse_combo("ctrl+control+c")[0] == ("control",)


def test_case_and_spacing_do_not_matter():
    assert parse_combo("  CTRL + Shift + C ") == (("control", "shift"), "c")


def test_a_hyphen_separates_just_like_a_plus():
    assert parse_combo("ctrl-c") == (("control",), "c")


def test_the_minus_key_itself_survives():
    assert parse_combo("ctrl+-") == (("control",), "minus")
    assert parse_combo("-") == ((), "minus")


def test_a_lone_modifier_means_its_physical_key():
    assert parse_combo("ctrl") == ((), "leftcontrol")
    assert parse_combo("super") == ((), "leftmeta")


def test_an_empty_combination_is_refused():
    with pytest.raises(KeyError_):
        parse_combo("")
    with pytest.raises(KeyError_):
        parse_combo("   ")


def test_an_unknown_key_is_refused_with_a_pointer_to_the_list():
    with pytest.raises(KeyError_) as e:
        parse_combo("capslok")
    assert "keys" in str(e.value)


def test_layer_names():
    assert layer_for(()) == "main"
    assert layer_for(("control",)) == "control"
    assert layer_for(("control", "alt")) == "control+alt"


def test_canonical_collapses_spellings():
    assert canonical("Shift+Ctrl+c") == canonical("ctrl+shift+C") == "control+shift+c"


def test_describe_reads_like_a_person_wrote_it():
    assert describe("ctrl+shift+c") == "Ctrl + Shift + C"
    assert describe("super+v") == "Super + V"
    assert describe("capslock") == "Capslock"


def test_describe_never_raises_on_junk():
    assert describe("not a key") == "not a key"


# ---------------------------------------------------------------- actions

def test_a_plain_key_is_a_valid_action():
    assert validate_action("esc") == "esc"


def test_a_chord_is_a_valid_action():
    for chord in ("C-c", "M-v", "C-S-tab", "M-S-a"):
        assert validate_action(chord) == chord


def test_keyd_actions_are_accepted():
    for action in ("macro(C-g n)", "command(omarchy-menu)", "layer(nav)",
                   "overload(control, esc)", "oneshot(shift)", "noop"):
        assert validate_action(action) == action


def test_an_unbalanced_action_is_refused():
    with pytest.raises(KeyError_):
        validate_action("macro(C-g n")


def test_an_unknown_function_is_refused():
    with pytest.raises(KeyError_) as e:
        validate_action("rm_rf(/)")
    assert "keyd action" in str(e.value)


def test_a_misspelled_key_on_the_right_is_refused():
    with pytest.raises(KeyError_):
        validate_action("escc")


def test_an_empty_action_is_refused():
    with pytest.raises(KeyError_):
        validate_action("")


# ---------------------------------------------------------------- the key list

def test_the_embedded_list_looks_like_keyds():
    assert len(KEYD_KEYS) > 250
    for key in ("esc", "capslock", "leftmeta", "f12", "volumeup", "a", "1"):
        assert key in KEYD_KEYS


def test_every_key_offered_in_the_menu_is_one_keyd_accepts():
    """A menu entry keyd would reject is a dead end the user cannot debug."""
    keys = valid_keys()
    unknown = [k for k in COMMON_KEYS if k not in keys]
    assert unknown == [], f"not keyd key names: {unknown}"
