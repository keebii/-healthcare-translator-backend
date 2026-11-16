"""Healthcare glossary service.

Provides reviewed medical terms and plain-language explanations in the three
supported languages. The structure mirrors the ERD in the documentation:

    Language      -> language_id (PK), language_name, language_code
    GlossaryEntry -> entry_id (PK), term_group_id, language_id (FK),
                     term, explanation, review_status

For the prototype the glossary lives in memory. It can later be moved to a
database without changing the API contract. Per the project guideline, entries
are marked ``review_status="draft"`` until checked by qualified language
speakers and healthcare reviewers; only ``reviewed`` entries are served by
default.
"""

from dataclasses import dataclass, field

from .languages import LANGUAGES_BY_CODE, is_supported


@dataclass
class GlossaryEntry:
    """A single language rendering of a medical concept."""

    language_code: str
    term: str
    explanation: str
    review_status: str = "draft"  # "draft" | "reviewed"


@dataclass
class GlossaryGroup:
    """A medical concept shared across the supported languages."""

    term_group_id: int
    category: str
    entries: list[GlossaryEntry] = field(default_factory=list)

    def entry_for(self, language_code: str) -> GlossaryEntry | None:
        for entry in self.entries:
            if entry.language_code == language_code:
                return entry
        return None


# --------------------------------------------------------------------------
# Seed content.
#
# NOTE: The terms and explanations below are provided as a starting point for
# the prototype. They MUST be reviewed by competent language speakers and a
# qualified healthcare professional before being treated as verified content.
# --------------------------------------------------------------------------
_SEED_GROUPS: list[GlossaryGroup] = [
    GlossaryGroup(
        term_group_id=1,
        category="Symptom",
        entries=[
            GlossaryEntry("eng_Latn", "Fever", "A higher than normal body temperature, often a sign of infection.", "reviewed"),
            GlossaryEntry("orm_Latn", "Hoo'a", "Qabxeeffannoo gubbee-caasaa, yeroo baay'ee mallattoo fuduraa (infekshinii) agarsiisa.", "draft"),
            GlossaryEntry("amh_Ethi", "ትኩሳት", "የተለመደውን ያለፈ የሰውነት ሙቀት፣ ብዙ ጊዜ የበሽታ መግለጫ ነው።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=2,
        category="Symptom",
        entries=[
            GlossaryEntry("eng_Latn", "Headache", "Pain in the head or upper neck.", "reviewed"),
            GlossaryEntry("orm_Latn", "Mataa-dhibee", "Dhibbi mataa ykn mormaa ol-geessaa.", "draft"),
            GlossaryEntry("amh_Ethi", "ራስ ምታት", "በራስ ወይም በአንገት አናት የሚሰማ ህመም።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=3,
        category="Symptom",
        entries=[
            GlossaryEntry("eng_Latn", "Cough", "A sudden expulsion of air from the lungs, often due to irritation.", "reviewed"),
            GlossaryEntry("orm_Latn", "Sanaa'uu", "Qilleensa of-saan siliifanii baasuu, yeroo baay'ee sababa aja'ibsuuti.", "draft"),
            GlossaryEntry("amh_Ethi", "ሳንባ መሳከክ", "ከሳንባ አየር በፍጥነት የመውጣት ሂደት፣ ብዙ ጊዜ በመከካካሪ ምክንያት።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=4,
        category="Instruction",
        entries=[
            GlossaryEntry("eng_Latn", "Take medicine with food", "Consume the medication during or after a meal to reduce stomach upset.", "reviewed"),
            GlossaryEntry("orm_Latn", "Qoraanya nyaata wajjin fudhaa", "Qoraanyi dodaan-niyaataa hin-qajaabuf nyaata wajjin ykn booda isaa fudhadhaa.", "draft"),
            GlossaryEntry("amh_Ethi", "መድሀኒትን ከምግብ ጋር ይውሰዱ", "የሆድ ህመም እንዳይከሰት መድሀኒቱን ከምግብ ጋር ወይም ከምግብ በኋላ ይውሰዱ።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=5,
        category="Instruction",
        entries=[
            GlossaryEntry("eng_Latn", "Drink plenty of water", "Stay hydrated by drinking fluids regularly.", "reviewed"),
            GlossaryEntry("orm_Latn", "Bishaan baay'ee dhangala'aa", "Bishaan yeroo walirraa dhangala'aa jiraadhaa.", "draft"),
            GlossaryEntry("amh_Ethi", "ብዙ ውሃ ይጠጡ", "በመደበኛነት ፈሳሽ በመጠጣት አካልዎን አስገባ።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=6,
        category="Medicine",
        entries=[
            GlossaryEntry("eng_Latn", "Painkiller", "Medication used to relieve pain, such as paracetamol.", "reviewed"),
            GlossaryEntry("orm_Latn", "Qoraanya dhibbii", "Dhibbii akka paraseetamoolitti hir'isuuf gargaaru qoraanya.", "draft"),
            GlossaryEntry("amh_Ethi", "የህመም ማስታገሻ", "እንደ ፓራሲታሞል ያሉ ህመምን ለማስታገስ የሚሰጡ መድሀኒቶች።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=7,
        category="Medicine",
        entries=[
            GlossaryEntry("eng_Latn", "Antibiotics", "Medicines that fight bacterial infections; must be taken as prescribed.", "reviewed"),
            GlossaryEntry("orm_Latn", "Anibiyeetikii", "Fuduraa baakteeriyaa (bacterial infection) falmuu danda'u qoraanya; akka kennametti fudhaani.", "draft"),
            GlossaryEntry("amh_Ethi", "አንቲባዮቲክስ", "የባክቴሪያ ኢንፌክሽንን የሚዋጉ መድሀኒቶች፤ እንደተወሰነው መጠን መውሰድ ይኖርባል።", "draft"),
        ],
    ),
    GlossaryGroup(
        term_group_id=8,
        category="Body part",
        entries=[
            GlossaryEntry("eng_Latn", "Chest", "The front part of the body between the neck and abdomen.", "reviewed"),
            GlossaryEntry("orm_Latn", "Hudhaa", "Qabxiifi qaama fuulduraa mormaa fi gadii giddu jiru.", "draft"),
            GlossaryEntry("amh_Ethi", "ደረት", "የሰውነት የፊት ክፍል ከአንገትና ከሆድ መካከል የሚገኝ።", "draft"),
        ],
    ),
]


class GlossaryService:
    """Read-only access to the healthcare glossary terms."""

    def __init__(self, groups: list[GlossaryGroup] | None = None) -> None:
        self._groups = list(groups) if groups else list(_SEED_GROUPS)

    def list_terms(
        self, only_reviewed: bool = True, language: str | None = None
    ) -> list[GlossaryGroup]:
        """Return glossary groups, optionally filtered.

        Args:
            only_reviewed: When True, groups only kept if their entry for the
                requested language (or any language) is reviewed.
            language: Optional NLLB-200 code to filter explanations by.
        """
        if language is not None and not is_supported(language):
            return []

        result: list[GlossaryGroup] = []
        for group in self._groups:
            entries = group.entries
            if language is not None:
                entries = [e for e in group.entries if e.language_code == language]
            if only_reviewed:
                reviewed = [e for e in entries if e.review_status == "reviewed"]
                if not reviewed:
                    continue
                entries = reviewed
            result.append(
                GlossaryGroup(
                    term_group_id=group.term_group_id,
                    category=group.category,
                    entries=[
                        GlossaryEntry(
                            e.language_code, e.term, e.explanation, e.review_status
                        )
                        for e in entries
                    ],
                )
            )
        return result

    def search(self, query: str, language: str | None = None) -> list[GlossaryGroup]:
        """Case-insensitive search over term and explanation text."""
        q = query.strip().lower()
        if not q:
            return self.list_terms(language=language)

        matches: list[GlossaryGroup] = []
        for group in self.list_terms(only_reviewed=False, language=language):
            if any(
                q in e.term.lower() or q in e.explanation.lower()
                for e in group.entries
            ):
                matches.append(group)
        return matches

    def by_language_info(self, language_code: str) -> list[dict]:
        """Return reviewed glossary entries flattened for one language."""
        if not is_supported(language_code):
            return []
        out = []
        for group in self.list_terms(only_reviewed=True):
            entry = group.entry_for(language_code)
            if entry is not None:
                out.append(
                    {
                        "term_group_id": group.term_group_id,
                        "category": group.category,
                        "term": entry.term,
                        "explanation": entry.explanation,
                    }
                )
        return out

    @staticmethod
    def language_name(code: str) -> str | None:
        lang = LANGUAGES_BY_CODE.get(code)
        return lang.name if lang else None


# Module-level singleton used by the API routes.
glossary = GlossaryService()
