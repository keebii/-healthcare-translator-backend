"""
Ethiopian Healthcare Translator - Main API

Auto-detects environment:
- Cloud (no torch): uses phrase dictionary
- Local (torch available): uses NLLB-200 model
"""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Ethiopian Healthcare Translator API",
    description="Healthcare translation among English, Afaan Oromoo, and Amharic.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Check if torch/transformers available ──────────────────────
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    HAS_MODEL = True
except ImportError:
    HAS_MODEL = False

LANGS = [
    {"code": "eng_Latn", "name": "English",      "native": "English"},
    {"code": "orm_Latn", "name": "Afaan Oromoo",  "native": "Afaan Oromoo"},
    {"code": "amh_Ethi", "name": "Amharic",       "native": "አማርኛ"},
]
CODES = {l["code"] for l in LANGS}

# ── Phrase dictionary (always available) ──────────────────────
PHRASES = [
    {"eng_Latn": "hello",                       "orm_Latn": "Akkam",                              "amh_Ethi": "ሰላም"},
    {"eng_Latn": "how are you",                 "orm_Latn": "Akkam jirtu?",                       "amh_Ethi": "እንዴት ነዎት?"},
    {"eng_Latn": "how are you?",                "orm_Latn": "Akkam jirtu?",                       "amh_Ethi": "እንዴት ነዎት?"},
    {"eng_Latn": "thank you",                   "orm_Latn": "Galatoomi",                          "amh_Ethi": "አመሰግናለሁ"},
    {"eng_Latn": "yes",                         "orm_Latn": "Eeyyee",                             "amh_Ethi": "አዎ"},
    {"eng_Latn": "no",                          "orm_Latn": "Lakki",                              "amh_Ethi": "አይ"},
    {"eng_Latn": "i have a fever",              "orm_Latn": "Ani hoo'a qaba",                     "amh_Ethi": "ትኩሳት ይዤአለሁ"},
    {"eng_Latn": "i have a headache",           "orm_Latn": "Mataan na dhukkuba",                 "amh_Ethi": "ራስ ምታት አለኝ"},
    {"eng_Latn": "i have a cough",              "orm_Latn": "Ani sanaa'a qaba",                   "amh_Ethi": "ሳልሳ ይዤአለሁ"},
    {"eng_Latn": "i have stomach pain",         "orm_Latn": "Garaan na dhukkuba",                 "amh_Ethi": "ሆዴ ያምኛል"},
    {"eng_Latn": "i have chest pain",           "orm_Latn": "Hudhaan na dhukkuba",                "amh_Ethi": "ደረቴ ያምኛል"},
    {"eng_Latn": "i have back pain",            "orm_Latn": "Dugdaan na dhukkuba",                "amh_Ethi": "ጀርባዬ ያምኛል"},
    {"eng_Latn": "i feel dizzy",                "orm_Latn": "Mataan na naanna'a",                 "amh_Ethi": "ራሴ ያዞራል"},
    {"eng_Latn": "i am tired",                  "orm_Latn": "Nan dadhabe",                        "amh_Ethi": "ደክሞኛል"},
    {"eng_Latn": "i have diarrhea",             "orm_Latn": "Garaan na baayyise",                 "amh_Ethi": "ተቅማጥ አለብኝ"},
    {"eng_Latn": "i am vomiting",               "orm_Latn": "Nan aarsa",                          "amh_Ethi": "ማስታወክ አለብኝ"},
    {"eng_Latn": "i have difficulty breathing", "orm_Latn": "Hafuura na rakkisa",                 "amh_Ethi": "መተንፈስ ይከብደኛል"},
    {"eng_Latn": "i have a sore throat",        "orm_Latn": "Mormi na dhukkuba",                  "amh_Ethi": "ጉሮሮዬ ያምኛል"},
    {"eng_Latn": "i am pregnant",               "orm_Latn": "Ani ulfa",                           "amh_Ethi": "ነፍሰ ጡር ነኝ"},
    {"eng_Latn": "i have malaria",              "orm_Latn": "Bofaa qaba",                         "amh_Ethi": "ወባ አለብኝ"},
    {"eng_Latn": "i have diabetes",             "orm_Latn": "Dhibee sukkaara qaba",               "amh_Ethi": "የስኳር ህመም አለብኝ"},
    {"eng_Latn": "i have high blood pressure",  "orm_Latn": "Dhiigni na ol ka'e",                 "amh_Ethi": "ደሜ ከፍ ብሏል"},
    {"eng_Latn": "i need a doctor",             "orm_Latn": "Doktora nan barbaada",               "amh_Ethi": "ዶክተር ያስፈልገኛል"},
    {"eng_Latn": "i need to see a doctor",      "orm_Latn": "Doktora arguun nan barbaada",        "amh_Ethi": "ዶክተር ማየት ያስፈልገኛል"},
    {"eng_Latn": "call an ambulance",           "orm_Latn": "Ambiilaansii waamu",                 "amh_Ethi": "አምቡላንስ ደውሉ"},
    {"eng_Latn": "it is an emergency",          "orm_Latn": "Ariitii barbaachisa",                "amh_Ethi": "አስቸኳይ ሁኔታ ነው"},
    {"eng_Latn": "take this medicine",          "orm_Latn": "Kana qoraanya fudhaa",               "amh_Ethi": "ይህን መድሀኒት ይውሰዱ"},
    {"eng_Latn": "take medicine with food",     "orm_Latn": "Qoraanya nyaata wajjin fudhaa",      "amh_Ethi": "መድሀኒቱን ከምግብ ጋር ይውሰዱ"},
    {"eng_Latn": "drink plenty of water",       "orm_Latn": "Bishaan baay'ee dhugi",              "amh_Ethi": "ብዙ ውሃ ይጠጡ"},
    {"eng_Latn": "you need to rest",            "orm_Latn": "Boqonnaa si barbaachisa",            "amh_Ethi": "ማረፍ ያስፈልጎታል"},
    {"eng_Latn": "three times a day",           "orm_Latn": "Guyyaatti yeroo sadii",              "amh_Ethi": "በቀን ሶስት ጊዜ"},
    {"eng_Latn": "twice a day",                 "orm_Latn": "Guyyaatti yeroo lama",               "amh_Ethi": "በቀን ሁለት ጊዜ"},
    {"eng_Latn": "once a day",                  "orm_Latn": "Guyyaatti yeroo tokko",              "amh_Ethi": "በቀን አንድ ጊዜ"},
    {"eng_Latn": "where does it hurt?",         "orm_Latn": "Eessatti si dhukkuba?",              "amh_Ethi": "የት ያምናል?"},
    {"eng_Latn": "come back tomorrow",          "orm_Latn": "Boru deebi'i",                       "amh_Ethi": "ነገ ተመለስ"},
    {"eng_Latn": "good morning",                "orm_Latn": "Ganama gaarii",                      "amh_Ethi": "እንደምን አደሩ"},
    {"eng_Latn": "i need help",                 "orm_Latn": "Gargaarsi nan barbaachisa",          "amh_Ethi": "እርዳታ ያስፈልገኛል"},
    {"eng_Latn": "open your mouth",             "orm_Latn": "Afaan kee bani",                     "amh_Ethi": "አፍዎን ይክፈቱ"},
    {"eng_Latn": "take a deep breath",          "orm_Latn": "Hafuura gadi fagoo fudhaa",          "amh_Ethi": "ጥልቅ እስትንፋስ ይውሰዱ"},
    {"eng_Latn": "you need a blood test",       "orm_Latn": "Qorannoo dhiigaa si barbaachisa",   "amh_Ethi": "የደም ምርመራ ያስፈልጎታል"},
    {"eng_Latn": "rest and drink water",        "orm_Latn": "Boqo, bishaan dhugi",               "amh_Ethi": "ያርፉ እና ውሃ ይጠጡ"},
    {"eng_Latn": "i have a rash",               "orm_Latn": "Gogni na dhukkuba",                  "amh_Ethi": "ሽፍታ አለኝ"},
    {"eng_Latn": "i feel pain here",            "orm_Latn": "Asatti dhukkuba nan qaba",           "amh_Ethi": "እዚህ ያምኛል"},
    {"eng_Latn": "good afternoon",              "orm_Latn": "Guyyaa gaarii",                      "amh_Ethi": "እንደምን ዋሉ"},
    {"eng_Latn": "good evening",                "orm_Latn": "Galgala gaarii",                     "amh_Ethi": "እንደምን አመሹ"},
    {"eng_Latn": "goodbye",                     "orm_Latn": "Nagaatti",                           "amh_Ethi": "ቻው"},
    {"eng_Latn": "please",                      "orm_Latn": "Maaloo",                             "amh_Ethi": "እባክዎ"},
    {"eng_Latn": "excuse me",                   "orm_Latn": "Dhiifama",                           "amh_Ethi": "ይቅርታ"},
    {"eng_Latn": "i don't understand",          "orm_Latn": "Hin hubadhu",                        "amh_Ethi": "አልገባኝም"},
    {"eng_Latn": "can you help me?",            "orm_Latn": "Na gargaaruu dandeessaa?",           "amh_Ethi": "ልትረዱኝ ትችላላችሁ?"},
]


