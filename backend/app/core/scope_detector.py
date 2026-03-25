"""Smart question classification and routing.

Philosophy: DEFAULT TO IN_SCOPE. Only reject questions that are clearly,
obviously not about Indian tax/finance at all (e.g., "what's the weather",
"write me a poem"). If there's any doubt, let the RAG pipeline handle it —
a bad retrieval with LOW confidence is far better than wrongly rejecting
a valid tax question.

Routes to the optimal pipeline:
- CALCULATION: Routes to SQL rate engine (has a number + tax context)
- COMPARISON: Fetches data for both regimes
- RATE_LOOKUP: Direct SQL lookup for specific rates
- IN_SCOPE: Standard RAG pipeline (the default)
- OUT_OF_SCOPE: Clearly not a tax/finance question at all
"""

import re
from dataclasses import dataclass


@dataclass
class QuestionIntent:
    scope: str  # IN_SCOPE, OUT_OF_SCOPE, RATE_LOOKUP, CALCULATION, COMPARISON
    sub_type: str | None = None
    params: dict | None = None


# ─── OUT-OF-SCOPE detection (narrow blocklist) ─────────────────────
# Only reject questions that are OBVIOUSLY not about tax/finance.
# Everything else goes to the RAG pipeline.
OUT_OF_SCOPE_PATTERNS = [
    r"^(hi|hello|hey|good morning|good evening|namaste)\s*[!?.]*$",
    r"(?:what(?:'s| is) the weather|weather forecast|temperature today)",
    r"(?:write (?:me )?(?:a |an )?(?:poem|story|essay|song|joke|recipe))",
    r"(?:who (?:is|was) (?:the )?(?:president|prime minister|ceo|actor|actress))",
    r"(?:how to (?:cook|bake|make food|lose weight|exercise|meditate))",
    r"(?:best (?:movie|restaurant|hotel|game|phone|laptop))",
    r"(?:score|match|cricket|football|ipl|world cup)(?:\s|$)",
    r"(?:translate|meaning of|define)\s+(?!section|tax|gst|tds|income)",
]

# ─── COMPARISON detection ───────────────────────────────────────────
COMPARISON_PATTERNS = [
    r"(?:old\s+(?:regime|tax)?\s*(?:vs|versus|or|compared|comparison)\s+new|new\s+(?:regime|tax)?\s*(?:vs|versus|or|compared|comparison)\s+old)",
    r"(?:old\s+vs\.?\s+new|new\s+vs\.?\s+old).*(?:regime|tax|slab)?",
    r"(?:should\s+i\s+choose|which\s+(?:regime|is\s+better)|compare\s+.*regime|better.*old.*new|better.*new.*old)",
    r"(?:difference\s+between\s+old\s+and\s+new|old\s+and\s+new\s+regime)",
]

# ─── CALCULATION detection ──────────────────────────────────────────
# Any question that contains a number AND tax-related intent
# We extract the number and route to the SQL calculator
TAX_CALC_SIGNALS = [
    "tax", "owe", "pay", "liability", "payable", "due",
    "slab", "calculate", "computation", "earning", "earn",
    "income", "salary", "ctc", "profit", "revenue",
    "how much", "kitna", "kitna",
]

# ─── RATE LOOKUP detection ──────────────────────────────────────────
RATE_PATTERNS = [
    (r"(?:what\s+is\s+the\s+(?:tds|gst|tax)\s+rate)", "rate_lookup"),
    (r"(?:tds\s+rate\s+(?:for|on|of))", "rate_lookup"),
    (r"(?:gst\s+rate\s+(?:for|on|of))", "rate_lookup"),
    (r"(?:(?:income\s+)?tax\s+slab)", "slab_lookup"),
    (r"(?:rate\s+of\s+(?:tds|tax|gst|tcs))", "rate_lookup"),
    (r"(?:section\s+194\w*\s+rate)", "rate_lookup"),
    (r"(?:tcs\s+rate\s+(?:for|on|of))", "tcs_lookup"),
    (r"(?:(?:tax\s+collected|tcs)\s+(?:at\s+source|rate))", "tcs_lookup"),
    (r"(?:cost\s+inflation\s+index|cii\s+(?:for|value|of))", "cii_lookup"),
    (r"(?:due\s+date|deadline|last\s+date)\s+(?:for|of|to)\s+(?:filing|itr|gstr|tds|return)", "deadline_lookup"),
]


def _extract_number(text: str) -> float | None:
    """Extract a monetary amount from text, handling lakhs/crores/plain numbers."""
    # Try patterns like "Rs. 50,00,000" or "₹15,00,000" or plain "5000000"
    matches = re.findall(r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|crore|crores|cr|l)?\b", text, re.IGNORECASE)

    if not matches:
        return None

    # Take the largest number found (most likely the income figure)
    best = None
    for amount_str, unit in matches:
        amount = float(amount_str.replace(",", ""))
        unit_lower = unit.lower() if unit else ""

        if unit_lower in ("crore", "crores", "cr"):
            amount *= 10_000_000
        elif unit_lower in ("lakh", "lakhs", "lac", "lacs", "l"):
            amount *= 100_000
        elif amount < 100:
            # Small number like "50" in tax context → probably lakhs
            amount *= 100_000

        if best is None or amount > best:
            best = amount

    return best


def detect_scope(question: str) -> QuestionIntent:
    """Classify the question intent for optimal routing.

    The key principle: NEVER reject a question that might be about tax.
    Only reject questions that are obviously unrelated (weather, sports, recipes).
    When in doubt → IN_SCOPE → let the RAG pipeline handle it.
    """
    q_lower = question.lower().strip()

    # ── Step 1: Check for OBVIOUSLY out-of-scope questions ──
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q_lower):
            return QuestionIntent("OUT_OF_SCOPE")

    # ── Step 2: Check for comparison questions ──
    for pattern in COMPARISON_PATTERNS:
        if re.search(pattern, q_lower):
            income = _extract_number(q_lower)
            return QuestionIntent("COMPARISON", "regime_comparison", {"income": income})

    # ── Step 3: Check for calculation questions ──
    # If the question has a number AND any tax-related signal → CALCULATION
    number = _extract_number(q_lower)
    if number and number >= 10000:  # At least ₹10,000 to be a meaningful income
        has_tax_signal = any(signal in q_lower for signal in TAX_CALC_SIGNALS)
        if has_tax_signal:
            regime = "new"
            if "old regime" in q_lower or "old tax" in q_lower:
                regime = "old"
            return QuestionIntent("CALCULATION", "income_tax_calc", {"income": number, "regime": regime})

    # ── Step 4: Check for rate lookup patterns ──
    for pattern, sub_type in RATE_PATTERNS:
        if re.search(pattern, q_lower):
            return QuestionIntent("RATE_LOOKUP", sub_type)

    # ── Step 5: DEFAULT TO IN_SCOPE ──
    # Let the RAG pipeline handle it. If chunks aren't found,
    # retriever returns empty → LOW confidence → "consult a CA" message.
    # This is always better than wrongly rejecting a valid question.
    return QuestionIntent("IN_SCOPE")
