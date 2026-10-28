
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(__file__).resolve().parent / "data"
CORPUS_FILE = DATA_DIR / "corpus.jsonl"


# ============================================================
# SCIENTIFIC CONCEPTS AND SYNONYMS
# ============================================================

# Each concept contains related scientific terms.
# Specific terms are preferred over generic terms during ranking.

CONCEPTS = {
    "creatine": [
        "creatine monohydrate",
        "creatine supplementation",
        "creatine supplement",
        "phosphocreatine",
        "creatine kinase",
        "creatine",
    ],
    "muscle": [
        "resistance training",
        "strength training",
        "muscle strength",
        "muscle mass",
        "muscle function",
        "exercise performance",
        "physical performance",
        "skeletal muscle",
    ],
    "cognition": [
        "cognitive function",
        "cognitive performance",
        "cognitive impairment",
        "memory",
        "brain function",
        "neuroprotection",
        "cognition",
    ],
    "kidney": [
        "glomerular filtration rate",
        "estimated glomerular filtration rate",
        "renal function",
        "kidney function",
        "renal impairment",
        "kidney injury",
        "serum creatinine",
        "creatinine",
        "renal",
        "kidney",
    ],
    "gut microbiome": [
        "microbiota gut brain axis",
        "microbiota-gut-brain axis",
        "intestinal microbiota",
        "intestinal microbiome",
        "gastrointestinal microbiota",
        "gut microbiota",
        "gut microbiome",
        "gut bacteria",
        "intestinal bacteria",
        "gut microbial",
        "intestinal microbial",
        "microbial community",
        "microbial communities",
        "gut microbes",
        "intestinal microbes",
        "gut flora",
        "microbiome",
        "microbiota",
    ],
    "digestion": [
        "nutrient absorption",
        "gastrointestinal function",
        "digestive system",
        "digestive health",
        "intestinal metabolism",
        "digestion",
    ],
    "immunity": [
        "immune response",
        "immune regulation",
        "immune system",
        "host immunity",
        "immune function",
        "inflammation",
        "inflammatory response",
    ],
    "mood": [
        "psychological well-being",
        "mental health",
        "gut-brain axis",
        "depressive symptoms",
        "depression",
        "anxiety",
        "mood",
    ],
    "vitamin c": [
        "ascorbic acid",
        "ascorbate",
        "vitamin c",
    ],
    "common cold": [
        "upper respiratory tract infection",
        "upper respiratory infection",
        "common cold",
        "cold symptoms",
        "respiratory infection",
    ],
    "vitamin d": [
        "25-hydroxyvitamin d",
        "cholecalciferol",
        "vitamin d",
    ],
    "folate": [
        "folic acid",
        "vitamin b9",
        "folate",
    ],
    "homocysteine": [
        "plasma homocysteine",
        "serum homocysteine",
        "homocysteine",
    ],
    "smoking": [
        "cigarette smoking",
        "tobacco smoking",
        "tobacco use",
        "smokers",
        "smoking",
    ],
    "lung cancer": [
        "pulmonary carcinoma",
        "lung neoplasms",
        "lung cancer",
    ],
    "prion": [
        "abnormal prion protein",
        "prion protein",
        "prpsc",
        "prion disease",
        "prion",
    ],
}


# Terms that can identify a concept even when the exact phrase
# used in the claim differs from the terminology in a paper.

ALIASES = {
    "ascorbate": "vitamin c",
    "ascorbic acid": "vitamin c",
    "creatine monohydrate": "creatine",
    "creatine supplementation": "creatine",
    "phosphocreatine": "creatine",
    "creatine kinase": "creatine",
    "gut microbiota": "gut microbiome",
    "intestinal microbiota": "gut microbiome",
    "intestinal microbiome": "gut microbiome",
    "gastrointestinal microbiota": "gut microbiome",
    "gut bacteria": "gut microbiome",
    "gut microbes": "gut microbiome",
    "intestinal bacteria": "gut microbiome",
    "intestinal microbes": "gut microbiome",
    "microbiota": "gut microbiome",
    "microbiome": "gut microbiome",
    "microbial communities": "gut microbiome",
    "microbial community": "gut microbiome",
    "renal": "kidney",
    "renal function": "kidney",
    "kidney function": "kidney",
    "glomerular filtration": "kidney",
    "folic acid": "folate",
    "vitamin b9": "folate",
    "pulmonary carcinoma": "lung cancer",
    "lung neoplasms": "lung cancer",
    "abnormal prion protein": "prion",
}


