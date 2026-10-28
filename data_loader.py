
import io
import json
import tarfile
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
ARCHIVE_URL = (
    "https://scifact.s3-us-west-2.amazonaws.com/"
    "release/latest/data.tar.gz"
)


def download_scifact():
    DATA_DIR.mkdir(exist_ok=True)

    claims_path = DATA_DIR / "claims_train.jsonl"
    corpus_path = DATA_DIR / "corpus.jsonl"

    if claims_path.exists() and corpus_path.exists():
        print("SciFact files already exist.")
        return claims_path, corpus_path

    print("Downloading SciFact dataset...")
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "ResearchTrace/1.0"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()

    with tarfile.open(
        fileobj=io.BytesIO(archive_bytes), mode="r:gz"
    ) as archive:
        members = archive.getmembers()

        for filename in ("claims_train.jsonl", "corpus.jsonl"):
            matches = [
                member for member in members
                if Path(member.name).name == filename
            ]

            if not matches:
                raise FileNotFoundError(
                    f"{filename} was not found in the archive."
                )

            source = archive.extractfile(matches[0])
            if source is None:
                raise OSError(f"Could not read {filename}")

            (DATA_DIR / filename).write_bytes(source.read())

    print("Dataset downloaded successfully.")
    return claims_path, corpus_path


def load_scifact_data():
    claims_path, corpus_path = download_scifact()

    with claims_path.open("r", encoding="utf-8") as file:
        claims = [json.loads(line) for line in file if line.strip()]

    with corpus_path.open("r", encoding="utf-8") as file:
        papers = [json.loads(line) for line in file if line.strip()]

    claims_df = pd.DataFrame(claims)
    papers_df = pd.DataFrame(papers)

    return claims_df, papers_df


if __name__ == "__main__":
    claims_df, papers_df = load_scifact_data()

    print("\nSciFact loaded successfully!")
    print("Claims:", claims_df.shape)
    print("Research papers:", papers_df.shape)

    print("\nClaim columns:")
    print(claims_df.columns.tolist())

    print("\nPaper columns:")
    print(papers_df.columns.tolist())

    print("\nExample claim:")
    print(claims_df.iloc[0]["claim"])

    print("\nExample paper:")
    print(papers_df.iloc[0]["title"])
