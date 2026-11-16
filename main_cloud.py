"""
Cloud deployment entry point — uses the phrase-dictionary mock server.
No torch/transformers needed, runs on any free tier (512MB RAM).

Render start command:
    uvicorn main_cloud:app --host 0.0.0.0 --port $PORT
"""

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

LANGS = [
    {"code": "eng_Latn", "name": "English",      "native": "English"},
    {"code": "orm_Latn", "name": "Afaan Oromoo",  "native": "Afaan Oromoo"},
    {"code": "amh_Ethi", "name": "Amharic",       "native": "አማርኛ"},
]
CODES = {l["code"] for l in LANGS}

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
]


def _words(text: str) -> set:
    return set(text.lower().replace("?", "").replace(".", "").replace(",", "").split())


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
        overlap = len(query_words & cand_words)
        score = overlap / max(len(query_words), len(cand_words))
        if score > best_score:
            best_score = score
            best_phrase = p
    return best_phrase if best_score >= 0.4 else None


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
    for i, p in enumerate(PHRASES[:10])
]


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True, "model": "phrase-dictionary-cloud"}


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

    match = _best_match(req.text, req.source_lang)
    if match:
        return {
            "translated_text": match[req.target_lang],
            "source_lang": req.source_lang,
            "target_lang": req.target_lang,
        }
    return {
        "translated_text": f"[Try: 'I have a fever', 'I need a doctor', 'Hello']",
        "source_lang": req.source_lang,
        "target_lang": req.target_lang,
    }


@app.get("/glossary")
def glossary():
    return GLOSSARY


@app.get("/glossary/search")
def search_glossary(q: str = ""):
    if not q:
        return GLOSSARY
    q = q.lower()
    return [g for g in GLOSSARY
            if any(q in e["term"].lower() or q in e["explanation"].lower()
                   for e in g["entries"])]
