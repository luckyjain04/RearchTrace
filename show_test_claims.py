
import json
from pathlib import Path

DATA_FILE = Path("data") / "claims_train.jsonl"

def get_label(claim_data):
    """Identify the evidence label for a SciFact claim."""
    evidence = claim_data.get("evidence", {})
    labels = set()

    for annotations in evidence.values():
        for annotation in annotations:
            label = annotation.get("label", "").upper()

            if label:
                labels.add(label)

    if not labels:
        return "INSUFFICIENT EVIDENCE"

    if labels == {"SUPPORT"}:
        return "SUPPORTS"

    if labels == {"CONTRADICT"}:
        return "REFUTES"

    # Skip claims with mixed or unexpected evidence labels.
    return None


def main():
    if not DATA_FILE.exists():
        print(f"Dataset not found: {DATA_FILE}")
        print("Run this script from your ResearchTrace project folder.")
        return

    wanted = {
        "SUPPORTS": None,
        "REFUTES": None,
        "INSUFFICIENT EVIDENCE": None,
    }

    with DATA_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            item = json.loads(line)
            label = get_label(item)

            if label in wanted and wanted[label] is None:
                wanted[label] = item.get("claim", "")

            if all(claim is not None for claim in wanted.values()):
                break

    print("\nRESEARCHTRACE LOCAL TEST CLAIMS")
    print("=" * 45)

    for label, claim in wanted.items():
        print(f"\nExpected label: {label}")
        if claim:
            print(f"Claim: {claim}")
        else:
            print("No matching example found in this dataset.")

    print("\nCopy each claim exactly as printed into Local Research.")


if __name__ == "__main__":
    main()