def _words(text: str) -> set:
    return set(text.lower().replace("?","").replace(".","").replace(",","").split())


def _best_match(text: str, source_lang: str):
    query_words = _words(text)
    best_score, best_phrase = 0, None
    for p in PHRASES:
        candidate = p.get(source_lang, "")
        if not candidate:
            continue
        if candidate.lower().strip("?") == text.lower().strip("?"):
            return p
        cand_words = _words(candidate)
        if not cand_words:
            continue
        score = len(query_words & cand_words) / max(len(query_words), len(cand_words))
        if score > best_score:
            best_score = score
            best_phrase = p
    return best_phrase if best_score >= 0.4 else None


# ── NLLB model (local only) ────────────────────────────────────
_tokenizer = None
_model = None
_model_loaded = False
import threading
_lock = threading.Lock()


def _load_model():
    global _tokenizer, _model, _model_loaded
    if _model_loaded:
        return
    MODEL = os.getenv("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL)
    _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
    _model.eval()
    _model_loaded = True


def _nllb_translate(text, source_lang, target_lang):
    # Map orm_Latn -> gaz_Latn for NLLB
    code_map = {"orm_Latn": "gaz_Latn"}
    src = code_map.get(source_lang, source_lang)
    tgt = code_map.get(target_lang, target_lang)
    with _lock:
        _load_model()
        _tokenizer.src_lang = src
        inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        _tokenizer.set_tgt_lang_special_tokens(tgt)
        bos = _tokenizer.cur_lang_code
        with torch.no_grad():
            out = _model.generate(**inputs, forced_bos_token_id=bos,
                                  max_length=512, num_beams=4)
        return _tokenizer.batch_decode(out, skip_special_tokens=True)[0].strip()


GLOSSARY = [
    {
        "term_group_id": i + 1,
        "category": "Healthcare",
        "entries": [
            {"language_code": c, "term": p[c],
             "explanation": f"Translation of: {p['eng_Latn']}",
             "review_status": "reviewed"}
            for c in ("eng_Latn", "orm_Latn", "amh_Ethi")
        ]
    }
    for i, p in enumerate(PHRASES[:12])
]


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


@app.get("/")
def root():
    return {"app": "Ethiopian Healthcare Translator", "status": "running",
            "mode": "nllb-200" if HAS_MODEL else "phrase-dictionary"}


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": HAS_MODEL and _model_loaded,
            "model": "nllb-200" if HAS_MODEL else "phrase-dictionary"}


