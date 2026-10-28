
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from functools import lru_cache


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL_NAME = "ResearchTrace"
TOOL_EMAIL = "researchtrace@example.com"
USER_AGENT = "ResearchTrace/1.0 (scientific literature retrieval)"


# ============================================================
# SCIENTIFIC CONCEPTS AND SYNONYMS
# ============================================================

CONCEPT_GROUPS = [
    {
        "name": "creatine",
        "patterns": [
            r"\bcreatine\b",
            r"\bcreatine monohydrate\b",
            r"\bphosphocreatine\b",
        ],
        "terms": [
            '"creatine"[Title/Abstract]',
            '"creatine monohydrate"[Title/Abstract]',
            '"phosphocreatine"[Title/Abstract]',
            '"creatine supplementation"[Title/Abstract]',
        ],
    },
    {
        "name": "muscle",
        "patterns": [
            r"\bmuscle\b",
            r"\bmuscular\b",
            r"\bresistance training\b",
            r"\bstrength training\b",
            r"\bexercise performance\b",
        ],
        "terms": [
            '"muscle strength"[Title/Abstract]',
            '"muscle mass"[Title/Abstract]',
            '"resistance training"[Title/Abstract]',
            '"strength training"[Title/Abstract]',
            '"exercise performance"[Title/Abstract]',
            '"physical performance"[Title/Abstract]',
        ],
    },
    {
        "name": "cognition",
        "patterns": [
            r"\bcognit\w*\b",
            r"\bbrain\b",
            r"\bmemory\b",
            r"\bneuroprotect\w*\b",
        ],
        "terms": [
            '"cognitive function"[Title/Abstract]',
            '"cognitive performance"[Title/Abstract]',
            '"cognitive impairment"[Title/Abstract]',
            '"brain function"[Title/Abstract]',
            '"neuroprotection"[Title/Abstract]',
            '"memory"[Title/Abstract]',
        ],
    },
    {
        "name": "kidney",
        "patterns": [
            r"\bkidney\b",
            r"\bkidneys\b",
            r"\brenal\b",
            r"\bglomerular filtration\b",
            r"\beGFR\b",
        ],
        "terms": [
            '"kidney function"[Title/Abstract]',
            '"renal function"[Title/Abstract]',
            '"kidney injury"[Title/Abstract]',
            '"renal impairment"[Title/Abstract]',
            '"glomerular filtration rate"[Title/Abstract]',
            '"serum creatinine"[Title/Abstract]',
        ],
    },
    {
        "name": "gut_microbiome",
        "patterns": [
            r"\bgut microbiom\w*\b",
            r"\bgut microbiot\w*\b",
            r"\bgut microb\w*\b",
            r"\bintestinal microbiom\w*\b",
            r"\bintestinal microbiot\w*\b",
            r"\bgastrointestinal microbiot\w*\b",
            r"\btrillions of microbes\b",
            r"\bmicrobes in the (?:human )?gut\b",
            r"\bgut bacteria\b",
            r"\bintestinal bacteria\b",
            r"\bmicrobiota.gut.brain axis\b",
        ],
        "terms": [
            '"gut microbiome"[Title/Abstract]',
            '"gut microbiota"[Title/Abstract]',
            '"intestinal microbiota"[Title/Abstract]',
            '"intestinal microbiome"[Title/Abstract]',
            '"gastrointestinal microbiota"[Title/Abstract]',
            '"gut bacteria"[Title/Abstract]',
            '"gut microbiome"[MeSH Terms]',
        ],
    },
    {
        "name": "digestion",
        "patterns": [
            r"\bdigestion\b",
            r"\bdigestive\b",
            r"\bnutrient absorption\b",
            r"\bgastrointestinal function\b",
        ],
        "terms": [
            '"digestion"[Title/Abstract]',
            '"digestive system"[Title/Abstract]',
            '"nutrient absorption"[Title/Abstract]',
            '"gastrointestinal function"[Title/Abstract]',
        ],
    },
    {
        "name": "immunity",
        "patterns": [
            r"\bimmun\w*\b",
            r"\binflammation\b",
            r"\binflammatory\b",
        ],
        "terms": [
            '"immune system"[Title/Abstract]',
            '"immune response"[Title/Abstract]',
            '"immune function"[Title/Abstract]',
            '"inflammation"[Title/Abstract]',
            '"inflammatory response"[Title/Abstract]',
        ],
    },
    {
        "name": "mood",
        "patterns": [
            r"\bmood\b",
            r"\bmental health\b",
            r"\bdepress\w*\b",
            r"\banxiety\b",
            r"\bpsychological well.being\b",
        ],
        "terms": [
            '"mood"[Title/Abstract]',
            '"mental health"[Title/Abstract]',
            '"depression"[Title/Abstract]',
            '"anxiety"[Title/Abstract]',
            '"gut-brain axis"[Title/Abstract]',
        ],
    },
    {
        "name": "vitamin_c",
        "patterns": [
            r"\bvitamin\s*c\b",
            r"\bascorbic acid\b",
            r"\bascorbate\b",
        ],
        "terms": [
            '"vitamin C"[Title/Abstract]',
            '"ascorbic acid"[Title/Abstract]',
            '"ascorbate"[Title/Abstract]',
        ],
    },
    {
        "name": "common_cold",
        "patterns": [
            r"\bcommon cold\b",
            r"\bcold symptoms\b",
            r"\bupper respiratory\b",
            r"\brespiratory infection\b",
        ],
        "terms": [
            '"common cold"[Title/Abstract]',
            '"common cold"[MeSH Terms]',
            '"upper respiratory tract infection"[Title/Abstract]',
            '"respiratory infection"[Title/Abstract]',
        ],
    },
    {
        "name": "vitamin_d",
        "patterns": [
            r"\bvitamin\s*d\b",
            r"\bcholecalciferol\b",
            r"\b25.hydroxyvitamin d\b",
        ],
        "terms": [
            '"vitamin D"[Title/Abstract]',
            '"cholecalciferol"[Title/Abstract]',
            '"25-hydroxyvitamin D"[Title/Abstract]',
        ],
    },
    {
        "name": "folate",
        "patterns": [
            r"\bfolate\b",
            r"\bfolic acid\b",
            r"\bvitamin b9\b",
        ],
        "terms": [
            '"folate"[Title/Abstract]',
            '"folic acid"[Title/Abstract]',
            '"vitamin B9"[Title/Abstract]',
        ],
    },
    {
        "name": "homocysteine",
        "patterns": [
            r"\bhomocysteine\b",
        ],
        "terms": [
            '"homocysteine"[Title/Abstract]',
            '"plasma homocysteine"[Title/Abstract]',
            '"serum homocysteine"[Title/Abstract]',
        ],
    },
    {
        "name": "smoking",
        "patterns": [
            r"\bsmok\w*\b",
            r"\btobacco\b",
            r"\bcigarette\w*\b",
        ],
        "terms": [
            '"smoking"[Title/Abstract]',
            '"tobacco"[Title/Abstract]',
            '"cigarette smoking"[Title/Abstract]',
        ],
    },
    {
        "name": "lung_cancer",
        "patterns": [
            r"\blung cancer\b",
            r"\bpulmonary carcinoma\b",
            r"\blung neoplasm\w*\b",
        ],
        "terms": [
            '"lung cancer"[Title/Abstract]',
            '"lung neoplasms"[MeSH Terms]',
            '"pulmonary carcinoma"[Title/Abstract]',
        ],
    },
    {
        "name": "prion",
        "patterns": [
            r"\bprion\w*\b",
            r"\babnormal prp\b",
            r"\bprp positivity\b",
        ],
        "terms": [
            '"prion protein"[Title/Abstract]',
            '"abnormal prion protein"[Title/Abstract]',
            '"PrPSc"[Title/Abstract]',
        ],
    },
]


