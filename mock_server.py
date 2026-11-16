"""Demo translation backend (pure standard library, no dependencies).

Improvements over v1:
- Fuzzy/partial matching: finds the closest phrase even if the user's
  input isn't word-for-word exact.
- More healthcare phrases covering common symptoms and instructions.
- Welcome / info endpoint at GET / for quick browser check.

Run:  py mock_server.py      (listens on 0.0.0.0:8000)
Tunnel to phone: adb reverse tcp:8000 tcp:8000
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LANGS = [
    {"code": "eng_Latn", "name": "English",      "native": "English"},
    {"code": "orm_Latn", "name": "Afaan Oromoo",  "native": "Afaan Oromoo"},
    {"code": "amh_Ethi", "name": "Amharic",       "native": "አማርኛ"},
]
CODES = {l["code"] for l in LANGS}

# ---------------------------------------------------------------------------
# Phrase dictionary  –  each row is one concept in all three languages.
# These are the sentences the app can translate accurately.
# ---------------------------------------------------------------------------
PHRASES = [
    # Greetings
    {"eng_Latn": "hello",                       "orm_Latn": "Akkam",                              "amh_Ethi": "ሰላም"},
    {"eng_Latn": "how are you",                 "orm_Latn": "Akkam jirtu?",                       "amh_Ethi": "እንዴት ነዎት?"},
    {"eng_Latn": "how are you?",                "orm_Latn": "Akkam jirtu?",                       "amh_Ethi": "እንዴት ነዎት?"},
    {"eng_Latn": "good morning",                "orm_Latn": "Ganama gaarii",                      "amh_Ethi": "እንደምን አደሩ"},
    {"eng_Latn": "thank you",                   "orm_Latn": "Galatoomi",                          "amh_Ethi": "አመሰግናለሁ"},
    {"eng_Latn": "yes",                         "orm_Latn": "Eeyyee",                             "amh_Ethi": "አዎ"},
    {"eng_Latn": "no",                          "orm_Latn": "Lakki",                              "amh_Ethi": "አይ"},
    {"eng_Latn": "please",                      "orm_Latn": "Maaloo",                             "amh_Ethi": "እባክዎ"},
    {"eng_Latn": "help",                        "orm_Latn": "Gargaarsa",                          "amh_Ethi": "እርዳታ"},

    # Symptoms
    {"eng_Latn": "i have a fever",              "orm_Latn": "Ani hoo'a qaba",                     "amh_Ethi": "ትኩሳት ይዤአለሁ"},
    {"eng_Latn": "i have fever",                "orm_Latn": "Ani hoo'a qaba",                     "amh_Ethi": "ትኩሳት ይዤአለሁ"},
    {"eng_Latn": "i have a headache",           "orm_Latn": "Mataan na dhukkuba",                 "amh_Ethi": "ራስ ምታት አለኝ"},
    {"eng_Latn": "i have headache",             "orm_Latn": "Mataan na dhukkuba",                 "amh_Ethi": "ራስ ምታት አለኝ"},
    {"eng_Latn": "i have a cough",              "orm_Latn": "Ani sanaa'a qaba",                   "amh_Ethi": "ሳልሳ ይዤአለሁ"},
    {"eng_Latn": "i have cough",                "orm_Latn": "Ani sanaa'a qaba",                   "amh_Ethi": "ሳልሳ ይዤአለሁ"},
    {"eng_Latn": "i have stomach pain",         "orm_Latn": "Garaan na dhukkuba",                 "amh_Ethi": "ሆዴ ያምኛል"},
    {"eng_Latn": "i have chest pain",           "orm_Latn": "Hudhaan na dhukkuba",                "amh_Ethi": "ደረቴ ያምኛል"},
    {"eng_Latn": "i have back pain",            "orm_Latn": "Dugdaan na dhukkuba",                "amh_Ethi": "ጀርባዬ ያምኛል"},
    {"eng_Latn": "i feel dizzy",                "orm_Latn": "Mataan na naanna'a",                 "amh_Ethi": "ራሴ ያዞራል"},
    {"eng_Latn": "i am tired",                  "orm_Latn": "Nan dadhabe",                        "amh_Ethi": "ደክሞኛል"},
    {"eng_Latn": "i feel weak",                 "orm_Latn": "Humni hin qabu",                     "amh_Ethi": "ደካማ ሆኛለሁ"},
    {"eng_Latn": "i have diarrhea",             "orm_Latn": "Garaan na baayyise",                 "amh_Ethi": "ተቅማጥ አለብኝ"},
    {"eng_Latn": "i am vomiting",               "orm_Latn": "Nan aarsa",                          "amh_Ethi": "ማስታወክ አለብኝ"},
    {"eng_Latn": "i have difficulty breathing", "orm_Latn": "Hafuura na rakkisa",                 "amh_Ethi": "መተንፈስ ይከብደኛል"},
    {"eng_Latn": "i have a sore throat",        "orm_Latn": "Mormi na dhukkuba",                  "amh_Ethi": "ጉሮሮዬ ያምኛል"},
    {"eng_Latn": "i have a rash",               "orm_Latn": "Gogni na dhukkuba",                  "amh_Ethi": "ሽፍታ አለኝ"},
    {"eng_Latn": "i am pregnant",               "orm_Latn": "Ani ulfa",                           "amh_Ethi": "ነፍሰ ጡር ነኝ"},
    {"eng_Latn": "i have diabetes",             "orm_Latn": "Dhibee sukkaara qaba",               "amh_Ethi": "የስኳር ህመም አለብኝ"},
    {"eng_Latn": "i have high blood pressure",  "orm_Latn": "Dhiigni na ol ka'e",                 "amh_Ethi": "ደሜ ከፍ ብሏል"},
    {"eng_Latn": "i have malaria",              "orm_Latn": "Bofaa qaba",                         "amh_Ethi": "ወባ አለብኝ"},

    # Questions
    {"eng_Latn": "where does it hurt",          "orm_Latn": "Eessatti si dhukkuba?",              "amh_Ethi": "የት ያምናል?"},
    {"eng_Latn": "where does it hurt?",         "orm_Latn": "Eessatti si dhukkuba?",              "amh_Ethi": "የት ያምናል?"},
    {"eng_Latn": "i need a doctor",             "orm_Latn": "Doktora nan barbaada",               "amh_Ethi": "ዶክተር ያስፈልገኛል"},
    {"eng_Latn": "i need to see a doctor",      "orm_Latn": "Doktora arguun nan barbaada",        "amh_Ethi": "ዶክተር ማየት ያስፈልገኛል"},
    {"eng_Latn": "call an ambulance",           "orm_Latn": "Ambiilaansii waamu",                 "amh_Ethi": "አምቡላንስ ደውሉ"},
    {"eng_Latn": "i need help",                 "orm_Latn": "Gargaarsi nan barbaachisa",          "amh_Ethi": "እርዳታ ያስፈልገኛል"},
    {"eng_Latn": "it is an emergency",          "orm_Latn": "Ariitii barbaachisa",                "amh_Ethi": "አስቸኳይ ሁኔታ ነው"},

    # Instructions
    {"eng_Latn": "take this medicine",          "orm_Latn": "Kana qoraanya fudhaa",               "amh_Ethi": "ይህን መድሀኒት ይውሰዱ"},
    {"eng_Latn": "take medicine with food",     "orm_Latn": "Qoraanya nyaata wajjin fudhaa",      "amh_Ethi": "መድሀኒቱን ከምግብ ጋር ይውሰዱ"},
    {"eng_Latn": "drink plenty of water",       "orm_Latn": "Bishaan baay'ee dhugi",              "amh_Ethi": "ብዙ ውሃ ይጠጡ"},
    {"eng_Latn": "rest and drink water",        "orm_Latn": "Boqo, bishaan dhugi",                "amh_Ethi": "ያርፉ እና ውሃ ይጠጡ"},
    {"eng_Latn": "you need to rest",            "orm_Latn": "Boqonnaa si barbaachisa",            "amh_Ethi": "ማረፍ ያስፈልጎታል"},
    {"eng_Latn": "come back tomorrow",          "orm_Latn": "Boru deebi'i",                       "amh_Ethi": "ነገ ተመለስ"},
    {"eng_Latn": "three times a day",           "orm_Latn": "Guyyaatti yeroo sadii",              "amh_Ethi": "በቀን ሶስት ጊዜ"},
    {"eng_Latn": "twice a day",                 "orm_Latn": "Guyyaatti yeroo lama",               "amh_Ethi": "በቀን ሁለት ጊዜ"},
    {"eng_Latn": "once a day",                  "orm_Latn": "Guyyaatti yeroo tokko",              "amh_Ethi": "በቀን አንድ ጊዜ"},

    # Body parts
    {"eng_Latn": "head",                        "orm_Latn": "Mataa",                              "amh_Ethi": "ራስ"},
    {"eng_Latn": "chest",                       "orm_Latn": "Hudhaa",                             "amh_Ethi": "ደረት"},
    {"eng_Latn": "stomach",                     "orm_Latn": "Garaa",                              "amh_Ethi": "ሆድ"},
    {"eng_Latn": "back",                        "orm_Latn": "Dugda",                              "amh_Ethi": "ጀርባ"},
    {"eng_Latn": "arm",                         "orm_Latn": "Harka",                              "amh_Ethi": "ክንድ"},
    {"eng_Latn": "leg",                         "orm_Latn": "Luka",                               "amh_Ethi": "እግር"},
    {"eng_Latn": "eye",                         "orm_Latn": "Ija",                                "amh_Ethi": "ዓይን"},
    {"eng_Latn": "ear",                         "orm_Latn": "Gurra",                              "amh_Ethi": "귀"},
    {"eng_Latn": "throat",                      "orm_Latn": "Morma",                              "amh_Ethi": "ጉሮሮ"},
    {"eng_Latn": "ear",                         "orm_Latn": "Gurra",                              "amh_Ethi": "ጆሮ"},
]


def _words(text: str) -> set:
    """Return set of lowercase words from text."""
    return set(text.lower().replace("?", "").replace(".", "").replace(",", "").split())


def _best_match(text: str, source_lang: str) -> dict | None:
    """Find the best matching phrase by word-overlap score."""
    query_words = _words(text)
    best_score = 0
    best_phrase = None
    for p in PHRASES:
        candidate = p.get(source_lang, "")
        if not candidate:
            continue
        # Exact match first
        if candidate.lower().strip("?") == text.lower().strip("?"):
            return p
        # Word overlap score
        cand_words = _words(candidate)
        if not cand_words:
            continue
        overlap = len(query_words & cand_words)
        score = overlap / max(len(query_words), len(cand_words))
        if score > best_score:
            best_score = score
            best_phrase = p
    # Only use fuzzy match if at least 40% of words overlap
    if best_score >= 0.4:
        return best_phrase
    return None


def translate(text, source_lang, target_lang):
    text = (text or "").strip()
    if not text:
        return (400, {"detail": "Input text must not be empty."})
    if source_lang == target_lang:
        return (400, {"detail": "Source and target languages must be different."})
    if source_lang not in CODES:
        return (400, {"detail": f"Unsupported source language: {source_lang}"})
    if target_lang not in CODES:
        return (400, {"detail": f"Unsupported target language: {target_lang}"})

    match = _best_match(text, source_lang)
    if match:
        return (200, {
            "translated_text": match[target_lang],
            "source_lang": source_lang,
            "target_lang": target_lang,
        })

    # No match — return a clearly marked placeholder so the UI still shows output
    return (200, {
        "translated_text": f"[Translation not available in demo — try: 'I have a fever', 'I need a doctor', 'Hello']",
        "source_lang": source_lang,
        "target_lang": target_lang,
    })


GLOSSARY = [
    {
        "term_group_id": i + 1,
        "category": "Healthcare",
        "entries": [
            {"language_code": c, "term": p[c], "explanation": f"See: {p['eng_Latn']}", "review_status": "reviewed"}
            for c in ("eng_Latn", "orm_Latn", "amh_Ethi")
        ]
    }
    for i, p in enumerate(PHRASES[:12])
]


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, fmt, *args):
        print("  " + fmt % args)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/health":
            self._send(200, {"status": "ok", "model_loaded": True, "model": "demo-phrase-dictionary"})
        elif p == "/languages":
            self._send(200, LANGS)
        elif p == "/glossary":
            self._send(200, GLOSSARY)
        elif p == "/":
            self._send(200, {"app": "Ethiopian Healthcare Translator", "status": "running"})
        else:
            self._send(404, {"detail": "Not found"})

    def do_POST(self):
        if self.path == "/translate":
            try:
                data = self._body()
            except Exception:
                self._send(400, {"detail": "Invalid JSON body"})
                return
            status, payload = translate(
                data.get("text"), data.get("source_lang"), data.get("target_lang")
            )
            self._send(status, payload)
        else:
            self._send(404, {"detail": "Not found"})


if __name__ == "__main__":
    port = 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Demo backend running on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