# When a claim contains a subject and an outcome/facet, prioritize the
# principal subject and require at least one other detected claim concept
# to appear in a candidate paper. This prevents generic text overlap from
# making an unrelated paper look directly relevant.
PRIMARY_CONCEPT_PRIORITY = [
    "creatine",
    "gut microbiome",
    "vitamin c",
    "vitamin d",
    "folate",
    "homocysteine",
    "smoking",
    "lung cancer",
    "prion",
    "common cold",
    "kidney",
    "muscle",
    "cognition",
    "digestion",
    "immunity",
    "mood",
]


# Generic words should not independently trigger a scientific topic.
# For example, "supplementation" alone should not imply creatine.

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "of", "to", "for", "and", "or", "in", "on", "with",
    "by", "from", "that", "this", "these", "those", "does", "do",
    "can", "could", "may", "might", "over", "under", "into",
    "without", "have", "has", "had", "their", "they", "them",
    "its", "it", "very", "more", "less", "even", "heavily",
    "influence", "influences", "improve", "improves", "improving",
    "prevent", "prevents", "prevention", "safely", "safe",
    "causing", "cause", "causes", "outcomes", "individuals",
    "human", "healthy", "trillions", "daily", "time",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def abstract_to_text(abstract):
    """Convert a list, string, or missing abstract into plain text."""
    if abstract is None:
        return ""

    if isinstance(abstract, list):
        parts = []

        for item in abstract:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    parts.append(str(text))
            elif item is not None:
                parts.append(str(item))

        return " ".join(parts)

    if isinstance(abstract, str):
        return abstract

    return str(abstract)


def normalize_claim(claim):
    """Normalize whitespace without altering the scientific claim."""
    if claim is None:
        return ""

    return re.sub(r"\s+", " ", str(claim)).strip()


def normalize_for_matching(text):
    """Normalize punctuation and case for concept matching."""
    text = normalize_claim(text).casefold()
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=2048)
def _compiled_phrase_regex(phrase):
    """Return a cached regular expression for a normalized phrase."""
    phrase = normalize_for_matching(phrase)

    if not phrase:
        return None

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])"
    )

    return re.compile(pattern)


def _phrase_in_normalized_text(phrase, normalized_text):
    """Match against text that has already been normalized."""
    if not normalized_text:
        return False

    pattern = _compiled_phrase_regex(phrase)
    return pattern is not None and pattern.search(normalized_text) is not None


def phrase_in_text(phrase, text):
    """Normalize text once and check a whole phrase safely."""
    normalized_text = normalize_for_matching(text)
    return _phrase_in_normalized_text(phrase, normalized_text)


def tokenize(text):
    """Create a set of informative, normalized word tokens."""
    return {
        word
        for word in re.findall(r"[a-z0-9]+", str(text).casefold())
        if len(word) > 2 and word not in STOPWORDS
    }


# ============================================================
# DATA LOADING
# ============================================================

def load_papers():
    """Load and deduplicate papers from the local SciFact corpus."""
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Corpus file not found: {CORPUS_FILE}\n"
            "Make sure data/corpus.jsonl exists."
        )

    papers = []

    with CORPUS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                continue

            doc_id = paper.get("doc_id", paper.get("id", ""))
            title = str(paper.get("title") or "").strip()
            abstract = abstract_to_text(
                paper.get("abstract", "")
            ).strip()

            if not title and not abstract:
                continue

            papers.append({
                "doc_id": str(doc_id),
                "title": title,
                "abstract": abstract,
                "search_text": f"{title}. {abstract}".strip(),
            })

    if not papers:
        raise ValueError(
            f"No usable research papers were loaded from {CORPUS_FILE}"
        )

    df = pd.DataFrame(papers)

    df = df.drop_duplicates(
        subset=["doc_id"],
        keep="first",
    ).reset_index(drop=True)

    return df


# ============================================================
# SCIENTIFIC CONCEPT DETECTION
# ============================================================