# ============================================================
# CONCEPT DETECTION AND QUERY BUILDING
# ============================================================

PRIMARY_CONCEPT_PRIORITY = [
    "creatine",
    "gut_microbiome",
    "vitamin_c",
    "vitamin_d",
    "folate",
    "homocysteine",
    "smoking",
    "lung_cancer",
    "prion",
    "common_cold",
    "kidney",
    "muscle",
    "cognition",
    "digestion",
    "immunity",
    "mood",
]


def _matching_groups(claim):
    """Detect scientific concepts explicitly mentioned in a claim."""
    if not isinstance(claim, str):
        return []

    text = claim.casefold()
    matches = []

    for group in CONCEPT_GROUPS:
        if any(
            re.search(pattern, text)
            for pattern in group["patterns"]
        ):
            matches.append(group)

    return matches


def _select_primary_group(groups):
    """
    Select the main subject for retrieval.

    This ensures that a claim about creatine and cognition is led
    by creatine rather than by the more general cognition concept.
    """
    if not groups:
        return None

    by_name = {
        group["name"]: group
        for group in groups
    }

    for name in PRIMARY_CONCEPT_PRIORITY:
        if name in by_name:
            return by_name[name]

    return groups[0]


def _group_query(group):
    """Build an OR query from one concept's PubMed synonyms."""
    terms = list(dict.fromkeys(group["terms"]))

    if not terms:
        return ""

    return "(" + " OR ".join(terms) + ")"


