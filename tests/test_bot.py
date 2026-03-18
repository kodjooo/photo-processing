from app.bot import PRESET_CALLBACK_PREFIX, _preset_keyboard


def test_preset_keyboard_contains_all_processing_modes() -> None:
    keyboard = _preset_keyboard()
    local_buttons = keyboard.inline_keyboard[0]
    global_buttons = keyboard.inline_keyboard[1]

    assert [button.text for button in local_buttons] == ["Local Natural", "Local Balanced", "Local Strong"]
    assert [button.callback_data for button in local_buttons] == [
        f"{PRESET_CALLBACK_PREFIX}natural",
        f"{PRESET_CALLBACK_PREFIX}balanced",
        f"{PRESET_CALLBACK_PREFIX}strong",
    ]
    assert [button.text for button in global_buttons] == ["Global Natural", "Global Balanced", "Global Strong"]
    assert [button.callback_data for button in global_buttons] == [
        f"{PRESET_CALLBACK_PREFIX}global_natural",
        f"{PRESET_CALLBACK_PREFIX}global_balanced",
        f"{PRESET_CALLBACK_PREFIX}global_strong",
    ]
