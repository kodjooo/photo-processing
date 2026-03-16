from app.bot import PRESET_CALLBACK_PREFIX, _preset_keyboard


def test_preset_keyboard_contains_all_processing_modes() -> None:
    keyboard = _preset_keyboard()
    buttons = keyboard.inline_keyboard[0]

    assert [button.text for button in buttons] == ["Natural", "Balanced", "Strong"]
    assert [button.callback_data for button in buttons] == [
        f"{PRESET_CALLBACK_PREFIX}natural",
        f"{PRESET_CALLBACK_PREFIX}balanced",
        f"{PRESET_CALLBACK_PREFIX}strong",
    ]