def build_pubmed_query(claim):
    """
    Build a focused PubMed query.

    Main topic AND (related topic A OR related topic B OR ...)

    Requiring the primary topic helps avoid results about cognition
    alone for a creatine claim. Using OR between secondary facets
    allows a gut microbiome claim to retrieve studies about digestion,
    immunity, or mood without requiring every facet in each paper.
    """
    if not isinstance(claim, str) or not claim.strip():
        return ""

    claim = re.sub(r"\s+", " ", claim).strip()
    groups = _matching_groups(claim)

    if not groups:
        return claim

    primary = _select_primary_group(groups)
    primary_query = _group_query(primary)

    if not primary_query:
        return claim

    secondary_groups = [
        group for group in groups
        if group["name"] != primary["name"]
    ]

    # If the claim contains only one detected concept, search that
    # concept and its synonyms without adding unrelated constraints.
    if not secondary_groups:
        return primary_query

    # Keep a manageable number of secondary concepts for long claims.
    # The priority list makes selection deterministic.
    secondary_groups.sort(
        key=lambda group: (
            PRIMARY_CONCEPT_PRIORITY.index(group["name"])
            if group["name"] in PRIMARY_CONCEPT_PRIORITY
            else len(PRIMARY_CONCEPT_PRIORITY)
        )
    )

    secondary_groups = secondary_groups[:4]

    secondary_queries = [
        _group_query(group)
        for group in secondary_groups
    ]

    secondary_queries = [
        query for query in secondary_queries if query
    ]

    if not secondary_queries:
        return primary_query

    facets_query = "(" + " OR ".join(secondary_queries) + ")"

    return primary_query + " AND " + facets_query


# ============================================================
# HTTP REQUESTS
# ============================================================

