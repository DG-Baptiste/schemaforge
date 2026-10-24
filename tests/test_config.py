from schemaforge.config import Settings


def test_settings_from_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "demo")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    settings = Settings.from_env()
    assert settings.base_url == "https://example.test/v1"
    assert settings.model == "demo"
    assert settings.max_retries == 4
