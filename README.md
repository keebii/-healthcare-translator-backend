# Ethiopian Healthcare Translator — Backend (FastAPI + NLLB-200)

Python/FastAPI service that translates healthcare-related text among **English**,
**Afaan Oromoo**, and **Amharic** using the NLLB-200 multilingual model, and serves
a reviewed healthcare glossary.

This is the backend half of the project described in the guideline document. The
Android client (`../android`) consumes this API.

> **Disclaimer:** This application is a communication aid, not a substitute for
> professional medical interpretation or clinical judgement. Glossary entries are
> provisional and must be reviewed by competent language speakers and a qualified
> healthcare professional before being treated as verified.

## Language codes (NLLB-200)

| Language      | Code        |
|---------------|-------------|
| English       | `eng_Latn`  |
| Afaan Oromoo  | `orm_Latn`  |
| Amharic       | `amh_Ethi`  |

## API contract

### `POST /translate`
```json
// request
{ "text": "Akkam jirtu?", "source_lang": "orm_Latn", "target_lang": "amh_Ethi" }

// response
{ "translated_text": "...", "source_lang": "orm_Latn", "target_lang": "amh_Ethi" }
```
Validation (FR-06): empty text, identical source/target, and unsupported codes
return `400` with a readable `detail`. Model/transport failures return `503`.

### `GET /health`
Returns `{ "status", "model_loaded", "model" }`. The model loads lazily on the
first translate request, so `/health` is fast before the model is downloaded.

### `GET /languages`
Lists the three supported languages with codes and native names.

### `GET /glossary` / `GET /glossary/search`
Reviewed healthcare terms with plain-language explanations. Each entry carries
a `review_status` of `reviewed` or `draft`; draft entries are returned with a
status so the client can badge them, rather than being hidden.

## Setup

Requires **Python 3.10–3.13** (the NLLB stack ships prebuilt wheels for these).
Using a virtual environment is recommended.

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/mac: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env      # adjust model/device if needed
```

### Run the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open the interactive docs at `http://localhost:8000/docs`.

The first translation request downloads the NLLB-200 model (a few GB) and may
take a while; subsequent requests use the cached, in-memory model.

### CPU vs GPU
Set `DEVICE=cuda` in `.env` to use a CUDA-capable GPU. On CPU the distilled
600M model is the practical default.

## Tests

The unit tests (UT-01 … UT-05 in the guideline) mock the translation model, so
they run **without** downloading NLLB-200:

```bash
pytest -v
```

> Use a stable CPython (3.10–3.13). Pre-release alphas (e.g. 3.15.0a6) break the
> async/compiled stack (`anyio`, `pydantic-core`, `pytest`) and are not suitable
> for running the suite.

## Notes on the model

- Default model: `facebook/nllb-200-distilled-600M` (lighter). For higher
  accuracy, set `NLLB_MODEL=facebook/nllb-200-3.3B` in `.env` (needs more RAM/VRAM).
- Translation quality for the healthcare domain and for every language direction
  must be evaluated with reviewed test data — see the guideline's testing chapter.
