"""Backend unit and API tests.

These map to the unit tests in the guideline documentation:

    UT-01  Language code mapping
    UT-02  Input validation (empty text)
    UT-03  Language validation (same source/target)
    UT-04  Response parsing (valid JSON response)
    UT-05  Error handling (API error -> readable message, no crash)

The translation model is mocked so tests run without downloading NLLB-200.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.languages import SUPPORTED_LANGUAGES, is_supported
from app.main import app
from app.translator import TranslationError

client = TestClient(app)


# Map the documentation's "UT-01" language-code mapping expectation.
EXPECTED_CODES = {"English": "eng_Latn", "Afaan Oromoo": "orm_Latn", "Amharic": "amh_Ethi"}


# --------------------------------------------------------------------------- #
# UT-01: Language code mapping
# --------------------------------------------------------------------------- #
def test_language_codes_are_correct():
    """English/Afaan Oromoo/Amharic map to eng_Latn, orm_Latn, amh_Ethi."""
    by_name = {lang.name: lang.code for lang in SUPPORTED_LANGUAGES}
    for name, code in EXPECTED_CODES.items():
        assert by_name[name] == code, f"{name} should map to {code}"
    for code in EXPECTED_CODES.values():
        assert is_supported(code), f"{code} should be supported"


def test_languages_endpoint_returns_all_three():
    response = client.get("/languages")
    assert response.status_code == 200
    codes = {lang["code"] for lang in response.json()}
    assert codes == {"eng_Latn", "orm_Latn", "amh_Ethi"}


# --------------------------------------------------------------------------- #
# UT-02: Input validation (empty text)
# --------------------------------------------------------------------------- #
def test_empty_text_rejected_without_model_call():
    """An empty request must fail validation and never reach the model."""
    with patch("app.main.translator_service") as mock_translator:
        response = client.post(
            "/translate",
            json={"text": "   ", "source_lang": "eng_Latn", "target_lang": "orm_Latn"},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        mock_translator.translate.assert_not_called()


# --------------------------------------------------------------------------- #
# UT-03: Language validation (same source and target)
# --------------------------------------------------------------------------- #
def test_same_source_target_rejected():
    response = client.post(
        "/translate",
        json={"text": "hello", "source_lang": "eng_Latn", "target_lang": "eng_Latn"},
    )
    assert response.status_code == 400
    assert "different" in response.json()["detail"].lower()


def test_unsupported_language_rejected():
    response = client.post(
        "/translate",
        json={"text": "hello", "source_lang": "eng_Latn", "target_lang": "fra_Latn"},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# UT-04: Response parsing (valid JSON response)
# --------------------------------------------------------------------------- #
def test_translate_parses_and_returns_expected_schema():
    """A valid API response is parsed into the documented response schema."""
    fake_output = "Akkam jirtu?"  # pretended model output
    with patch("app.main.translator_service") as mock_translator:
        mock_translator.translate.return_value = fake_output
        mock_translator.is_loaded = True

        response = client.post(
            "/translate",
            json={
                "text": "How are you?",
                "source_lang": "eng_Latn",
                "target_lang": "orm_Latn",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["translated_text"] == fake_output
    assert body["source_lang"] == "eng_Latn"
    assert body["target_lang"] == "orm_Latn"
    mock_translator.translate.assert_called_once_with(
        "How are you?", "eng_Latn", "orm_Latn"
    )


# --------------------------------------------------------------------------- #
# UT-05: Error handling (API error -> readable message, no crash)
# --------------------------------------------------------------------------- #
def test_model_error_returns_readable_message():
    with patch("app.main.translator_service") as mock_translator:
        mock_translator.translate.side_effect = TranslationError("Model unavailable")
        response = client.post(
            "/translate",
            json={
                "text": "How are you?",
                "source_lang": "eng_Latn",
                "target_lang": "amh_Ethi",
            },
        )
    assert response.status_code == 503
    assert "Model unavailable" in response.json()["detail"]


def test_health_endpoint_works():
    with patch("app.main.translator_service") as mock_translator:
        mock_translator.is_loaded = False
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False


# --------------------------------------------------------------------------- #
# Glossary
# --------------------------------------------------------------------------- #
def test_glossary_returns_all_entries_with_status_by_default():
    response = client.get("/glossary")
    assert response.status_code == 200
    groups = response.json()
    assert len(groups) > 0
    for group in groups:
        for entry in group["entries"]:
            assert entry["language_code"] in {"eng_Latn", "orm_Latn", "amh_Ethi"}
            assert entry["term"]
            assert entry["explanation"]
            assert entry["review_status"] in {"reviewed", "draft"}


def test_glossary_only_reviewed_filters_draft():
    response = client.get("/glossary", params={"only_reviewed": "true"})
    assert response.status_code == 200
    for group in response.json():
        for entry in group["entries"]:
            assert entry["review_status"] == "reviewed"


def test_glossary_search_matches_text():
    response = client.get("/glossary/search", params={"q": "fever"})
    assert response.status_code == 200
    groups = response.json()
    assert any("fever" in e["term"].lower() for g in groups for e in g["entries"])