def _claim_concepts(claim):
    """
    Detect scientific concepts explicitly present in a claim.

    Detection is based on phrases and word boundaries, not generic
    words such as 'supplementation' or 'performance' by themselves.
    """
    text = normalize_for_matching(claim)
    found = []

    # Detect aliases first, prioritizing specific phrases.
    for phrase, canonical in sorted(
        ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if phrase_in_text(phrase, text):
            if canonical not in found:
                found.append(canonical)

    # Detect concept-specific terminology.
    for canonical, phrases in CONCEPTS.items():
        if canonical in found:
            continue

        if any(phrase_in_text(phrase, text) for phrase in phrases):
            found.append(canonical)

    # Natural phrasing such as "microbes in the human gut" does not
    # necessarily contain the literal phrase "gut microbiome".
    has_gut = phrase_in_text("gut", text) or phrase_in_text(
        "intestinal", text
    )

    has_microbes = any(
        phrase_in_text(term, text)
        for term in [
            "microbe", "microbes", "microbial", "microbiome",
            "microbiota", "bacteria", "bacterial",
        ]
    )

    if has_gut and has_microbes and "gut microbiome" not in found:
        found.insert(0, "gut microbiome")

    return found


def expand_scientific_query(claim):
    """
    Build a restrained retrieval query using the original claim
    and synonyms for its detected scientific concepts.

    Expansion is for paper retrieval only. It must never be used
    to determine the evidence verdict.
    """
    original = normalize_claim(claim)

    if not original:
        return ""

    expanded = [original]
    concepts = _claim_concepts(original)

    # Limit expansion to a few detected concepts so that unrelated
    # secondary ideas do not overwhelm the original scientific claim.
    for concept in concepts[:3]:
        phrases = CONCEPTS.get(concept, [])

        # Keep the most informative synonyms and avoid very broad terms.
        for phrase in phrases[:5]:
            if len(phrase.split()) >= 2 or phrase in {
                "creatine", "microbiome", "microbiota", "cognition",
                "kidney", "folate", "homocysteine", "prion",
            }:
                expanded.append(phrase)

    return " ".join(dict.fromkeys(expanded))


# ============================================================
# RESEARCH SEARCH ENGINE
# ============================================================

class ResearchEngine:
    """Hybrid retrieval over the local SciFact research corpus."""

    def __init__(self):
        self.papers = load_papers()

        titles = self.papers["title"].fillna("").astype(str)
        abstracts = self.papers["abstract"].fillna("").astype(str)
        combined_text = self.papers["search_text"].fillna("").astype(str)

        self.document_count = len(self.papers)

        # Title matching: titles are highly informative for relevance.
        self.title_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=30000,
            sublinear_tf=True,
        )

        self.title_matrix = self.title_vectorizer.fit_transform(titles)

        # Full text: captures relevant terms found in abstracts.
        self.word_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=50000,
            sublinear_tf=True,
        )

        self.word_matrix = self.word_vectorizer.fit_transform(
            combined_text
        )

        # Character matching helps with spelling variations and word forms.
        self.char_vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=50000,
            min_df=2,
            sublinear_tf=True,
        )

        self.char_matrix = self.char_vectorizer.fit_transform(
            combined_text
        )

        # Count matrix used for BM25 scoring.
        self.bm25_vectorizer = CountVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=100000,
            dtype=np.float32,
        )

        self.bm25_matrix = self.bm25_vectorizer.fit_transform(
            combined_text
        ).tocsr()

        self.document_lengths = np.asarray(
            self.bm25_matrix.sum(axis=1)
        ).ravel()

        self.average_document_length = float(
            self.document_lengths.mean()
        )

        document_frequency = np.asarray(
            self.bm25_matrix.getnnz(axis=0)
        ).ravel()

        self.bm25_idf = np.log(
            1.0
            + (
                self.document_count - document_frequency + 0.5
            )
            / (document_frequency + 0.5)
        )

        # Pre-normalized paper text for concept matching.
        self.lower_titles = [
            normalize_for_matching(value)
            for value in titles.tolist()
        ]

        self.lower_abstracts = [
            normalize_for_matching(value)
            for value in abstracts.tolist()
        ]

        self.lower_combined = [
            f"{title} {abstract}".strip()
            for title, abstract in zip(
                self.lower_titles,
                self.lower_abstracts,
            )
        ]

        self.title_tokens = [
            tokenize(title) for title in titles.tolist()
        ]

        self.abstract_tokens = [
            tokenize(abstract) for abstract in abstracts.tolist()
        ]

        print(
            f"ResearchEngine loaded {len(self.papers)} papers."
        )

    # --------------------------------------------------------
    # MULTI-CONCEPT RELEVANCE FILTER
    # --------------------------------------------------------

    @staticmethod
    def _concept_present(concept, normalized_text):
        """Return True when any known phrase for a concept is present."""
        phrases = CONCEPTS.get(concept, [concept])
        return any(
            _phrase_in_normalized_text(phrase, normalized_text)
            for phrase in phrases
        )

    def _eligible_multi_concept_indices(self, claim):
        """
        Prefer papers matching the primary concept and another claim facet.

        If the local corpus has no paper matching both, fall back to papers
        that mention the primary concept alone. This keeps useful background
        papers visible without pretending that they test the full claim.

        Returns (indices, match_scope). A None index array means no strict
        topic filter is needed for a single-concept or unrecognized claim.
        """
        concepts = _claim_concepts(claim)
        if len(concepts) < 2:
            return None, "text_similarity"

        primary = next(
            (concept for concept in PRIMARY_CONCEPT_PRIORITY if concept in concepts),
            concepts[0],
        )
        secondary = [concept for concept in concepts if concept != primary]

        primary_matches = []
        joint_matches = []

        for index, normalized_text in enumerate(self.lower_combined):
            if not self._concept_present(primary, normalized_text):
                continue

            primary_matches.append(index)
            if any(
                self._concept_present(concept, normalized_text)
                for concept in secondary
            ):
                joint_matches.append(index)

        if joint_matches:
            return np.asarray(joint_matches, dtype=np.int64), "primary_and_secondary_topics"

        if primary_matches:
            return np.asarray(primary_matches, dtype=np.int64), "primary_topic_only"

        # No paper even matches the primary concept. Allow a clearly-labelled
        # text-similarity fallback so the local explorer does not silently
        # become empty for claims outside the local dataset's topic coverage.
        return np.asarray([], dtype=np.int64), "text_similarity_fallback"

    # --------------------------------------------------------
    # VECTOR SIMILARITY
    # --------------------------------------------------------

    @staticmethod
    def _cosine_scores(vectorizer, matrix, query):
        """Return TF-IDF cosine scores for a query."""
        query = normalize_claim(query)

        if not query:
            return np.zeros(matrix.shape[0], dtype=np.float64)

        query_vector = vectorizer.transform([query])

        if query_vector.nnz == 0:
            return np.zeros(matrix.shape[0], dtype=np.float64)

        return cosine_similarity(
            query_vector,
            matrix,
        ).ravel()

    @staticmethod
    def _normalize_scores(scores):
        """
        Normalize non-negative scores without changing their order.
        Used for BM25 only, not as a probability transformation.
        """
        scores = np.asarray(scores, dtype=np.float64)

        if scores.size == 0:
            return scores

        maximum = float(scores.max())

        if maximum <= 0:
            return np.zeros_like(scores)

        return scores / maximum

    # --------------------------------------------------------
    # BM25
    # --------------------------------------------------------

    def _bm25_scores(self, query):
        """Compute BM25-style lexical relevance scores."""
        query_vector = self.bm25_vectorizer.transform([query]).tocsr()

        query_terms = query_vector.indices
        query_counts = query_vector.data

        scores = np.zeros(
            self.document_count,
            dtype=np.float64,
        )

        if len(query_terms) == 0:
            return scores

        k1 = 1.5
        b = 0.75
        k3 = 8.0

        if self.average_document_length > 0:
            length_norm = k1 * (
                1.0 - b
                + b * self.document_lengths
                / self.average_document_length
            )
        else:
            length_norm = np.full(
                self.document_count,
                k1,
            )

        for term_index, query_frequency in zip(
            query_terms,
            query_counts,
        ):
            term_index = int(term_index)

            term_frequency = self.bm25_matrix[
                :, term_index
            ].toarray().ravel()

            numerator = term_frequency * (k1 + 1.0)
            denominator = term_frequency + length_norm

            term_score = np.divide(
                numerator,
                denominator,
                out=np.zeros_like(
                    numerator,
                    dtype=np.float64,
                ),
                where=denominator != 0,
            )

            query_weight = (
                query_frequency * (k3 + 1.0)
                / (query_frequency + k3)
            )

            scores += (
                self.bm25_idf[term_index]
                * term_score
                * query_weight
            )

        return scores

    # --------------------------------------------------------
    # CONCEPT-AWARE SCORING
    # --------------------------------------------------------

    def _topic_scores(self, claim):
        """
        Score papers for the specific scientific concepts in a claim.

        Exact phrase matches in titles receive the strongest boost.
        Abstract matches provide supporting relevance.
        A concept mentioned only in the claim does not automatically
        make every paper in a broad topic category relevant.
        """
        concepts = _claim_concepts(claim)

        scores = np.zeros(
            self.document_count,
            dtype=np.float64,
        )

        if not concepts:
            return scores

        # Primary subjects receive higher weights than secondary
        # aspects such as mood, immunity, or cognition.
        weights = {
            "creatine": 1.7,
            "gut microbiome": 1.7,
            "vitamin c": 1.7,
            "vitamin d": 1.7,
            "folate": 1.5,
            "homocysteine": 1.5,
            "smoking": 1.5,
            "lung cancer": 1.5,
            "prion": 1.7,
            "kidney": 1.3,
            "muscle": 1.2,
            "cognition": 1.1,
            "digestion": 1.0,
            "immunity": 1.0,
            "mood": 0.8,
            "common cold": 1.5,
        }

        # Determine how central a concept is in the original claim.
        # Earlier specific concepts are not required to match every
        # other concept; papers can be relevant to one facet.
        concept_weights = []

        for position, concept in enumerate(concepts):
            weight = weights.get(concept, 1.0)

            if position == 0:
                weight *= 1.25
            elif position >= 3:
                weight *= 0.75

            concept_weights.append((concept, weight))

        total_weight = sum(
            weight for _, weight in concept_weights
        )

        if total_weight <= 0:
            return scores

        for index in range(self.document_count):
            title = self.lower_titles[index]
            abstract = self.lower_abstracts[index]

            raw_score = 0.0

            for concept, weight in concept_weights:
                phrases = CONCEPTS.get(concept, [concept])

                # These strings were normalized once during engine setup.
                # Reuse them directly and avoid normalizing every phrase
                # against every paper during ranking.
                title_match = any(
                    _phrase_in_normalized_text(phrase, title)
                    for phrase in phrases
                )

                if title_match:
                    raw_score += weight
                else:
                    # An abstract match is only needed when the title did
                    # not match, so skip this work for title matches.
                    abstract_match = any(
                        _phrase_in_normalized_text(phrase, abstract)
                        for phrase in phrases
                    )

                    if abstract_match:
                        raw_score += weight * 0.30

            scores[index] = raw_score / total_weight

        return scores

    # --------------------------------------------------------
    # CLAIM TERM COVERAGE
    # --------------------------------------------------------

    def _term_coverage_scores(self, claim):
        """
        Reward papers covering distinctive words from the original claim.

        This reduces the chance that generic matches such as 'health',
        'performance', or 'treatment' dominate the results.
        """
        claim_tokens = tokenize(claim)

        scores = np.zeros(
            self.document_count,
            dtype=np.float64,
        )

        if not claim_tokens:
            return scores

        for index in range(self.document_count):
            title_tokens = self.title_tokens[index]
            abstract_tokens = self.abstract_tokens[index]

            title_overlap = len(
                claim_tokens & title_tokens
            )

            abstract_overlap = len(
                claim_tokens & abstract_tokens
            )

            # Normalize by the number of query terms, not by the
            # most highly ranked paper.
            title_coverage = title_overlap / len(claim_tokens)
            abstract_coverage = abstract_overlap / len(claim_tokens)

            scores[index] = min(
                1.0,
                0.70 * title_coverage
                + 0.30 * abstract_coverage,
            )

        return scores

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    def search(self, claim, top_k=5):
        """
        Retrieve papers related to a scientific claim.

        Returns:
            A list of dictionaries with:
            doc_id, title, abstract, similarity

        The similarity field is a ranking score, not a probability,
        confidence estimate, or scientific truth verdict.
        """
        original_claim = normalize_claim(claim)

        if not original_claim:
            return []

        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5

        if top_k <= 0:
            return []

        expanded_claim = expand_scientific_query(
            original_claim
        )

        # Score the original claim separately. This prevents added
        # synonyms from replacing the actual subject of the query.
        original_title_scores = self._cosine_scores(
            self.title_vectorizer,
            self.title_matrix,
            original_claim,
        )

        original_word_scores = self._cosine_scores(
            self.word_vectorizer,
            self.word_matrix,
            original_claim,
        )

        expanded_title_scores = self._cosine_scores(
            self.title_vectorizer,
            self.title_matrix,
            expanded_claim,
        )

        expanded_word_scores = self._cosine_scores(
            self.word_vectorizer,
            self.word_matrix,
            expanded_claim,
        )

        # Character similarity uses the original claim to reduce
        # noise introduced by expanded query terms.
        char_scores = self._cosine_scores(
            self.char_vectorizer,
            self.char_matrix,
            original_claim,
        )

        bm25_scores = self._normalize_scores(
            self._bm25_scores(expanded_claim)
        )

        topic_scores = self._topic_scores(
            original_claim
        )

        term_coverage_scores = self._term_coverage_scores(
            original_claim
        )

        # Hybrid relevance score.
        #
        # Original query relevance is emphasized over query expansion.
        # Title similarity and concept matching receive meaningful
        # weight so broad abstract-only matches are less likely to win.
        scores = (
            0.24 * original_title_scores
            + 0.22 * original_word_scores
            + 0.10 * expanded_title_scores
            + 0.08 * expanded_word_scores
            + 0.05 * char_scores
            + 0.13 * bm25_scores
            + 0.13 * topic_scores
            + 0.05 * term_coverage_scores
        )

        # For multi-concept claims, exclude papers that mention only a
        # generic background term or only one side of the claim. A paper
        # must match the primary topic plus at least one additional
        # detected facet in its title/abstract. If no paper qualifies,
        # return no local matches rather than imply false relevance.
        eligible_indices, match_scope = self._eligible_multi_concept_indices(
            original_claim
        )

        if eligible_indices is None:
            candidate_indices = np.arange(self.document_count)
        elif eligible_indices.size > 0:
            candidate_indices = eligible_indices
        else:
            # Fall back to broad textual ranking only when no paper even
            # matches the main detected topic. match_scope makes this
            # limitation explicit to the UI instead of implying relevance.
            candidate_indices = np.arange(self.document_count)

        ranked_positions = np.argsort(
            -scores[candidate_indices],
            kind="stable",
        )[:min(top_k, candidate_indices.size)]
        ranked_indices = candidate_indices[ranked_positions]

        results = []

        for index in ranked_indices:
            paper = self.papers.iloc[int(index)]

            results.append({
                "doc_id": str(paper["doc_id"]),
                "title": str(paper["title"]),
                "abstract": str(paper["abstract"]),
                "similarity": round(
                    float(scores[index]),
                    4,
                ),
                "match_scope": match_scope,
            })

        return results


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":
    engine = ResearchEngine()

    while True:
        claim = input(
            "\nEnter a scientific claim (or type 'exit'): "
        ).strip()

        if claim.casefold() in {"exit", "quit"}:
            break

        if not claim:
            print("Please enter a scientific claim.")
            continue

        results = engine.search(
            claim,
            top_k=10,
        )

        print("\nTop matching research papers:")
        print(
            "Similarity is a ranking score, "
            "not a truth probability.\n"
        )

        if not results:
            print("No matching papers found.")
            continue

        for rank, paper in enumerate(results, start=1):
            print(f"{rank}. {paper['title']}")
            print(f"   Paper ID: {paper['doc_id']}")
            print(
                f"   Similarity: {paper['similarity']:.4f}"
            )

            abstract = paper["abstract"]

            if len(abstract) > 500:
                abstract = abstract[:500].rstrip() + "..."

            print(f"   Abstract: {abstract}\n")
