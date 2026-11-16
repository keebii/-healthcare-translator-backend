"""Supported languages and their NLLB-200 language codes.

IMPORTANT: NLLB-200 uses 'gaz_Latn' for Afaan Oromoo (Borana-Arsi-Guji Oromo),
NOT 'orm_Latn'. Using orm_Latn returns the unknown token and produces empty output.

    English       -> eng_Latn   (token_id: 256047)
    Afaan Oromoo  -> gaz_Latn   (token_id: 256135)
    Amharic       -> amh_Ethi   (token_id: 256009)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str        # NLLB-200 identifier
    name: str        # Display name
    native: str      # Native script display
    app_code: str    # Code exposed to the Android app (kept as orm_Latn for UI)

    def to_dict(self) -> dict:
        return {"code": self.app_code, "name": self.name, "native": self.native}


SUPPORTED_LANGUAGES: list[Language] = [
    Language("eng_Latn", "English",      "English",      "eng_Latn"),
    Language("gaz_Latn", "Afaan Oromoo", "Afaan Oromoo", "orm_Latn"),
    Language("amh_Ethi", "Amharic",      "አማርኛ",         "amh_Ethi"),
]

# Lookup by NLLB code (gaz_Latn) or app code (orm_Latn)
LANGUAGES_BY_CODE: dict[str, Language] = {}
for _lang in SUPPORTED_LANGUAGES:
    LANGUAGES_BY_CODE[_lang.code]     = _lang   # real NLLB code
    LANGUAGES_BY_CODE[_lang.app_code] = _lang   # app-facing code


def is_supported(code: str) -> bool:
    return code in LANGUAGES_BY_CODE


def nllb_code(app_code: str) -> str:
    """Convert app-facing code (orm_Latn) to real NLLB code (gaz_Latn)."""
    lang = LANGUAGES_BY_CODE.get(app_code)
    return lang.code if lang else app_code
