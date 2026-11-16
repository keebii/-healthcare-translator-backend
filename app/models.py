"""Pydantic models for the API request/response contract.

These mirror the schema documented in the guideline:

    Request:
        { "text": "Akkam jirtu?", "source_lang": "orm_Latn", "target_lang": "amh_Ethi" }

    Response:
        { "translated_text": "...", "source_lang": "orm_Latn", "target_lang": "amh_Ethi" }
"""

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Translation request body sent by the Android client."""

    text: str = Field(..., description="Source text to translate")
    source_lang: str = Field(..., description="NLLB-200 source language code")
    target_lang: str = Field(..., description="NLLB-200 target language code")


class TranslateResponse(BaseModel):
    """Translation response returned to the Android client."""

    translated_text: str = Field(..., description="Translated output text")
    source_lang: str = Field(..., description="Echoed source language code")
    target_lang: str = Field(..., description="Echoed target language code")


class LanguageInfo(BaseModel):
    """A single supported language as exposed through the API."""

    code: str
    name: str
    native: str


class GlossaryEntryItem(BaseModel):
    """One language version of a glossary term group."""

    language_code: str
    term: str
    explanation: str
    review_status: str = Field(..., description='"reviewed" or "draft"')


class GlossaryTermGroup(BaseModel):
    """A reviewed medical concept with its rendering in each supported language."""

    term_group_id: int
    category: str
    entries: list[GlossaryEntryItem]


class HealthResponse(BaseModel):
    """Health-check payload."""

    status: str
    model_loaded: bool
    model: str
