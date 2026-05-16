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


def test_all_languages_present() -> None:
    from src.bot.locales import _STRINGS

    expected_langs = {
        "en", "ru", "hi", "id", "pt", "uk", "ar",
        "fa", "de", "tr", "es", "fr", "uz", "am", "ko",
    }
    for key, translations in _STRINGS.items():
        missing = expected_langs - set(translations.keys())
        assert not missing, (
            f"Key '{key}' missing languages: {missing}"
        )
