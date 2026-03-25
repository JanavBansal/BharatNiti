"""Thorough end-to-end RAG pipeline tests across all document categories."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = "http://localhost:8000"

# 30 questions across all categories
TESTS = [
    # === INCOME TAX ACT 1961 — Core provisions ===
    {"q": "What deductions are available under Section 80C?", "expect_cite": ["80C"], "category": "IT_Deductions"},
    {"q": "What is the definition of 'previous year' under the Income Tax Act?", "expect_cite": ["3"], "category": "IT_Definitions"},
    {"q": "What are the heads of income under Section 14?", "expect_cite": ["14"], "category": "IT_Basics"},
    {"q": "What is the exemption limit for HRA under Section 10(13A)?", "expect_cite": ["10"], "category": "IT_Exemptions"},
    {"q": "How is income from house property calculated under Section 22-27?", "expect_cite": ["22", "23", "24"], "category": "IT_HouseProperty"},
    {"q": "What are the conditions for claiming deduction under Section 80D for health insurance?", "expect_cite": ["80D"], "category": "IT_Deductions"},

    # === CAPITAL GAINS ===
    {"q": "How is long-term capital gains tax calculated on sale of equity shares?", "expect_cite": ["112", "112A"], "category": "IT_CapGains"},
    {"q": "What is the indexation benefit for capital gains computation?", "expect_cite": ["48"], "category": "IT_CapGains"},
    {"q": "What is the exemption under Section 54 for capital gains on sale of residential house?", "expect_cite": ["54"], "category": "IT_CapGains"},

    # === TDS ===
    {"q": "What is the TDS rate on professional fees under Section 194J?", "expect_cite": ["194J"], "category": "TDS"},
    {"q": "What is the TDS rate on rent payments under Section 194I?", "expect_cite": ["194I"], "category": "TDS"},
    {"q": "When should TDS be deposited with the government?", "expect_cite": [], "category": "TDS"},
    {"q": "What is the TDS rate on interest from fixed deposits for senior citizens?", "expect_cite": ["194A"], "category": "TDS"},

    # === GST ===
    {"q": "What are the provisions for input tax credit under GST?", "expect_cite": ["16", "17", "18"], "category": "GST"},
    {"q": "What is the GST rate for restaurant services?", "expect_cite": [], "category": "GST_Rates"},
    {"q": "What is the GST rate for IT and software services?", "expect_cite": [], "category": "GST_Rates"},
    {"q": "What is the composition scheme under GST and who is eligible?", "expect_cite": ["10"], "category": "GST"},
    {"q": "What are the provisions for reverse charge mechanism under GST?", "expect_cite": ["9"], "category": "GST"},
    {"q": "What is the time limit for filing GSTR-1?", "expect_cite": [], "category": "GST"},

    # === PENALTIES & COMPLIANCE ===
    {"q": "What is the penalty for late filing of income tax return?", "expect_cite": ["234F", "271F"], "category": "IT_Penalties"},
    {"q": "What is the interest charged under Section 234A, 234B, and 234C?", "expect_cite": ["234A", "234B", "234C"], "category": "IT_Interest"},

    # === 2025 NEW LAW ===
    {"q": "What are the key changes in the new Income Tax Act 2025?", "expect_cite": [], "category": "IT_2025"},
    {"q": "When does the new Income Tax Act 2025 come into effect?", "expect_cite": [], "category": "IT_2025"},
    {"q": "How does the new Income Tax Act 2025 simplify the tax code?", "expect_cite": [], "category": "IT_2025"},

    # === BUDGET 2026 ===
    {"q": "What are the key highlights of Union Budget 2026-27?", "expect_cite": [], "category": "Budget2026"},
    {"q": "What income tax changes were proposed in Finance Bill 2026?", "expect_cite": [], "category": "Budget2026"},

    # === RATE LOOKUPS (should work via SQL) ===
    {"q": "What is the TDS rate for Section 194C payment to contractors?", "expect_cite": ["194C"], "category": "TDS_Rates"},
    {"q": "What is the income tax slab under the new regime for AY 2025-26?", "expect_cite": [], "category": "IT_Slabs"},

    # === ADVANCED / CROSS-CUTTING ===
    {"q": "What are the provisions for assessment and reassessment under the Income Tax Act?", "expect_cite": ["147", "148", "149"], "category": "IT_Assessment"},
    {"q": "What is the definition of residential status and how does it affect taxation?", "expect_cite": ["6"], "category": "IT_Residential"},
]


async def run_test(client: httpx.AsyncClient, test: dict, idx: int) -> dict:
    """Run a single test question and parse the response."""
    q = test["q"]
    try:
        resp = await client.post(f"{BASE}/api/v1/ask", json={"question": q}, timeout=60)
        if resp.status_code != 200:
            return {"idx": idx, "q": q, "status": "HTTP_ERROR", "code": resp.status_code, "confidence": "N/A", "citations": [], "category": test["category"]}

        text = resp.text
        answer_tokens = []
        citations = []
        confidence = "N/A"
        cached = False

        for line in text.split("\n"):
            if line.startswith("data: ") and not line.startswith("data: {"):
                answer_tokens.append(line[6:])
            elif line.startswith("data: {"):
                try:
                    meta = json.loads(line[6:])
                    citations = [c.get("section_number", "") for c in meta.get("citations", [])]
                    confidence = meta.get("confidence", "N/A")
                    cached = meta.get("cached", False)
                except json.JSONDecodeError:
                    pass

        answer = "".join(answer_tokens)
        answer_len = len(answer)

        # Check if expected citations were found
        expected = test.get("expect_cite", [])
        found_expected = [c for c in expected if any(c in cite for cite in citations)]
        cite_match = len(found_expected) / len(expected) if expected else 1.0

        return {
            "idx": idx,
            "q": q[:70],
            "status": "OK",
            "confidence": confidence,
            "citations": citations,
            "cite_match": cite_match,
            "answer_len": answer_len,
            "cached": cached,
            "category": test["category"],
        }
    except Exception as e:
        return {"idx": idx, "q": q[:70], "status": "ERROR", "error": str(e)[:80], "confidence": "N/A", "citations": [], "category": test["category"]}


async def main():
    print(f"Running {len(TESTS)} thorough RAG tests...\n")
    print(f"{'#':>2} {'Conf':>6} {'Cites':>5} {'Match':>5} {'Len':>5} {'Cache':>5} {'Category':<15} Question")
    print("-" * 120)

    async with httpx.AsyncClient() as client:
        results = []
        for i, test in enumerate(TESTS):
            r = await run_test(client, test, i + 1)
            results.append(r)

            status = r.get("status", "?")
            conf = r.get("confidence", "N/A")
            cites = len(r.get("citations", []))
            match = r.get("cite_match", 0)
            alen = r.get("answer_len", 0)
            cached = "Y" if r.get("cached") else "N"
            cat = r.get("category", "")

            if status == "OK":
                print(f"{r['idx']:>2} {conf:>6} {cites:>5} {match:>5.0%} {alen:>5} {cached:>5} {cat:<15} {r['q']}")
            else:
                print(f"{r['idx']:>2} {'FAIL':>6} {'--':>5} {'--':>5} {'--':>5} {'--':>5} {cat:<15} {r['q']} [{r.get('error', status)}]")

    # Summary
    print("\n" + "=" * 120)
    ok = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] != "OK"]
    high = sum(1 for r in ok if r["confidence"] == "HIGH")
    med = sum(1 for r in ok if r["confidence"] == "MEDIUM")
    low = sum(1 for r in ok if r["confidence"] == "LOW")
    with_cites = sum(1 for r in ok if r["citations"])
    avg_len = sum(r.get("answer_len", 0) for r in ok) / len(ok) if ok else 0
    cite_matches = [r["cite_match"] for r in ok if r.get("cite_match") is not None]
    avg_cite_match = sum(cite_matches) / len(cite_matches) if cite_matches else 0

    print(f"\nRESULTS: {len(ok)}/{len(TESTS)} passed, {len(failed)} failed")
    print(f"Confidence: HIGH={high} MEDIUM={med} LOW={low}")
    print(f"With citations: {with_cites}/{len(ok)}")
    print(f"Citation accuracy: {avg_cite_match:.0%} (expected sections found)")
    print(f"Avg answer length: {avg_len:.0f} chars")

    # Per-category breakdown
    print("\nPer-category:")
    categories = {}
    for r in ok:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "high": 0, "med": 0, "low": 0, "cites": 0}
        categories[cat]["count"] += 1
        if r["confidence"] == "HIGH": categories[cat]["high"] += 1
        elif r["confidence"] == "MEDIUM": categories[cat]["med"] += 1
        else: categories[cat]["low"] += 1
        if r["citations"]: categories[cat]["cites"] += 1

    for cat, stats in sorted(categories.items()):
        print(f"  {cat:<20} {stats['count']} tests | H:{stats['high']} M:{stats['med']} L:{stats['low']} | Cited:{stats['cites']}/{stats['count']}")

    if failed:
        print(f"\nFailed questions:")
        for r in failed:
            print(f"  [{r['idx']}] {r['q']} — {r.get('error', r['status'])}")


if __name__ == "__main__":
    asyncio.run(main())
