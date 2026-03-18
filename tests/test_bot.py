from app.bot import PRESET_CALLBACK_PREFIX, _preset_keyboard


def test_preset_keyboard_contains_all_processing_modes() -> None:
    keyboard = _preset_keyboard()
    first_row = keyboard.inline_keyboard[0]
    second_row = keyboard.inline_keyboard[1]
    third_row = keyboard.inline_keyboard[2]

    assert [button.text for button in first_row] == ["Лок Мягко", "Общ Мягко"]
    assert [button.callback_data for button in first_row] == [
        f"{PRESET_CALLBACK_PREFIX}natural",
        f"{PRESET_CALLBACK_PREFIX}global_natural",
    ]
    assert [button.text for button in second_row] == ["Лок Баланс", "Общ Баланс"]
    assert [button.callback_data for button in second_row] == [
        f"{PRESET_CALLBACK_PREFIX}balanced",
        f"{PRESET_CALLBACK_PREFIX}global_balanced",
    ]
    assert [button.text for button in third_row] == ["Лок Сильно", "Общ Сильно"]
    assert [button.callback_data for button in third_row] == [
        f"{PRESET_CALLBACK_PREFIX}strong",
        f"{PRESET_CALLBACK_PREFIX}global_strong",
    ]