def _request_url(endpoint, params):
    """Send a request to NCBI E-utilities."""
    params = dict(params)
    params.setdefault("tool", TOOL_NAME)
    params.setdefault("email", TOOL_EMAIL)

    url = (
        BASE_URL
        + endpoint
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def _request_json(endpoint, params):
    raw = _request_url(endpoint, params)
    return json.loads(raw.decode("utf-8"))


def _request_xml(endpoint, params):
    raw = _request_url(endpoint, params)
    return ET.fromstring(raw)


# ============================================================
# PUBMED XML PARSING
# ============================================================

def _get_text(element, path):
    """Read text from an XML element, including nested markup."""
    found = element.find(path)

    if found is None:
        return ""

    return " ".join(
        text.strip()
        for text in found.itertext()
        if text and text.strip()
    )


def _parse_publication_date(article):
    date_element = article.find(".//PubDate")

    if date_element is None:
        return "Date unavailable"

    year = _get_text(date_element, "Year")
    month = _get_text(date_element, "Month")
    day = _get_text(date_element, "Day")
    medline_date = _get_text(date_element, "MedlineDate")

    if year and month and day:
        return f"{year} {month} {day}"

    if year and month:
        return f"{month} {year}"

    if year:
        return year

    if medline_date:
        return medline_date

    return "Date unavailable"


def _parse_article(article):
    """Convert a PubMed XML article into the app's paper format."""
    pmid = _get_text(article, ".//PMID")
    title = _get_text(article, ".//ArticleTitle")
    journal = _get_text(article, ".//Journal/Title")

    abstract_parts = []

    for element in article.findall(".//Abstract/AbstractText"):
        section = " ".join(
            text.strip()
            for text in element.itertext()
            if text and text.strip()
        )

        label = element.attrib.get("Label", "").strip()

        if section:
            abstract_parts.append(
                f"{label}: {section}" if label else section
            )

    authors = []

    for author in article.findall(".//AuthorList/Author"):
        collective = _get_text(author, "CollectiveName")
        first = _get_text(author, "ForeName")
        last = _get_text(author, "LastName")

        name = collective or " ".join(
            part for part in (first, last) if part
        )

        if name:
            authors.append(name)

    return {
        "pmid": pmid,
        "title": title or "Title unavailable",
        "abstract": "\n\n".join(abstract_parts)
        or "No abstract available from PubMed.",
        "journal": journal or "Journal unavailable",
        "publication_date": _parse_publication_date(article),
        "authors": authors,
        "url": (
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if pmid else ""
        ),
        "source": "PubMed",
    }


# ============================================================
# RELEVANCE RANKING
# ============================================================

def _normalize_for_matching(text):
    """Normalize text for consistent scientific phrase matching."""
    text = str(text).casefold()
    text = re.sub(r"[-_/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _phrase_in_text(phrase, text):
    """Check for a phrase using word boundaries."""
    phrase = _normalize_for_matching(phrase)
    text = _normalize_for_matching(text)

    if not phrase or not text:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])"
    )

    return re.search(pattern, text) is not None


def _term_phrase(pubmed_term):
    """Extract the phrase from a PubMed query term."""
    return pubmed_term.split("[", 1)[0].strip().strip('"')


def _group_match_strength(group, title, abstract):
    """
    Return a relevance score for one concept group.

    Exact title mentions are weighted more heavily than abstract-only
    mentions. This is a ranking heuristic, not a scientific conclusion.
    """
    phrases = [
        _term_phrase(term)
        for term in group["terms"]
    ]

    title_match = any(
        _phrase_in_text(phrase, title)
        for phrase in phrases
    )

    abstract_match = any(
        _phrase_in_text(phrase, abstract)
        for phrase in phrases
    )

    if title_match:
        return 1.0

    if abstract_match:
        return 0.45

    # Also use the group patterns for natural-language variants.
    combined_text = title + " " + abstract

    if any(
        re.search(pattern, combined_text, flags=re.IGNORECASE)
        for pattern in group["patterns"]
    ):
        return 0.30

    return 0.0