@app.get("/languages")
def languages():
    return LANGS


@app.post("/translate")
def translate(req: TranslateRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(400, detail="Input text must not be empty.")
    if req.source_lang == req.target_lang:
        raise HTTPException(400, detail="Source and target languages must be different.")
    if req.source_lang not in CODES:
        raise HTTPException(400, detail=f"Unsupported source language: {req.source_lang}")
    if req.target_lang not in CODES:
        raise HTTPException(400, detail=f"Unsupported target language: {req.target_lang}")

    # Try NLLB if available (local), else phrase dictionary (cloud)
    if HAS_MODEL:
        try:
            result = _nllb_translate(req.text, req.source_lang, req.target_lang)
            return {"translated_text": result,
                    "source_lang": req.source_lang, "target_lang": req.target_lang}
        except Exception:
            pass  # fall through to phrase dictionary

    match = _best_match(req.text, req.source_lang)
    if match:
        return {"translated_text": match[req.target_lang],
                "source_lang": req.source_lang, "target_lang": req.target_lang}

    return {"translated_text": "[Try: 'I have a fever', 'I need a doctor', 'Hello']",
            "source_lang": req.source_lang, "target_lang": req.target_lang}


@app.get("/glossary")
def glossary(only_reviewed: bool = False, language: str = None):
    result = GLOSSARY
    if language:
        result = [
            {**g, "entries": [e for e in g["entries"] if e["language_code"] == language]}
            for g in result
        ]
    return result


@app.get("/glossary/search")
def search_glossary(q: str = "", language: str = None):
    result = GLOSSARY
    if q:
        q_lower = q.lower()
        result = [g for g in result
                  if any(q_lower in e["term"].lower() for e in g["entries"])]
    if language:
        result = [
            {**g, "entries": [e for e in g["entries"] if e["language_code"] == language]}
            for g in result
        ]
    return result
