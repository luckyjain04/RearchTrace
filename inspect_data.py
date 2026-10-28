
import json
from pathlib import Path
from pprint import pprint

path = Path("data/claims_train.jsonl")

with path.open("r", encoding="utf-8") as file:
    for i, line in enumerate(file):
        claim = json.loads(line)

        print("\n" + "=" * 60)
        print("CLAIM:", claim["claim"])
        print("CLAIM ID:", claim["id"])

        print("\nEVIDENCE:")
        pprint(claim["evidence"])

        print("\nCITED PAPER IDS:")
        pprint(claim["cited_doc_ids"])

        if i == 2:
            break
