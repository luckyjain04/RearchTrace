
import json
import re
import unicodedata
from pathlib import Path

from research_engine import ResearchEngine


DATA_DIR = Path(__file__).resolve().parent / "data"


def normalize(text):
    """Normalize Unicode, whitespace, and capitalization for exact matching."""
    text = unicodedata.normalize("NFKC", str(text or ""))
    return re.sub(r"\s+", " ", text).strip().casefold()


def load_jsonl(path):
    """Load a JSON Lines file with useful error messages."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required dataset file was not found: {path.resolve()}"
        )

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in {path} at line {line_number}: {error}"
                ) from error

            if isinstance(record, dict):
                records.append(record)

    return records


class EvidenceEngine:
    """
    Analyze claims using SciFact annotations and hybrid TF-IDF retrieval.

    Dataset annotations determine exact-match verdicts.
    Retrieved-paper similarity is used only to rank related research.
    """

    def __init__(self):
        # Uses the improved ResearchEngine from research_engine.py.
        self.search_engine = ResearchEngine()

        claims = load_jsonl(DATA_DIR / "claims_train.jsonl")
        papers = load_jsonl(DATA_DIR / "corpus.jsonl")

        self.claims_by_text = {}

        for item in claims:
            claim_text = item.get("claim")

            if isinstance(claim_text, str) and claim_text.strip():
                self.claims_by_text[normalize(claim_text)] = item

        self.papers_by_id = {
            str(paper["doc_id"]): paper
            for paper in papers
            if paper.get("doc_id") is not None
        }

    @staticmethod
    def get_abstract_sentences(paper):
        """
        Preserve original sentence positions because SciFact annotations
        refer to indices in the original abstract list.
        """
        abstract = paper.get("abstract", [])

        if isinstance(abstract, list):
            return [
                str(sentence or "").strip()
                for sentence in abstract
            ]

        if isinstance(abstract, str) and abstract.strip():
            return [abstract.strip()]

        return []

    @staticmethod
    def normalize_label(label):
        """Normalize SciFact annotation labels."""
        label = str(label or "").strip().upper()

        aliases = {
            "SUPPORTS": "SUPPORT",
            "SUPPORTED": "SUPPORT",
            "CONTRADICTS": "CONTRADICT",
            "CONTRADICTED": "CONTRADICT",
            "REFUTES": "CONTRADICT",
            "REFUTED": "CONTRADICT",
            "NOT ENOUGH INFO": "NOT_ENOUGH_INFO",
            "NOT_ENOUGH_INFORMATION": "NOT_ENOUGH_INFO",
            "NEI": "NOT_ENOUGH_INFO",
        }

        return aliases.get(label, label or "UNKNOWN")

    def extract_evidence(self, annotations):
        """Extract annotated evidence sentences and source papers."""
        evidence_results = []
        source_papers = {}
        annotation_labels = set()

        if not isinstance(annotations, dict):
            return evidence_results, source_papers, annotation_labels

        for raw_paper_id, items in annotations.items():
            paper_id = str(raw_paper_id)
            paper = self.papers_by_id.get(paper_id)

            if not isinstance(items, list):
                continue

            valid_items = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                label = self.normalize_label(item.get("label"))
                annotation_labels.add(label)
                valid_items.append((item, label))

            if paper is None:
                continue

            source_papers[paper_id] = paper
            sentences = self.get_abstract_sentences(paper)

            for item, label in valid_items:
                indices = item.get("sentences", [])

                if not isinstance(indices, list):
                    continue

                for raw_index in indices:
                    try:
                        sentence_index = int(raw_index)
                    except (TypeError, ValueError):
                        continue

                    if not 0 <= sentence_index < len(sentences):
                        continue

                    sentence = sentences[sentence_index]

                    if not sentence:
                        continue

                    evidence_results.append({
                        "paper_id": paper_id,
                        "title": paper.get("title", "Untitled"),
                        "label": label,
                        "sentence": sentence,
                        "sentence_index": sentence_index,
                    })

        # Remove duplicate evidence while preserving order.
        unique_evidence = []
        seen = set()

        for item in evidence_results:
            key = (
                item["paper_id"],
                item["sentence_index"],
                item["label"],
                item["sentence"],
            )

            if key not in seen:
                seen.add(key)
                unique_evidence.append(item)

        return unique_evidence, source_papers, annotation_labels

    def analyze(self, claim, top_k=5):
        """Analyze one claim and retrieve related research papers."""
        claim = str(claim or "").strip()

        if not claim:
            return {
                "verdict": "Insufficient evidence",
                "message": "Please enter a scientific claim.",
                "evidence": [],
                "papers": [],
                "annotated_paper_ids": [],
                "exact_match": False,
            }

        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5

        top_k = max(1, min(top_k, 100))

        matching_claim = self.claims_by_text.get(normalize(claim))

        evidence_results = []
        source_papers = {}
        annotation_labels = set()

        verdict = "Insufficient evidence"

        if matching_claim is not None:
            annotations = matching_claim.get("evidence") or {}

            (
                evidence_results,
                source_papers,
                annotation_labels,
            ) = self.extract_evidence(annotations)

            has_support = "SUPPORT" in annotation_labels
            has_contradiction = "CONTRADICT" in annotation_labels

            if has_support and has_contradiction:
                verdict = "Mixed evidence"
            elif has_support:
                verdict = "Supports"
            elif has_contradiction:
                verdict = "Refutes"

            if evidence_results:
                message = (
                    "Verdict based on SciFact's annotated evidence for "
                    "this exact claim. This is a dataset-based label, "
                    "not an independent scientific verification."
                )
            elif annotation_labels:
                message = (
                    "This claim matches an annotated SciFact claim, but "
                    "no valid evidence sentences could be extracted from "
                    "the local corpus."
                )
            else:
                message = (
                    "This claim matches a SciFact training claim, but "
                    "no usable annotation labels were found."
                )
        else:
            message = (
                "This claim does not exactly match an annotated SciFact "
                "training claim. Related papers are provided for exploration. "
                "Text similarity alone cannot determine whether a claim "
                "is scientifically true or false."
            )

        # Use hybrid TF-IDF retrieval from research_engine.py.
        retrieved = self.search_engine.search(claim, top_k=top_k)
        papers_by_id = {}

        for paper in retrieved:
            paper_copy = dict(paper)
            raw_id = paper_copy.get("doc_id")

            if raw_id is None:
                continue

            paper_id = str(raw_id)
            paper_copy["doc_id"] = paper_id
            paper_copy["is_annotated_source"] = (
                paper_id in source_papers
            )

            if not paper_copy.get("title"):
                corpus_paper = self.papers_by_id.get(paper_id, {})
                paper_copy["title"] = corpus_paper.get(
                    "title", "Untitled"
                )

            papers_by_id[paper_id] = paper_copy

        # Ensure annotated evidence sources are available even when
        # ordinary retrieval did not rank them in the top results.
        for paper_id, source in source_papers.items():
            if paper_id in papers_by_id:
                papers_by_id[paper_id]["is_annotated_source"] = True
                continue

            abstract_sentences = self.get_abstract_sentences(source)

            papers_by_id[paper_id] = {
                "doc_id": paper_id,
                "title": source.get("title", "Untitled"),
                "abstract": " ".join(
                    sentence
                    for sentence in abstract_sentences
                    if sentence
                ),
                "similarity": 0.0,
                "is_annotated_source": True,
            }

        return {
            "verdict": verdict,
            "message": message,
            "evidence": evidence_results,
            "papers": list(papers_by_id.values()),
            "annotated_paper_ids": list(source_papers.keys()),
            "exact_match": matching_claim is not None,
        }


if __name__ == "__main__":
    engine = EvidenceEngine()

    claim = input("Enter a scientific claim: ").strip()
    result = engine.analyze(claim, top_k=10)

    print("\nVERDICT:", result["verdict"])
    print(result["message"])
    print("Exact annotated claim match:", result["exact_match"])
    print("Annotated source papers:", len(result["annotated_paper_ids"]))
    print("Extracted evidence sentences:", len(result["evidence"]))

    if result["evidence"]:
        print("\nANNOTATED EVIDENCE:")

        for item in result["evidence"]:
            print(f"\nPaper: {item['title']}")
            print(f"Paper ID: {item['paper_id']}")
            print(f"Label: {item['label']}")
            print(f"Sentence index: {item['sentence_index']}")
            print(f"Sentence: {item['sentence']}")
    else:
        print("\nNo valid annotated evidence sentences were extracted.")

    print("\nRELATED PAPERS AND ANNOTATED SOURCES:")

    for index, paper in enumerate(result["papers"], start=1):
        marker = (
            " [ANNOTATED EVIDENCE SOURCE]"
            if paper.get("is_annotated_source")
            else ""
        )

        print(f"\n{index}. {paper['title']}{marker}")
        print(f"Paper ID: {paper['doc_id']}")
        print(f"Similarity: {paper.get('similarity', 0):.3f}")
