from src.bot.locales import t


def test_english_fallback() -> None:
    result = t("greeting", "xx", user="Bob")
    assert "Bob" in result
    assert "Hi" in result


def test_russian_greeting() -> None:
    result = t("greeting", "ru", user="Иван")
    assert "Иван" in result
    assert "Привет" in result


def test_all_keys_have_english() -> None:
    from src.bot.locales import _STRINGS

    for key in _STRINGS:
        assert "en" in _STRINGS[key], f"Key '{key}' missing English translation"


def test_placeholder_formatting() -> None:
    result = t("audio_too_long", "en", duration="5m 30s", max_min=60)
    assert "5m 30s" in result
    assert "60" in result


def test_unknown_key_returns_key() -> None:
    assert t("nonexistent_key", "en") == "nonexistent_key"


def test_none_lang_defaults_to_english() -> None:
    result = t("help", None)
    assert "voice message" in result


def test_button_labels_localized() -> None:
    """Button labels should be available in all languages."""
    for key in ("btn_summarize", "btn_save_file", "btn_transcribe",
                "btn_secretary_setup"):
        en = t(key, "en")
        ru = t(key, "ru")
        assert en != key, f"{key} missing English translation"
        assert ru != en, f"{key} not localized for Russian"


def test_secretary_setup_mentions_chat_automation() -> None:
    """Setup instructions should reference the Telegram settings path."""
    result = t("secretary_setup", "en")
    assert "Chat Automation" in result
    assert "Account" in result


def test_keyboard_uses_localized_labels() -> None:
    """Keyboard buttons should use localized labels."""
    from src.bot.keyboards import (
        post_transcription_keyboard,
        secretary_setup_keyboard,
        secretary_transcribe_keyboard,
    )

    kb_en = post_transcription_keyboard(123, "en")
    kb_ru = post_transcription_keyboard(123, "ru")
    assert kb_en.inline_keyboard[0][0].text == "Summarize"
    assert kb_ru.inline_keyboard[0][0].text != "Summarize"

    setup_en = secretary_setup_keyboard("en")
    assert "transcription" in setup_en.inline_keyboard[0][0].text.lower()

    tr_ru = secretary_transcribe_keyboard(123, "conn_1", "ru")
    assert tr_ru.inline_keyboard[0][0].text != "📝 Transcribe"


def test_no_partial_translations() -> None:
    """English-only keys are OK (work in progress).

    But if a key has English + at least one other language,
    ALL supported languages must be present — partial translations
    mean something was missed.
    """
    from src.bot.locales import _STRINGS

    expected_langs = {"en", "ru", "hi", "id", "fa"}
    for key, translations in _STRINGS.items():
        langs = set(translations.keys())
        if langs == {"en"}:
            continue
        missing = expected_langs - langs
        assert not missing, (
            f"Key '{key}' has partial translations — "
            f"missing: {missing}. Either add all languages "
            f"or keep English-only during development."
        )
