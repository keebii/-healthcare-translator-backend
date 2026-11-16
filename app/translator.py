"""NLLB-200 translation service."""

import logging
import threading

from .config import get_settings
from .languages import is_supported, nllb_code

logger = logging.getLogger("healthtranslator.translator")


class TranslationError(Exception):
    pass


class TranslatorService:

    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None
        self._settings = get_settings()
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading NLLB-200 model %s ...", self._settings.nllb_model)
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(self._settings.nllb_model)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(
            self._settings.nllb_model
        ).to(self._settings.device)
        self._model.eval()
        logger.info("Model loaded on device '%s'.", self._settings.device)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            raise TranslationError("Text must not be empty.")
        if source_lang == target_lang:
            raise TranslationError("Source and target languages must differ.")
        if not is_supported(source_lang):
            raise TranslationError(f"Unsupported source language: {source_lang}")
        if not is_supported(target_lang):
            raise TranslationError(f"Unsupported target language: {target_lang}")

        self._load()

        import torch

        with self._lock:
            try:
                # Convert app codes (orm_Latn) to real NLLB codes (gaz_Latn)
                real_src = nllb_code(source_lang)
                real_tgt = nllb_code(target_lang)

                self._tokenizer.src_lang = real_src
                inputs = self._tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self._settings.max_source_length,
                ).to(self._settings.device)

                self._tokenizer.set_tgt_lang_special_tokens(real_tgt)
                forced_bos_id = self._tokenizer.cur_lang_code

                with torch.no_grad():
                    generated = self._model.generate(
                        **inputs,
                        forced_bos_token_id=forced_bos_id,
                        max_length=self._settings.max_target_length,
                        num_beams=4,
                    )

                output = self._tokenizer.batch_decode(
                    generated, skip_special_tokens=True
                )[0]
                return output.strip()
            except TranslationError:
                raise
            except Exception as exc:
                logger.exception("Translation failed for %s->%s", source_lang, target_lang)
                raise TranslationError(f"Translation failed: {exc}") from exc


translator = TranslatorService()