def _rank_papers(papers, claim):
    """Rank fetched PubMed records for main-topic and outcome relevance.

    This orders search results only. It does not determine claim truth,
    assess study quality, or infer a paper's conclusion from its title.
    """
    if not papers:
        return []

    groups = _matching_groups(claim)
    if not groups:
        return papers

    primary = _select_primary_group(groups)
    secondary_groups = [g for g in groups if g["name"] != primary["name"]]
    claim_text = _normalize_for_matching(claim)

    outcome_patterns = {
        "prevention": r"\b(prevent\w*|prophylaxis|incidence|risk reduction)\b",
        "treatment": r"\b(treat\w*|therap\w*|management|alleviat\w*|cure\w*)\b",
        "duration": r"\b(duration|shorten\w*|recovery time|time to recovery)\b",
        "severity": r"\b(severity|severe|symptom burden|symptom severity)\b",
        "safety": r"\b(safe\w*|safety|adverse effect\w*|side effect\w*|toxicity|harm|kidney damage|renal damage)\b",
        "performance": r"\b(improv\w*|performance|efficacy|effectiveness|benefit\w*|strength)\b",
    }
    claim_outcomes = {
        name for name, pattern in outcome_patterns.items()
        if re.search(pattern, claim_text)
    }

    ranked = []
    for position, original in enumerate(papers):
        paper = dict(original)
        title = str(paper.get("title", ""))
        abstract = str(paper.get("abstract", ""))
        title_norm = _normalize_for_matching(title)
        abstract_norm = _normalize_for_matching(abstract)
        has_abstract = bool(abstract.strip()) and "no abstract available" not in abstract.casefold()

        primary_strength = _group_match_strength(primary, title_norm, abstract_norm)
        primary_in_title = _group_match_strength(primary, title_norm, "") > 0
        secondary_strengths = [
            _group_match_strength(group, title_norm, abstract_norm)
            for group in secondary_groups
        ]
        secondary_score = sum(secondary_strengths) / len(secondary_strengths) if secondary_strengths else 0.0
        secondary_in_title = any(
            _group_match_strength(group, title_norm, "") > 0
            for group in secondary_groups
        )

        combined = title_norm + " " + abstract_norm
        title_outcomes = {
            name for name, pattern in outcome_patterns.items()
            if re.search(pattern, title_norm)
        }
        paper_outcomes = {
            name for name, pattern in outcome_patterns.items()
            if re.search(pattern, combined)
        }
        outcome_title_matches = len(claim_outcomes & title_outcomes)
        outcome_any_matches = len(claim_outcomes & paper_outcomes)
        title_links_intervention_and_outcome = bool(
            primary_in_title and secondary_in_title and outcome_title_matches > 0
        )
        direct_question_title = bool(
            title_norm.endswith("?")
            and primary_in_title
            and secondary_in_title
            and outcome_title_matches > 0
        )

        is_review = bool(re.search(r"\b(systematic review|meta[- ]analysis|review)\b", title_norm))
        title_is_generic = len(re.findall(r"[a-z0-9]+", title_norm)) <= 3

        score = 12.0 * primary_strength + 2.0 * secondary_score
        score += 5.0 * outcome_title_matches + 2.0 * outcome_any_matches
        score += 3.0 * int(title_links_intervention_and_outcome)
        score += 3.0 * int(direct_question_title)

        # Abstract-only mentions are weaker than titles naming the intervention.
        if primary_strength == 0:
            score -= 7.0
        elif not primary_in_title:
            score -= 3.0
        if not has_abstract:
            score -= 2.0
        if title_is_generic and outcome_any_matches == 0:
            score -= 2.5
        if is_review and primary_strength > 0:
            score += 1.0

        # Do not let a background mention of prevention mask a title focused
        # on treatment, cold duration, or symptom severity.
        if "prevention" in claim_outcomes:
            prevention_in_title = "prevention" in title_outcomes
            other_outcomes_in_title = title_outcomes & {"treatment", "duration", "severity"}
            if not prevention_in_title and other_outcomes_in_title:
                score -= 6.0
            elif not prevention_in_title:
                score -= 2.5

        ranked_paper = dict(paper)
        ranked_paper["retrieval_score"] = round(score, 3)
        ranked.append((score, position, ranked_paper))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked]

# ============================================================
# PUBMED SEARCH
# ============================================================

