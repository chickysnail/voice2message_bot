from src.bot.locales import t


def test_english_fallback() -> None:
    result = t("greeting", "xx", user="Bob")
    assert "Bob" in result
    assert "Welcome" in result


def test_russian_greeting() -> None:
    result = t("greeting", "ru", user="Иван")
    assert "Иван" in result
    assert "Добро пожаловать" in result


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
    assert "Send me a voice message" in result


def test_no_partial_translations() -> None:
    """English-only keys are OK (work in progress).

    But if a key has English + at least one other language,
    ALL supported languages must be present — partial translations
    mean something was missed.
    """
    from src.bot.locales import _STRINGS

    expected_langs = {
        "en", "ru", "hi", "id", "pt", "uk", "ar",
        "fa", "de", "tr", "es", "fr", "uz", "am", "ko",
    }
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
