"""FastAPI application for the Ethiopian Healthcare Translator.

Exposes the translation and glossary endpoints consumed by the Android
client. The API contract matches the guideline documentation:

    POST /translate
        request:  {"text": "...", "source_lang": "orm_Latn", "target_lang": "amh_Ethi"}
        response: {"translated_text": "...", "source_lang": "...", "target_lang": "..."}

Run locally with:

    uvicorn app.main:app --reload

The model loads on the first translation request, so /health returns
quickly even before the model is downloaded.
"""

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .glossary import glossary as glossary_service
from .languages import SUPPORTED_LANGUAGES, is_supported
from .models import (
    GlossaryEntryItem,
    GlossaryTermGroup,
    HealthResponse,
    LanguageInfo,
    TranslateRequest,
    TranslateResponse,
)
from .translator import TranslationError, translator as translator_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healthtranslator")

settings = get_settings()

app = FastAPI(
    title="Ethiopian Healthcare Translator API",
    description=(
        "Translation service for healthcare-related text among English, "
        "Afaan Oromoo, and Amharic using the NLLB-200 model. Intended as a "
        "communication aid, not a substitute for professional interpretation "
        "or clinical judgement."
    ),
    version="1.0.0",
)

# CORS: allow the Android app (and a dev browser) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report API and model readiness."""
    return HealthResponse(
        status="ok",
        model_loaded=translator_service.is_loaded,
        model=settings.nllb_model,
    )


@app.get("/languages", response_model=list[LanguageInfo], tags=["system"])
def languages() -> list[LanguageInfo]:
    """List the supported languages and their NLLB-200 codes."""
    return [LanguageInfo(**lang.to_dict()) for lang in SUPPORTED_LANGUAGES]


@app.post("/translate", response_model=TranslateResponse, tags=["translation"])
def translate(request: TranslateRequest) -> TranslateResponse:
    """Translate healthcare-related text between supported languages.

    Business rules (from the guideline):
      * source and target must be different,
      * both must be supported language codes,
      * input text must not be empty,
      * an understandable message is returned on failure.
    """
    # Validate input before touching the model so failures are cheap and clear.
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text must not be empty.")
    if request.source_lang == request.target_lang:
        raise HTTPException(
            status_code=400,
            detail="Source and target languages must be different.",
        )
    if not is_supported(request.source_lang):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source language: {request.source_lang}",
        )
    if not is_supported(request.target_lang):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language: {request.target_lang}",
        )

    try:
        result = translator_service.translate(
            request.text, request.source_lang, request.target_lang
        )
    except TranslationError as exc:
        # Surface a readable message rather than a raw stack trace.
        logger.warning("Translation rejected: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TranslateResponse(
        translated_text=result,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
    )


@app.get("/glossary", response_model=list[GlossaryTermGroup], tags=["glossary"])
def get_glossary(
    only_reviewed: bool = Query(
        False,
        description="Only return reviewed terms. Default False returns all "
        "terms with their review_status so the client can badge draft entries.",
    ),
    language: str | None = Query(None, description="Filter to one NLLB-200 code."),
) -> list[GlossaryTermGroup]:
    """Return healthcare glossary terms and explanations."""
    groups = glossary_service.list_terms(only_reviewed=only_reviewed, language=language)
    return [
        GlossaryTermGroup(
            term_group_id=g.term_group_id,
            category=g.category,
            entries=[
                GlossaryEntryItem(
                    language_code=e.language_code,
                    term=e.term,
                    explanation=e.explanation,
                    review_status=e.review_status,
                )
                for e in g.entries
            ],
        )
        for g in groups
    ]


@app.get("/glossary/search", response_model=list[GlossaryTermGroup], tags=["glossary"])
def search_glossary(
    q: str = Query(..., description="Search query over terms and explanations."),
    language: str | None = Query(None, description="Filter to one NLLB-200 code."),
) -> list[GlossaryTermGroup]:
    """Search glossary terms by text (case-insensitive)."""
    groups = glossary_service.search(q, language=language)
    return [
        GlossaryTermGroup(
            term_group_id=g.term_group_id,
            category=g.category,
            entries=[
                GlossaryEntryItem(
                    language_code=e.language_code,
                    term=e.term,
                    explanation=e.explanation,
                    review_status=e.review_status,
                )
                for e in g.entries
            ],
        )
        for g in groups
    ]


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
