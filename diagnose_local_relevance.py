"""Diagnose whether the local SciFact corpus contains direct matches for a claim.

Run from the ResearchTrace project folder:
    python diagnose_local_relevance.py

This is a diagnostic only. It does not alter the search engine or verdict logic.
"""

import json
import re
from pathlib import Path

CORPUS_FILE = Path("data") / "corpus.jsonl"

INTERVENTION_TERMS = (
    "vitamin c",
    "ascorbic acid",
    "ascorbate",
    "l-ascorbic acid",
)
CONDITION_DIRECT_TERMS = (
    "common cold",
    "common colds",
    "rhinovirus",
    "rhinoviruses",
    "rhinoviral",
)
CONDITION_CLOSE_TERMS = (
    "upper respiratory tract infection",
    "upper respiratory tract infections",
    "upper respiratory infection",
    "upper respiratory infections",
    "acute respiratory infection",
    "acute respiratory tract infection",
)
PREVENTION_TERMS = (
    "prevent",
    "prevents",
    "prevented",
    "preventing",
    "prevention",
    "prophylaxis",
    "incidence",
    "occurrence",
    "risk reduction",
    "reduce the risk",
    "reduced risk",
)


def as_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                part = item.get("text", "")
                if part:
                    parts.append(str(part))
            elif item is not None:
                parts.append(str(item))
        return " ".join(parts)
    return str(value)


def normalize(text):
    text = as_text(text).casefold().replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text, phrases):
    for phrase in phrases:
        pattern = r"(?<![a-z0-9])" + re.escape(normalize(phrase)) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            return True
    return False


def main():
    if not CORPUS_FILE.exists():
        print(f"ERROR: Could not find {CORPUS_FILE.resolve()}")
        print("Run this script from C:\\Users\\jainl\\ResearchTrace.")
        return

    tiers = {
        "DIRECT: intervention + common-cold/rhinovirus + prevention-related term": [],
        "CONDITION MATCH: intervention + common-cold/rhinovirus (outcome not explicit)": [],
        "CLOSE CONDITION: intervention + upper-respiratory-infection term": [],
        "INTERVENTION ONLY: vitamin C/ascorbate but no condition phrase": [],
    }
    rows = 0

    with CORPUS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            rows += 1
            title = as_text(item.get("title", ""))
            abstract = as_text(item.get("abstract", ""))
            full = normalize(title + " " + abstract)

            has_intervention = contains_any(full, INTERVENTION_TERMS)
            has_direct_condition = contains_any(full, CONDITION_DIRECT_TERMS)
            has_close_condition = contains_any(full, CONDITION_CLOSE_TERMS)
            has_prevention = contains_any(full, PREVENTION_TERMS)

            doc_id = item.get("doc_id", item.get("id", "Unknown ID"))
            entry = {
                "id": str(doc_id),
                "title": title or "(No title)",
                "has_abstract": bool(abstract.strip()),
            }

            if has_intervention and has_direct_condition and has_prevention:
                tiers["DIRECT: intervention + common-cold/rhinovirus + prevention-related term"].append(entry)
            elif has_intervention and has_direct_condition:
                tiers["CONDITION MATCH: intervention + common-cold/rhinovirus (outcome not explicit)"].append(entry)
            elif has_intervention and has_close_condition:
                tiers["CLOSE CONDITION: intervention + upper-respiratory-infection term"].append(entry)
            elif has_intervention:
                tiers["INTERVENTION ONLY: vitamin C/ascorbate but no condition phrase"].append(entry)

    print("\nRESEARCHTRACE LOCAL CORPUS DIAGNOSTIC")
    print("=" * 52)
    print(f"Corpus file: {CORPUS_FILE.resolve()}")
    print(f"Rows read: {rows}")
    print("\nPotential coverage for: Vitamin C supplementation prevents the common cold")

    for label, entries in tiers.items():
        print(f"\n{label}: {len(entries)} paper(s)")
        for item in entries[:12]:
            abstract_note = "abstract available" if item["has_abstract"] else "no abstract"
            print(f"  - ID {item['id']} | {item['title']} [{abstract_note}]")
        if len(entries) > 12:
            print(f"  ... and {len(entries) - 12} more")

    direct_count = len(tiers["DIRECT: intervention + common-cold/rhinovirus + prevention-related term"])
    condition_count = len(tiers["CONDITION MATCH: intervention + common-cold/rhinovirus (outcome not explicit)"])
    close_count = len(tiers["CLOSE CONDITION: intervention + upper-respiratory-infection term"])

    print("\nINTERPRETATION")
    if direct_count:
        print("Direct candidate papers exist in the corpus. If they do not appear near the top, ranking logic needs further tuning.")
    elif condition_count or close_count:
        print("The corpus contains some intervention-condition candidates, but none matched the simple prevention-term scan. Ranking or terminology coverage may need improvement.")
    else:
        print("This scan found no papers mentioning both vitamin C/ascorbate and a direct or close common-cold condition phrase. Local ranking cannot return direct matches that are absent; use PubMed for broader coverage or extend the local corpus.")


if __name__ == "__main__":
    main()