@lru_cache(maxsize=64)
def _search_ids(query, max_results):
    """Search PubMed and return article IDs and total match count."""
    result = _request_json(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        },
    )

    data = result.get("esearchresult", {})

    return (
        data.get("idlist", []),
        int(data.get("count", 0)),
    )


def _empty_result(query, error=None, count=0):
    return {
        "query": query,
        "count": count,
        "papers": [],
        "error": error,
    }


def search_pubmed(claim, max_results=10):
    """
    Search PubMed for literature related to a scientific claim.

    Return format is compatible with ResearchTrace:
        {
            "query": str,
            "count": int,
            "papers": list,
            "error": str | None
        }

    This retrieves related literature; it does not verify a claim.
    """
    if not isinstance(claim, str) or not claim.strip():
        return _empty_result(
            "",
            "Please enter a scientific claim.",
        )

    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        max_results = 10

    max_results = max(1, min(max_results, 50))

    primary_query = build_pubmed_query(claim)

    # First try the structured concept query. If it produces no IDs,
    # retry with the original claim as a broader natural-language query.
    queries = [primary_query]

    original_query = re.sub(
        r"\s+",
        " ",
        claim,
    ).strip()

    if (
        primary_query.casefold()
        != original_query.casefold()
    ):
        queries.append(original_query)

    last_query = primary_query
    last_count = 0

    try:
        ids = []

        for query in queries:
            last_query = query
            ids, last_count = _search_ids(
                query,
                max_results,
            )

            if ids:
                break

        if not ids:
            return _empty_result(
                last_query,
                error=None,
                count=last_count,
            )

        # Keep requests separated briefly to be considerate of NCBI.
        time.sleep(0.4)

        root = _request_xml(
            "efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
            },
        )

        parsed = {}

        for article in root.findall(".//PubmedArticle"):
            paper = _parse_article(article)

            if paper["pmid"]:
                parsed[paper["pmid"]] = paper

        # Preserve ESearch order before applying our relevance ranking.
        papers = [
            parsed[pmid]
            for pmid in ids
            if pmid in parsed
        ]

        papers = _rank_papers(
            papers,
            claim,
        )

        return {
            "query": last_query,
            "count": last_count,
            "papers": papers,
            "error": None,
        }

    except urllib.error.HTTPError as exc:
        return _empty_result(
            last_query,
            error=(
                f"PubMed returned HTTP {exc.code}. "
                "Please try again later."
            ),
        )

    except urllib.error.URLError:
        return _empty_result(
            last_query,
            error=(
                "Could not connect to PubMed. Check your internet "
                "connection and try again."
            ),
        )

    except (TimeoutError, OSError):
        return _empty_result(
            last_query,
            error="The PubMed request timed out. Please try again.",
        )

    except (
        ValueError,
        ET.ParseError,
        KeyError,
        TypeError,
    ) as exc:
        return _empty_result(
            last_query,
            error=f"Could not process PubMed results: {exc}",
        )


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":
    while True:
        claim = input(
            "\nEnter a scientific claim (or type 'exit'): "
        ).strip()

        if claim.casefold() in {"exit", "quit"}:
            break

        if not claim:
            print("Please enter a scientific claim.")
            continue

        query = build_pubmed_query(claim)

        print("\nConstructed PubMed query:")
        print(query)

        result = search_pubmed(
            claim,
            max_results=10,
        )

        print("\nTotal matching PubMed records:", result["count"])

        if result["error"]:
            print("Error:", result["error"])

        if not result["papers"]:
            print("No papers were retrieved.")
            continue

        print("\nTop matching research papers:")

        for number, paper in enumerate(
            result["papers"],
            start=1,
        ):
            print(f"\n{number}. {paper['title']}")
            print("PMID:", paper["pmid"])
            print("Journal:", paper["journal"])
            print("Date:", paper["publication_date"])
            print("Retrieval score:", paper.get("retrieval_score", 0))
            print("URL:", paper["url"])
            print("Abstract:", paper["abstract"][:400])
