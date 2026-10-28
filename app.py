
import html
import re
from collections import Counter

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from evidence_engine import EvidenceEngine

try:
    from pubmed_engine import search_pubmed
    PUBMED_AVAILABLE = True
except ImportError:
    PUBMED_AVAILABLE = False


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ResearchTrace | Scientific Discovery",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# THEME AND CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg: #080b16;
        --panel: rgba(19, 24, 46, 0.82);
        --border: rgba(148, 163, 255, 0.17);
        --text: #f2f4ff;
        --muted: #a1a9c8;
        --purple: #a78bfa;
        --cyan: #67e8f9;
        --green: #86efac;
        --pink: #f0abfc;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 10% 0%, rgba(91, 63, 190, 0.22), transparent 34%),
            radial-gradient(ellipse at 92% 18%, rgba(23, 147, 190, 0.14), transparent 30%),
            radial-gradient(ellipse at 50% 100%, rgba(92, 55, 157, 0.12), transparent 35%),
            var(--bg);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(8, 11, 22, 0.78);
    }

    [data-testid="stAppViewContainer"] {
        background: transparent;
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1500px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        background: #10152a;
    }

    h1, h2, h3, h4 {
        color: var(--text) !important;
        letter-spacing: -0.035em;
    }

    p, li, label {
        color: #d8dcf1;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 30px 32px;
        border: 1px solid rgba(167, 139, 250, 0.30);
        border-radius: 24px;
        background: linear-gradient(
            135deg,
            rgba(42, 39, 89, 0.90),
            rgba(16, 29, 54, 0.90) 55%,
            rgba(14, 42, 59, 0.82)
        );
        box-shadow:
            0 22px 55px rgba(0, 0, 0, 0.28),
            inset 0 1px 0 rgba(255, 255, 255, 0.10),
            0 0 35px rgba(139, 92, 246, 0.09);
        margin-bottom: 24px;
    }

    .hero::before {
        content: "";
        position: absolute;
        width: 260px;
        height: 260px;
        right: -70px;
        top: -125px;
        border-radius: 50%;
        background: rgba(103, 232, 249, 0.09);
        filter: blur(12px);
    }

    .eyebrow {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.19em;
        text-transform: uppercase;
        color: var(--cyan);
        margin-bottom: 12px;
    }

    .hero-title {
        font-size: clamp(34px, 4vw, 52px);
        font-weight: 800;
        line-height: 1.05;
        margin: 0;
        background: linear-gradient(100deg, #ffffff 10%, #d9ccff 48%, #8cecff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        font-size: 14px;
        line-height: 1.8;
        max-width: 780px;
        color: #c0c9e7;
        margin-top: 14px;
    }

    .hero-chip {
        display: inline-block;
        margin-top: 17px;
        margin-right: 7px;
        padding: 6px 11px;
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 100px;
        background: rgba(255,255,255,0.055);
        font-size: 11px;
        color: #e2e8ff;
    }

    .section-kicker {
        color: var(--cyan);
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .section-title {
        font-size: 23px;
        font-weight: 750;
        color: var(--text);
        letter-spacing: -0.04em;
        margin-bottom: 5px;
    }

    .section-description {
        font-size: 13px;
        line-height: 1.7;
        color: var(--muted);
        margin-bottom: 17px;
    }

    .metric-card {
        border: 1px solid rgba(148, 163, 255, 0.17);
        background: linear-gradient(145deg, rgba(31, 38, 73, 0.90), rgba(17, 22, 43, 0.90));
        border-radius: 16px;
        padding: 17px 18px;
        min-height: 105px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.055);
    }

    .metric-label {
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 10px;
    }

    .metric-value {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #f7f7ff;
        overflow-wrap: anywhere;
    }

    .metric-caption {
        font-size: 10px;
        color: #9ba7c9;
        margin-top: 6px;
    }

    .verdict-card {
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 17px;
        background: linear-gradient(130deg, rgba(38, 43, 82, 0.91), rgba(17, 24, 48, 0.94));
        border: 1px solid rgba(167, 139, 250, 0.30);
        box-shadow: 0 14px 32px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.06);
    }

    .verdict-label {
        font-family: 'DM Mono', monospace;
        color: var(--purple);
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 10px;
        margin-bottom: 9px;
    }

    .verdict-value {
        color: #f7f5ff;
        font-size: 25px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .verdict-message {
        color: #c3cbe4;
        font-size: 13px;
        line-height: 1.8;
    }

    .paper-card {
        border: 1px solid rgba(148, 163, 255, 0.15);
        border-radius: 15px;
        padding: 17px 18px;
        margin-bottom: 12px;
        background: linear-gradient(130deg, rgba(25, 31, 57, 0.85), rgba(14, 20, 39, 0.90));
        box-shadow: 0 8px 22px rgba(0,0,0,0.13);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .paper-card:hover {
        border-color: rgba(103, 232, 249, 0.42);
        transform: translateY(-2px);
    }

    .paper-title {
        color: #f0f3ff;
        font-size: 14px;
        line-height: 1.6;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .paper-meta {
        color: #a9b4d5;
        font-size: 11px;
        line-height: 1.8;
    }

    .paper-abstract {
        color: #c2cbe5;
        font-size: 12px;
        line-height: 1.8;
        margin-top: 11px;
    }

    .tag {
        display: inline-block;
        font-size: 10px;
        padding: 4px 8px;
        margin: 4px 5px 0 0;
        border-radius: 100px;
        color: #d8d5ff;
        border: 1px solid rgba(167, 139, 250, 0.23);
        background: rgba(139, 92, 246, 0.10);
    }

    .source-note {
        border-left: 2px solid var(--cyan);
        padding: 10px 14px;
        background: rgba(103, 232, 249, 0.045);
        color: #bfc9e3;
        border-radius: 0 10px 10px 0;
        font-size: 12px;
        line-height: 1.8;
        margin: 12px 0 17px;
    }

    .graph-legend {
        border: 1px solid rgba(148, 163, 255, 0.16);
        border-radius: 14px;
        padding: 14px;
        margin-top: 4px;
        margin-bottom: 18px;
        background: rgba(20, 25, 48, 0.52);
    }

    .legend-title {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        color: #aebbe0;
        margin-bottom: 12px;
    }

    .legend-item {
        font-size: 12px;
        font-weight: 700;
        color: #edf0ff;
    }

    .legend-description {
        font-size: 10px;
        line-height: 1.5;
        color: #9ba8ca;
        margin-top: 4px;
    }

    .footer {
        text-align: center;
        color: #7f8aaa;
        font-size: 11px;
        line-height: 1.9;
        border-top: 1px solid rgba(148, 163, 255, 0.13);
        padding-top: 22px;
        margin-top: 38px;
    }

    .stTextInput input, .stNumberInput input {
        background: rgba(15, 20, 41, 0.88) !important;
        color: #f4f5ff !important;
        border: 1px solid rgba(148, 163, 255, 0.24) !important;
        border-radius: 12px !important;
    }

    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(15, 20, 41, 0.88) !important;
        color: #f4f5ff !important;
        border-color: rgba(148, 163, 255, 0.24) !important;
        border-radius: 11px !important;
    }

    .stButton > button, .stFormSubmitButton > button {
        border: 1px solid rgba(167, 139, 250, 0.40);
        border-radius: 11px;
        color: #ffffff;
        font-weight: 700;
        background: linear-gradient(105deg, #7555d9, #536ce0 55%, #287fa7);
        box-shadow: 0 6px 18px rgba(96, 80, 210, 0.20);
        transition: all 0.2s ease;
    }

    .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: rgba(103, 232, 249, 0.7);
        box-shadow: 0 8px 24px rgba(67, 173, 216, 0.20);
        transform: translateY(-1px);
        color: #ffffff;
    }

    div[data-testid="stTabs"] button {
        border-radius: 10px 10px 0 0;
        font-weight: 700;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #a5f3fc !important;
        border-bottom-color: #67e8f9 !important;
        background: rgba(103, 232, 249, 0.055);
    }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(148, 163, 255, 0.16);
        border-radius: 12px;
        background: rgba(20, 25, 48, 0.50);
    }

    a {
        color: #86e9fb !important;
    }

    hr {
        border-color: rgba(148, 163, 255, 0.14);
    }

    @media (max-width: 700px) {
        .hero {
            padding: 22px 20px;
        }

        .metric-value {
            font-size: 22px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

ENGINE_CACHE_VERSION = "multi-concept-relevance-v2"


@st.cache_resource
def load_evidence_engine(cache_version=ENGINE_CACHE_VERSION):
    """Cache the local evidence engine under an explicit version key."""
    return EvidenceEngine()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_pubmed_search(claim, max_results):
    """Cache repeat PubMed queries for one hour to avoid duplicate requests."""
    return search_pubmed(claim, int(max_results))


def as_text(value, default=""):
    if value is None:
        return default

    if isinstance(value, (list, tuple)):
        return ", ".join(
            str(item) for item in value if item is not None
        )

    return str(value)


def get_value(item, *keys, default=""):
    if not isinstance(item, dict):
        return default

    for key in keys:
        value = item.get(key)

        if value is not None and value != "":
            return value

    return default


def clean_text(value):
    return re.sub(r"\s+", " ", as_text(value)).strip()


def escape_html(value):
    return html.escape(as_text(value))


def truncate_text(value, limit=420):
    value = clean_text(value)

    if len(value) <= limit:
        return value

    return value[:limit].rsplit(" ", 1)[0] + "..."


def safe_similarity(paper):
    try:
        return float(
            get_value(
                paper,
                "similarity",
                "score",
                "relevance_score",
                default=0,
            )
        )
    except (ValueError, TypeError):
        return 0.0


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_paper_id(paper, fallback="paper"):
    return clean_text(
        get_value(
            paper,
            "doc_id",
            "paper_id",
            "pmid",
            "id",
            default=fallback,
        )
    )


def get_paper_title(paper):
    return clean_text(
        get_value(
            paper,
            "title",
            "paper_title",
            default="Untitled research paper",
        )
    )


def get_paper_abstract(paper):
    return clean_text(
        get_value(
            paper,
            "abstract",
            "summary",
            "description",
            default="No abstract is available from this record.",
        )
    )


def get_paper_url(paper):
    url = clean_text(
        get_value(
            paper,
            "url",
            "link",
            "paper_url",
            default="",
        )
    )

    if url.startswith(("https://", "http://")):
        return url

    pmid = get_value(
        paper,
        "pmid",
        "id",
        "doc_id",
        default="",
    )

    if str(pmid).isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    return ""


def get_pubmed_metadata(paper):
    authors = clean_text(
        get_value(paper, "authors", "author", default="")
    )
    journal = clean_text(
        get_value(
            paper,
            "journal",
            "source",
            "publication",
            default="",
        )
    )
    year = clean_text(
        get_value(
            paper,
            "year",
            "pub_year",
            "publication_year",
            "publication_date",
            default="",
        )
    )
    pmid = clean_text(
        get_value(paper, "pmid", "id", default="")
    )

    parts = []

    if journal:
        parts.append(journal)
    if year:
        parts.append(year)
    if authors:
        parts.append(authors)
    if pmid:
        parts.append(f"PMID: {pmid}")

    return " · ".join(parts) if parts else "External PubMed record"


def get_evidence_label(item):
    label = clean_text(
        get_value(
            item,
            "label",
            "verdict",
            "evidence_label",
            "stance",
            default="",
        )
    ).upper()

    if label in {"SUPPORT", "SUPPORTS", "SUPPORTED"}:
        return "SUPPORTS"

    if label in {"CONTRADICT", "CONTRADICTS", "REFUTES", "REFUTE"}:
        return "REFUTES"

    if label in {
        "NOT_ENOUGH_INFO",
        "NOT ENOUGH INFO",
        "NEI",
        "INSUFFICIENT",
    }:
        return "NOT ENOUGH INFO"

    return label or "ANNOTATED EVIDENCE"


def get_evidence_sentence(item):
    return clean_text(
        get_value(
            item,
            "evidence",
            "sentence",
            "evidence_text",
            "text",
            "snippet",
            default="No evidence sentence is available.",
        )
    )


# ============================================================
# GENERAL SCIENTIFIC TOPIC MATCHING
# ============================================================

TOPIC_GROUPS = {
    "Creatine and supplementation": [
        "creatine monohydrate", "creatine", "phosphocreatine",
        "supplementation",
    ],
    "Muscle and exercise": [
        "muscle strength", "muscle mass", "resistance training",
        "strength training", "exercise performance", "muscle",
    ],
    "Cognition and brain": [
        "cognitive function", "cognitive performance", "cognition",
        "brain", "memory", "neuroprotection",
    ],
    "Kidney and renal function": [
        "glomerular filtration", "kidney function",
        "renal function", "kidney", "renal",
    ],
    "Gut microbiome": [
        "gut microbiome", "gut microbiota", "intestinal microbiome",
        "intestinal microbiota", "gut bacteria", "microbial community",
    ],
    "Digestion and absorption": [
        "nutrient absorption", "digestion", "digestive",
        "gastrointestinal",
    ],
    "Immunity and inflammation": [
        "immune system", "immune response", "immunity",
        "inflammation", "inflammatory",
    ],
    "Mood and mental health": [
        "gut-brain axis", "mental health", "depression",
        "anxiety", "mood",
    ],
    "Vitamin C": [
        "vitamin c", "ascorbic acid", "ascorbate",
    ],
    "Common cold and respiratory illness": [
        "common cold", "cold symptoms", "upper respiratory",
        "respiratory infection",
    ],
    "Vitamin D": [
        "vitamin d", "cholecalciferol", "25-hydroxyvitamin d",
    ],
    "Folate and homocysteine": [
        "folate", "folic acid", "homocysteine", "vitamin b9",
    ],
    "Smoking and tobacco": [
        "smoking", "smoker", "tobacco", "cigarette",
    ],
    "Lung cancer": [
        "lung cancer", "pulmonary carcinoma", "lung neoplasm",
    ],
    "Prion disease": [
        "prion protein", "abnormal prp", "prpsc", "prion",
    ],
    "Clinical trials and reviews": [
        "randomized controlled trial", "randomised controlled trial",
        "systematic review", "meta-analysis", "clinical trial",
    ],
}


def detect_topics(text, limit=4):
    """Detect broad scientific topics from paper or claim text."""
    text = clean_text(text).casefold()
    matches = []

    for topic, phrases in TOPIC_GROUPS.items():
        if any(phrase in text for phrase in phrases):
            matches.append(topic)

    return matches[:limit]


# ============================================================
# CLAIM OUTCOME / INTENT MATCHING
# ============================================================

CLAIM_ASPECTS = {
    "prevention": [
        "prevent", "prevents", "preventing", "prevention",
        "prophylaxis", "incidence", "preventive",
    ],
    "treatment": [
        "treat", "treats", "treated", "treating", "treatment",
        "therapy", "therapeutic", "management", "alleviate",
        "alleviates", "cure", "curative",
    ],
    "duration": [
        "duration", "shorten", "shortens", "shortening",
        "recovery time", "time to recovery",
    ],
    "severity": [
        "severity", "severe", "symptom burden",
        "symptom severity", "symptoms",
    ],
    "safety": [
        "safe", "safety", "adverse effect", "adverse effects",
        "side effect", "side effects", "toxicity", "harm",
        "kidney damage", "renal damage",
    ],
    "dose and saturation": [
        "dose", "dosage", "low dose", "daily dose",
        "loading dose", "saturation", "saturate", "supplementation",
    ],
    "performance and efficacy": [
        "improve", "improves", "improved", "improving",
        "efficacy", "effectiveness", "performance", "benefit",
        "benefits", "effect", "effects", "outcome", "outcomes",
    ],
}


def detect_claim_aspects(text):
    """Identify the outcome or relationship described in a claim."""
    text = clean_text(text).casefold()
    detected = set()

    for aspect, phrases in CLAIM_ASPECTS.items():
        if any(phrase in text for phrase in phrases):
            detected.add(aspect)

    return detected


def get_pubmed_match_signals(paper):
    """Read the explanation attached by the PubMed ranking function."""
    if not isinstance(paper, dict):
        return []

    signals = paper.get("_researchtrace_match_signals", [])

    if isinstance(signals, str):
        return [signals] if signals else []

    return signals if isinstance(signals, list) else []


# ============================================================
# PUBMED DISPLAY RANKING
# ============================================================

def rank_pubmed_papers(papers, claim):
    """
    Rank PubMed results using topic overlap, title matches,
    and claim-outcome overlap.

    This is a display-ranking heuristic, not a truth score,
    evidence-quality score, or systematic-review assessment.
    """
    if not papers:
        return []

    claim_text = clean_text(claim).casefold()
    claim_topics = set(detect_topics(claim_text, limit=20))
    claim_aspects = detect_claim_aspects(claim_text)

    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be",
        "been", "being", "of", "to", "for", "and", "or", "in",
        "on", "with", "by", "from", "that", "this", "does", "do",
        "can", "could", "may", "might", "over", "under", "into",
        "without", "have", "has", "had", "their", "they", "them",
        "its", "it", "very", "more", "less", "even", "which",
        "who", "how", "what", "when", "where", "prevent",
        "prevents", "prevention", "improve", "improves",
        "improving", "influence", "influences",
    }

    claim_words = {
        word
        for word in re.findall(r"[a-z0-9]+", claim_text)
        if len(word) > 2 and word not in stopwords
    }

    def get_aspect_matches(text):
        text = clean_text(text).casefold()

        return {
            aspect
            for aspect, phrases in CLAIM_ASPECTS.items()
            if any(phrase in text for phrase in phrases)
        }

    ranked = []

    for original_paper in papers:
        paper = (
            dict(original_paper)
            if isinstance(original_paper, dict)
            else {}
        )

        title = get_paper_title(paper).casefold()
        abstract = get_paper_abstract(paper).casefold()
        combined_text = f"{title} {abstract}"

        title_words = set(re.findall(r"[a-z0-9]+", title))
        abstract_words = set(re.findall(r"[a-z0-9]+", abstract))

        title_overlap = len(claim_words & title_words)
        abstract_overlap = len(claim_words & abstract_words)

        paper_topics = set(
            detect_topics(combined_text, limit=20)
        )
        topic_overlap = len(claim_topics & paper_topics)

        title_aspects = get_aspect_matches(title)
        paper_aspects = get_aspect_matches(combined_text)
        aspect_overlap = len(claim_aspects & paper_aspects)

        # Give exact topic phrases additional weight when they occur
        # in the paper title.
        exact_phrase_matches = 0

        for topic, phrases in TOPIC_GROUPS.items():
            if topic not in claim_topics:
                continue

            matching_phrases = [
                phrase for phrase in phrases
                if phrase in claim_text
            ]

            if any(phrase in title for phrase in matching_phrases):
                exact_phrase_matches += 1

        score = (
            5.0 * title_overlap
            + 0.65 * abstract_overlap
            + 6.0 * topic_overlap
            + 4.0 * aspect_overlap
            + 5.0 * exact_phrase_matches
        )

        is_review = any(
            term in title
            for term in (
                "systematic review",
                "meta-analysis",
                "meta analysis",
            )
        )

        if is_review and topic_overlap > 0:
            score += 1.5

        # A treatment-focused paper may be less directly relevant to a
        # prevention claim if it does not discuss prevention at all.
        if "prevention" in claim_aspects:
            prevention_terms = (
                "prevent", "prevention", "prophylaxis", "preventive",
            )
            treatment_terms = (
                "treatment", "treated", "treating",
                "therapy", "therapeutic",
            )

            paper_mentions_prevention = any(
                term in combined_text for term in prevention_terms
            )
            paper_mentions_treatment = any(
                term in combined_text for term in treatment_terms
            )

            if (
                paper_mentions_treatment
                and not paper_mentions_prevention
            ):
                score -= 5.0

        signals = []

        if title_overlap > 0 or exact_phrase_matches > 0:
            signals.append("Title matches claim terminology")

        if topic_overlap > 0:
            signals.append("Related scientific topic")

        if aspect_overlap > 0:
            signals.append("Claim outcome also discussed")

        if is_review and topic_overlap > 0:
            signals.append("Review or meta-analysis")

        if (
            "prevention" in claim_aspects
            and "prevention" not in paper_aspects
            and "treatment" in paper_aspects
        ):
            signals.append(
                "Focus may be treatment rather than prevention"
            )

        if not signals:
            signals.append(
                "Limited direct overlap; inspect the abstract"
            )

        paper["_researchtrace_score"] = score
        paper["_researchtrace_match_signals"] = signals

        ranked.append(paper)

    return sorted(
        ranked,
        key=lambda paper: paper.get("_researchtrace_score", 0),
        reverse=True,
    )


# ============================================================
# SECTION AND METRIC HELPERS
# ============================================================

def render_section_header(kicker, title, description):
    st.markdown(
        f"""
        <div class="section-kicker">{escape_html(kicker)}</div>
        <div class="section-title">{escape_html(title)}</div>
        <div class="section-description">
            {escape_html(description)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label, value, caption=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape_html(label)}</div>
            <div class="metric-value">{escape_html(value)}</div>
            <div class="metric-caption">{escape_html(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# GRAPH CREATION
# ============================================================

def make_research_graph(
    claim,
    papers,
    graph_type="local",
    evidence=None,
    max_papers=12,
):
    """
    Local graph:
        Claim -> Paper -> Annotated evidence

    PubMed graph:
        Claim -> Paper -> Detected scientific topic
    """
    graph = nx.Graph()
    root = "research_claim"

    graph.add_node(
        root,
        label=truncate_text(claim, 48),
        kind="claim",
        hover=claim,
    )

    evidence = evidence or []
    evidence_by_paper = {}

    for item in evidence:
        paper_id = clean_text(
            get_value(
                item,
                "paper_id",
                "doc_id",
                "source_id",
                "id",
                default="",
            )
        )

        if paper_id:
            evidence_by_paper.setdefault(paper_id, []).append(item)

    for index, paper in enumerate(list(papers or [])[:max_papers]):
        paper_id = get_paper_id(paper, f"paper_{index}")
        title = get_paper_title(paper)
        paper_node = f"paper_{index}"

        graph.add_node(
            paper_node,
            label=truncate_text(title, 33),
            kind="paper",
            hover=title,
        )

        graph.add_edge(root, paper_node)

        if graph_type == "local":
            matching_evidence = evidence_by_paper.get(
                str(paper_id), []
            )

            for evidence_index, item in enumerate(matching_evidence[:2]):
                evidence_node = f"evidence_{index}_{evidence_index}"
                sentence = get_evidence_sentence(item)
                label = get_evidence_label(item)

                graph.add_node(
                    evidence_node,
                    label=truncate_text(sentence, 30),
                    kind="evidence",
                    hover=f"{label}: {sentence}",
                )

                graph.add_edge(paper_node, evidence_node)

        else:
            combined = title + " " + get_paper_abstract(paper)
            topics = detect_topics(combined, limit=3)

            if not topics:
                topics = ["Other research"]

            for topic in topics:
                topic_node = f"topic_{topic}"

                if topic_node not in graph:
                    graph.add_node(
                        topic_node,
                        label=topic,
                        kind="topic",
                        hover=(
                            "Topic inferred from title and abstract "
                            f"keywords: {topic}"
                        ),
                    )

                graph.add_edge(paper_node, topic_node)

    if graph.number_of_nodes() <= 1:
        return None

    positions = nx.spring_layout(
        graph,
        seed=23,
        k=1.15,
        iterations=90,
    )

    edge_x = []
    edge_y = []

    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1.2, color="rgba(135, 151, 211, 0.35)"),
        hoverinfo="none",
        showlegend=False,
    )

    styles = {
        "claim": {
            "color": "#a78bfa",
            "size": 31,
            "symbol": "diamond",
        },
        "paper": {
            "color": "#67e8f9",
            "size": 20,
            "symbol": "circle",
        },
        "evidence": {
            "color": "#86efac",
            "size": 14,
            "symbol": "circle",
        },
        "topic": {
            "color": "#f0abfc",
            "size": 18,
            "symbol": "hexagon",
        },
    }

    node_traces = []

    for kind in ["claim", "paper", "evidence", "topic"]:
        nodes = [
            node for node, data in graph.nodes(data=True)
            if data.get("kind") == kind
        ]

        if not nodes:
            continue

        node_x = [positions[node][0] for node in nodes]
        node_y = [positions[node][1] for node in nodes]
        labels = [
            graph.nodes[node].get("label", node)
            for node in nodes
        ]
        hover_text = [
            graph.nodes[node].get("hover", node)
            for node in nodes
        ]

        style = styles[kind]

        node_traces.append(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                text=labels,
                textposition="bottom center",
                textfont=dict(
                    size=9 if kind != "claim" else 11,
                    color="#dfe7ff",
                    family="Inter",
                ),
                hovertext=hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
                marker=dict(
                    size=style["size"],
                    color=style["color"],
                    symbol=style["symbol"],
                    opacity=0.96,
                    line=dict(color="rgba(255,255,255,0.65)", width=1),
                ),
                name=kind.title(),
                showlegend=False,
            )
        )

    fig = go.Figure(data=[edge_trace] + node_traces)

    fig.update_layout(
        height=520,
        margin=dict(l=12, r=12, t=12, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dbe4ff", family="Inter"),
        hoverlabel=dict(
            bgcolor="#171d36",
            bordercolor="#8176d9",
            font=dict(color="#f5f7ff"),
        ),
        xaxis=dict(visible=False, showgrid=False, zeroline=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False),
        dragmode="pan",
    )

    return fig


def render_graph_legend(graph_type="local"):
    if graph_type == "local":
        legend_items = [
            ("◆", "#a78bfa", "Claim",
             "The scientific claim being investigated."),
            ("●", "#67e8f9", "Paper",
             "A related paper retrieved from SciFact."),
            ("●", "#86efac", "Evidence",
             "An annotated evidence sentence, when available."),
        ]
    else:
        legend_items = [
            ("◆", "#a78bfa", "Claim",
             "The scientific claim being investigated."),
            ("●", "#67e8f9", "Paper",
             "A paper retrieved from PubMed."),
            ("⬡", "#f0abfc", "Topic",
             "A topic inferred from title and abstract keywords."),
        ]

    st.markdown(
        '<div class="graph-legend">'
        '<div class="legend-title">GRAPH KEY / NODE LEGEND</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(len(legend_items))

    for column, (symbol, color, label, description) in zip(
        columns, legend_items
    ):
        with column:
            st.markdown(
                f"""
                <div class="legend-item">
                    <span style="color:{color};font-size:18px">
                        {symbol}
                    </span>
                    {escape_html(label)}
                </div>
                <div class="legend-description">
                    {escape_html(description)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def render_graph(
    claim,
    papers,
    graph_type,
    evidence=None,
    key=None,
):
    fig = make_research_graph(
        claim=claim,
        papers=papers,
        graph_type=graph_type,
        evidence=evidence,
    )

    if fig is None:
        st.info(
            "There are not enough results to build a graph yet. "
            "Try a different claim or retrieve more papers."
        )
        return

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"researchtrace_{graph_type}_graph",
                "scale": 2,
            },
        },
        key=key,
    )

    render_graph_legend(graph_type)

    st.caption(
        "Hover over nodes to inspect them. Drag to rearrange, "
        "zoom to explore, or use the camera icon to export a PNG."
    )


# ============================================================
# PAPER CARDS
# ============================================================

def render_paper_card(
    paper,
    index,
    source="local",
    show_similarity=True,
):
    title = get_paper_title(paper)
    abstract = get_paper_abstract(paper)
    paper_id = get_paper_id(paper, str(index + 1))
    url = get_paper_url(paper)

    if source == "pubmed":
        metadata = get_pubmed_metadata(paper)
    else:
        metadata = f"Paper ID: {paper_id}"

    with st.container(border=True):
        st.markdown(f"**{index + 1:02d}. {title}**")
        st.caption(metadata)

        if show_similarity and source == "local":
            st.caption(
                f"Ranking score: {safe_similarity(paper):.3f} "
                "· Not a truth probability"
            )

        if source == "pubmed":
            signals = get_pubmed_match_signals(paper)

            if signals:
                st.caption("Match signals: " + " · ".join(signals))

        st.write(truncate_text(abstract, 360))

        with st.expander(f"Read full abstract · Paper {index + 1}"):
            st.write(abstract)

        if url:
            st.link_button(
                "Open original paper ↗",
                url,
                use_container_width=False,
            )


# ============================================================
# ANNOTATED EVIDENCE EXPLORER
# ============================================================

def render_evidence_explorer(evidence):
    if not evidence:
        st.info(
            "No annotated evidence sentences are available for this "
            "exact claim in the local SciFact data."
        )
        return

    counts = Counter(get_evidence_label(item) for item in evidence)
    columns = st.columns(3)

    for column, label in zip(
        columns, ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"]
    ):
        column.metric(label.title(), counts.get(label, 0))

    for index, item in enumerate(evidence):
        label = get_evidence_label(item)
        sentence = get_evidence_sentence(item)

        paper_id = get_value(
            item,
            "paper_id",
            "doc_id",
            "source_id",
            default="Not specified",
        )

        with st.expander(f"Evidence {index + 1} · {label}"):
            st.write(sentence)
            st.caption(f"Source paper ID: {paper_id}")


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">✦ AI-POWERED RESEARCH DISCOVERY</div>
        <div class="hero-title">ResearchTrace</div>
        <div class="hero-subtitle">
            Explore scientific claims through annotated evidence,
            research literature, and interactive knowledge graphs.
            Move from a claim to the papers connected to it —
            with separate views for the local SciFact dataset and
            external PubMed research.
        </div>
        <span class="hero-chip">SCIENCE + AI</span>
        <span class="hero-chip">EVIDENCE EXPLORATION</span>
        <span class="hero-chip">INTERACTIVE GRAPHS</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SEARCH FORM
# ============================================================

render_section_header(
    "START EXPLORING",
    "Investigate a scientific claim",
    "Search the local SciFact corpus and optionally retrieve "
    "related biomedical literature from PubMed.",
)

with st.form("research_search_form"):
    claim = st.text_input(
        "Scientific claim",
        value=st.session_state.get(
            "research_claim",
            "Vitamin C supplementation prevents the common cold.",
        ),
        placeholder="Enter a scientific claim...",
    )

    control_left, control_middle, control_right = st.columns(
        [1, 1, 1.3]
    )

    with control_left:
        local_count = st.selectbox(
            "Local papers",
            options=[5, 10, 15, 20, 30, 40, 50],
            index=1,
        )

    with control_middle:
        pubmed_count = st.selectbox(
            "PubMed papers",
            options=[5, 10, 15, 20],
            index=0,
        )

    with control_right:
        include_pubmed = st.checkbox(
            "Search external PubMed",
            value=True,
            disabled=not PUBMED_AVAILABLE,
        )

    submitted = st.form_submit_button(
        "✦  Analyse claim",
        use_container_width=True,
    )


# ============================================================
# SEARCH EXECUTION
# ============================================================

if submitted:
    if not clean_text(claim):
        st.warning("Enter a scientific claim before searching.")

    else:
        active_claim_for_search = clean_text(claim)

        st.session_state["research_claim"] = active_claim_for_search
        st.session_state["research_local_count"] = local_count
        st.session_state["research_pubmed_count"] = pubmed_count
        st.session_state["research_include_pubmed"] = include_pubmed
        st.session_state["research_pubmed_result"] = None
        st.session_state["research_pubmed_searched"] = bool(
            include_pubmed and PUBMED_AVAILABLE
        )

        # Search the local corpus independently, with its own status message.
        with st.spinner("Searching the local SciFact corpus..."):
            try:
                engine = load_evidence_engine()
                result = engine.analyze(
                    active_claim_for_search,
                    top_k=int(local_count),
                )
                st.session_state["research_local_result"] = result
                st.session_state["research_search_error"] = None
            except Exception as exc:
                st.session_state["research_local_result"] = None
                st.session_state["research_search_error"] = str(exc)

        # PubMed is optional and runs only when explicitly selected.
        if include_pubmed and PUBMED_AVAILABLE:
            with st.spinner(
                f"Searching PubMed for up to {int(pubmed_count)} papers..."
            ):
                try:
                    pubmed_result = cached_pubmed_search(
                        active_claim_for_search,
                        int(pubmed_count),
                    )

                    if not isinstance(pubmed_result, dict):
                        pubmed_result = {
                            "papers": [],
                            "count": 0,
                            "query": "",
                            "error": (
                                "PubMed returned an unexpected result format."
                            ),
                        }

                    st.session_state["research_pubmed_result"] = pubmed_result
                except Exception as exc:
                    st.session_state["research_pubmed_result"] = {
                        "papers": [],
                        "count": 0,
                        "error": str(exc),
                        "query": "",
                    }
        else:
            st.session_state["research_pubmed_result"] = None


# ============================================================
# FIRST-LOAD DEFAULT SEARCH
# ============================================================

# Load only the local dataset on first visit. External PubMed retrieval
# waits until the user submits a claim with its checkbox enabled.
if "research_local_result" not in st.session_state:
    default_claim = clean_text(
        st.session_state.get(
            "research_claim",
            "Vitamin C supplementation prevents the common cold.",
        )
    )

    st.session_state.setdefault("research_pubmed_result", None)
    st.session_state.setdefault("research_pubmed_searched", False)

    try:
        with st.spinner("Loading the local SciFact corpus..."):
            engine = load_evidence_engine()
            result = engine.analyze(
                default_claim,
                top_k=int(
                    st.session_state.get("research_local_count", 10)
                ),
            )
            st.session_state["research_local_result"] = result
            st.session_state["research_search_error"] = None
    except Exception as exc:
        st.session_state["research_local_result"] = None
        st.session_state["research_search_error"] = str(exc)

# ============================================================
# DISPLAY RESULTS
# ============================================================

local_result = st.session_state.get("research_local_result")
search_error = st.session_state.get("research_search_error")

active_claim = clean_text(
    st.session_state.get(
        "research_claim",
        "Vitamin C supplementation prevents the common cold.",
    )
)

if search_error:
    st.error(
        "ResearchTrace could not analyse this claim. "
        "Check the error details below."
    )
    st.code(search_error)

elif local_result:
    local_papers = local_result.get("papers", []) or []
    local_evidence = local_result.get("evidence", []) or []

    local_papers = sorted(
        local_papers,
        key=safe_similarity,
        reverse=True,
    )

    local_papers = local_papers[
        :int(st.session_state.get("research_local_count", 10))
    ]

    pubmed_result = (
        st.session_state.get("research_pubmed_result") or {}
    )
    pubmed_was_searched = bool(
        st.session_state.get("research_pubmed_searched", False)
    )

    pubmed_papers = pubmed_result.get("papers", []) or []
    pubmed_papers = rank_pubmed_papers(pubmed_papers, active_claim)

    pubmed_papers = pubmed_papers[
        :int(st.session_state.get("research_pubmed_count", 5))
    ]

    verdict = clean_text(
        local_result.get("verdict", "Insufficient evidence")
    )

    verdict_message = clean_text(
        local_result.get(
            "message",
            "No additional explanation is available.",
        )
    )

    exact_match = bool(local_result.get("exact_match", False))

    annotated_ids = local_result.get("annotated_paper_ids", []) or []
    annotated_count = len(annotated_ids)

    similarities = [
        safe_similarity(paper) for paper in local_papers
    ]
    top_similarity = max(similarities) if similarities else 0.0

    local_tab, pubmed_tab = st.tabs(
        ["◈  01 · LOCAL RESEARCH", "◎  02 · PUBMED RESEARCH"]
    )

    # ========================================================
    # TAB 1: LOCAL RESEARCH
    # ========================================================

    with local_tab:
        render_section_header(
            "SOURCE 01 · LOCAL DATASET",
            "SciFact evidence explorer",
            "The local verdict is based on exact annotated claim matches "
            "and evidence labels in SciFact. Similarity is used to "
            "retrieve related papers, not establish scientific truth.",
        )

        verdict_lower = verdict.casefold()

        if "support" in verdict_lower:
            verdict_color = "#86efac"
        elif "refute" in verdict_lower or "contradict" in verdict_lower:
            verdict_color = "#fca5a5"
        else:
            verdict_color = "#c4b5fd"

        st.markdown(
            f"""
            <div class="verdict-card">
                <div class="verdict-label">CLAIM ANALYSIS</div>
                <div class="verdict-value" style="color:{verdict_color}">
                    {escape_html(verdict)}
                </div>
                <div class="verdict-message">
                    {escape_html(verdict_message)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not exact_match:
            match_scopes = {
                clean_text(paper.get("match_scope", ""))
                for paper in local_papers
                if isinstance(paper, dict)
            }

            if local_papers and match_scopes == {"primary_topic_only"}:
                st.info(
                    "Local corpus coverage note: SciFact contains papers about "
                    "the main topic, but none of these local papers also matched "
                    "another key concept in the claim. The displayed papers are "
                    "main-topic background only and may not directly test the "
                    "claim. This does not mean the claim is false. Use the "
                    "PubMed Research tab for broader biomedical literature."
                )
            elif local_papers and match_scopes == {"text_similarity_fallback"}:
                st.info(
                    "Local corpus coverage note: no local paper matched the "
                    "main detected scientific topic. The displayed papers are "
                    "text-similarity fallback candidates and may be unrelated; "
                    "inspect their titles and abstracts carefully. This does not "
                    "mean the claim is false. Use the PubMed Research tab for "
                    "broader biomedical literature."
                )
            elif local_papers:
                st.info(
                    "Local corpus coverage note: no annotated evidence was "
                    "found for this exact claim. These are related candidate "
                    "papers, not proof that the claim is true or false. Use the "
                    "PubMed Research tab for broader biomedical literature."
                )
            else:
                st.info(
                    "Local corpus coverage note: no related local papers were "
                    "returned for this claim. This is a limitation of the local "
                    "collection, not evidence that the claim is false. Use the "
                    "PubMed Research tab for broader biomedical literature."
                )

        metric_columns = st.columns(4)

        with metric_columns[0]:
            render_metric(
                "RELATED PAPERS",
                str(len(local_papers)),
                "Retrieved from local corpus",
            )

        with metric_columns[1]:
            render_metric(
                "ANNOTATED SENTENCES",
                str(len(local_evidence)),
                "Evidence records returned",
            )

        with metric_columns[2]:
            render_metric(
                "ANNOTATED SOURCES",
                str(annotated_count),
                "Annotated source paper IDs",
            )

        with metric_columns[3]:
            render_metric(
                "TOP RANKING SCORE",
                f"{top_similarity:.3f}",
                "Not a truth probability",
            )

        st.markdown("---")

        graph_column, details_column = st.columns(
            [1.35, 0.85],
            gap="large",
        )

        with graph_column:
            render_section_header(
                "KNOWLEDGE GRAPH",
                "Claim-to-evidence network",
                "The central node represents the claim. Connected nodes "
                "represent related papers and annotated evidence "
                "sentences when available.",
            )

            render_graph(
                active_claim,
                local_papers,
                graph_type="local",
                evidence=local_evidence,
                key="local_research_graph",
            )

        with details_column:
            render_section_header(
                "PAPER DETAILS",
                "Explore retrieved papers",
                "Select a local result to inspect its metadata and abstract.",
            )

            if local_papers:
                # Use stable paper IDs as widget values. Index-based options
                # can display a stale title after result ordering changes.
                local_paper_lookup = {}
                local_paper_options = []
                for paper_position, paper in enumerate(local_papers):
                    paper_key = get_paper_id(
                        paper, fallback=f"paper-{paper_position}"
                    )
                    # Corpus document IDs are unique; guard against malformed
                    # duplicates without making the UI crash.
                    if paper_key in local_paper_lookup:
                        paper_key = f"{paper_key}__{paper_position}"
                    local_paper_lookup[paper_key] = paper
                    local_paper_options.append(paper_key)

                if st.session_state.get("local_paper_selector") not in local_paper_options:
                    st.session_state.pop("local_paper_selector", None)

                selected_paper_key = st.selectbox(
                    "Select paper",
                    options=local_paper_options,
                    format_func=lambda paper_key: (
                        f"{local_paper_options.index(paper_key) + 1}. "
                        f"{truncate_text(get_paper_title(local_paper_lookup[paper_key]), 65)}"
                    ),
                    key="local_paper_selector",
                )

                selected_paper = local_paper_lookup[selected_paper_key]
                selected_index = local_paper_options.index(selected_paper_key)

                st.markdown(
                    f"""
                    <div class="paper-card">
                        <div class="section-kicker">
                            PAPER {selected_index + 1:02d}
                        </div>
                        <div class="paper-title">
                            {escape_html(get_paper_title(selected_paper))}
                        </div>
                        <div class="paper-meta">
                            ID: {escape_html(get_paper_id(selected_paper))}
                        </div>
                        <div style="margin-top:12px">
                            <span class="tag">
                                Ranking score:
                                {safe_similarity(selected_paper):.3f}
                            </span>
                        </div>
                        <div class="paper-abstract">
                            {escape_html(truncate_text(
                                get_paper_abstract(selected_paper), 650
                            ))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.expander("Read full abstract"):
                    st.write(get_paper_abstract(selected_paper))

            else:
                st.info("No local papers were returned.")

        st.markdown("---")

        render_section_header(
            "ANNOTATED EVIDENCE",
            "Evidence explorer",
            "Inspect evidence labels returned by the local SciFact "
            "annotation engine.",
        )

        render_evidence_explorer(local_evidence)

        st.markdown("---")

        render_section_header(
            "LOCAL LITERATURE",
            "Related research papers",
            "Retrieved papers are ranked by textual relevance. "
            "A high ranking does not mean a paper supports or refutes "
            "the claim.",
        )

        if local_papers:
            for start in range(0, len(local_papers), 2):
                row = st.columns(2, gap="medium")

                for offset, column in enumerate(row):
                    index = start + offset

                    if index < len(local_papers):
                        with column:
                            render_paper_card(
                                local_papers[index],
                                index,
                                source="local",
                            )
        else:
            st.info("No related local papers were found.")

        if not exact_match:
            st.markdown(
                """
                <div class="source-note">
                    <strong>Why the verdict may be insufficient:</strong>
                    the claim did not exactly match an annotated SciFact
                    claim. Related papers may provide context, but text
                    similarity alone cannot establish whether the claim
                    is scientifically true or false.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # TAB 2: PUBMED RESEARCH
    # ========================================================

    with pubmed_tab:
        render_section_header(
            "SOURCE 02 · EXTERNAL LITERATURE",
            "PubMed research explorer",
            "Explore biomedical publications independently of the local "
            "SciFact verdict. Review titles, abstracts, metadata, and "
            "topic connections before interpreting the evidence.",
        )

        pubmed_error = pubmed_result.get("error")
        pubmed_total = safe_int(pubmed_result.get("count", 0))
        pubmed_query = clean_text(pubmed_result.get("query", ""))

        pubmed_metric_columns = st.columns(4)

        with pubmed_metric_columns[0]:
            render_metric(
                "PAPERS DISPLAYED",
                str(len(pubmed_papers)),
                "PubMed results after display ranking",
            )

        with pubmed_metric_columns[1]:
            render_metric(
                "PUBMED MATCHES",
                f"{pubmed_total:,}",
                "Total returned by the search",
            )

        with pubmed_metric_columns[2]:
            with_abstracts = sum(
                bool(get_paper_abstract(paper))
                and "no abstract is available"
                not in get_paper_abstract(paper).casefold()
                for paper in pubmed_papers
            )

            render_metric(
                "ABSTRACTS AVAILABLE",
                str(with_abstracts),
                "Among displayed papers",
            )

        with pubmed_metric_columns[3]:
            render_metric(
                "EXTERNAL SOURCE",
                "PubMed",
                "NCBI literature database",
            )

        if not PUBMED_AVAILABLE:
            st.warning(
                "The PubMed module could not be imported. "
                "Check that pubmed_engine.py exists and that it has "
                "no import errors."
            )

        elif pubmed_error:
            st.error(f"PubMed search returned an error: {pubmed_error}")
            st.caption(
                "The local SciFact results are independent of this "
                "external search error."
            )

        elif not pubmed_was_searched:
            st.info(
                "PubMed has not been searched for this claim yet. "
                "Return to the claim form, keep 'Search external PubMed' "
                "selected, and click 'Analyse claim' to retrieve external papers."
            )

        elif not pubmed_papers:
            st.info(
                "No PubMed papers were retrieved for this claim. "
                "The search may have returned zero matches, or the "
                "requested query may need broader terminology."
            )

        else:
            st.markdown("---")

            pubmed_graph_column, pubmed_info_column = st.columns(
                [1.35, 0.85],
                gap="large",
            )

            with pubmed_graph_column:
                render_section_header(
                    "PUBMED KNOWLEDGE GRAPH",
                    "Claim-to-literature network",
                    "Explore retrieved papers and broad topic categories "
                    "in a graph independent of the local SciFact graph.",
                )

                render_graph(
                    active_claim,
                    pubmed_papers,
                    graph_type="pubmed",
                    evidence=None,
                    key="pubmed_research_graph",
                )

            with pubmed_info_column:
                render_section_header(
                    "RESEARCH SNAPSHOT",
                    "Publication details",
                    "Inspect a paper's abstract, bibliographic metadata, "
                    "and original source record.",
                )

                pubmed_paper_lookup = {}
                pubmed_paper_options = []
                for paper_position, paper in enumerate(pubmed_papers):
                    paper_key = get_paper_id(
                        paper, fallback=f"pubmed-paper-{paper_position}"
                    )
                    if paper_key in pubmed_paper_lookup:
                        paper_key = f"{paper_key}__{paper_position}"
                    pubmed_paper_lookup[paper_key] = paper
                    pubmed_paper_options.append(paper_key)

                if st.session_state.get("pubmed_paper_selector") not in pubmed_paper_options:
                    st.session_state.pop("pubmed_paper_selector", None)

                selected_pubmed_key = st.selectbox(
                    "Select PubMed paper",
                    options=pubmed_paper_options,
                    format_func=lambda paper_key: (
                        f"{pubmed_paper_options.index(paper_key) + 1}. "
                        f"{truncate_text(get_paper_title(pubmed_paper_lookup[paper_key]), 65)}"
                    ),
                    key="pubmed_paper_selector",
                )
                selected_pubmed = pubmed_paper_lookup[selected_pubmed_key]
                selected_pubmed_index = pubmed_paper_options.index(selected_pubmed_key)

                st.markdown(
                    f"""
                    <div class="paper-card">
                        <div class="section-kicker">
                            PUBMED RECORD {selected_pubmed_index + 1:02d}
                        </div>
                        <div class="paper-title">
                            {escape_html(get_paper_title(selected_pubmed))}
                        </div>
                        <div class="paper-meta">
                            {escape_html(get_pubmed_metadata(selected_pubmed))}
                        </div>
                        <div class="paper-abstract">
                            {escape_html(truncate_text(
                                get_paper_abstract(selected_pubmed), 750
                            ))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                selected_signals = get_pubmed_match_signals(
                    selected_pubmed
                )

                if selected_signals:
                    st.caption(
                        "Match signals: " + " · ".join(selected_signals)
                    )

                selected_url = get_paper_url(selected_pubmed)

                if selected_url:
                    st.link_button(
                        "Open original PubMed record ↗",
                        selected_url,
                        use_container_width=True,
                    )

            st.markdown("---")

            render_section_header(
                "LITERATURE REVIEW",
                "Retrieved PubMed papers",
                "Papers are ordered using title matches, scientific topic "
                "overlap, and whether the study discusses the outcome in "
                "your claim. Match signals explain the ranking; they do "
                "not establish whether the claim is true or whether a "
                "study is high quality.",
            )

            for index, paper in enumerate(pubmed_papers):
                render_paper_card(
                    paper,
                    index,
                    source="pubmed",
                    show_similarity=False,
                )

        if pubmed_query:
            with st.expander("View PubMed search query"):
                st.code(pubmed_query, language="text")

        st.markdown(
            """
            <div class="source-note">
                <strong>Interpretation note:</strong>
                a PubMed search result is not automatically supporting
                evidence. Study design, population, dosage, outcome,
                limitations, and the distinction between preventing
                an illness and reducing its duration or severity all
                matter when evaluating a scientific claim.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # FOOTER
    # ========================================================

    st.markdown(
        """
        <div class="footer">
            <div>
                RESEARCHTRACE · AI-POWERED SCIENTIFIC DISCOVERY
            </div>
            Built with Python, Streamlit, SciFact, PubMed,
            NetworkX and Plotly.
            <br>
            Project by Lucky Jain &amp; Shruti Rajak
            · NMIMS, Navi Mumbai
        </div>
        """,
        unsafe_allow_html=True,
    )
