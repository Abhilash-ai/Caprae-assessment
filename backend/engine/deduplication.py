import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

LEGAL_SUFFIXES_REGEX = re.compile(
    r"\b(inc|incorporated|llc|corp|corporation|ltd|limited|co|company|group|technologies|tech|solutions|systems|holdings?|services|global)\b",
    re.IGNORECASE
)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Lowercase and replace non-alphanumeric with space
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    norm = normalize_text(name)
    # Remove common legal and generic suffixes
    norm = LEGAL_SUFFIXES_REGEX.sub("", norm)
    return re.sub(r"\s+", " ", norm).strip()

def string_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

def are_leads_duplicate(lead1: Dict[str, Any], lead2: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Evaluates whether two leads represent the same individual/company contact.
    Returns (is_dup, reason).
    """
    # 1. Exact email match (non-empty)
    email1 = (lead1.get("email") or "").strip().lower()
    email2 = (lead2.get("email") or "").strip().lower()
    if email1 and email2 and email1 == email2:
        return True, f"Identical email address ({email1})"

    # Cleaned domains
    dom1 = (lead1.get("cleaned_domain") or lead1.get("domain") or "").strip().lower()
    dom2 = (lead2.get("cleaned_domain") or lead2.get("domain") or "").strip().lower()

    # Full names
    fn1 = normalize_text(f"{lead1.get('first_name', '')} {lead1.get('last_name', '')}")
    fn2 = normalize_text(f"{lead2.get('first_name', '')} {lead2.get('last_name', '')}")

    name_sim = string_similarity(fn1, fn2)

    # 2. Same domain + High Name Similarity
    if dom1 and dom2 and dom1 == dom2:
        if name_sim >= 0.82:
            return True, f"Matching domain ({dom1}) with {int(name_sim*100)}% name match ('{fn1}' vs '{fn2}')"

    # 3. Same normalized company + High Name Similarity
    comp1 = normalize_company_name(lead1.get("company", ""))
    comp2 = normalize_company_name(lead2.get("company", ""))
    comp_sim = string_similarity(comp1, comp2)

    if comp_sim >= 0.85 and name_sim >= 0.85:
        return True, f"Fuzzy match on company ({int(comp_sim*100)}%) and name ({int(name_sim*100)}%)"

    return False, ""

def run_deduplication(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Runs multi-pass deduplication across the lead dataset.
    Assigns cluster IDs and flags duplicates while preserving the best-quality record.
    """
    n = len(leads)
    for i in range(n):
        leads[i]["temp_id"] = i + 1
        leads[i]["is_duplicate"] = False
        leads[i]["primary_lead_id"] = None
        leads[i]["duplicate_reason"] = ""
        leads[i]["dedup_cluster_id"] = f"cluster_{i + 1}"

    # Disjoint-set / Connected components clustering
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    match_reasons = {}

    for i in range(n):
        for j in range(i + 1, n):
            is_dup, reason = are_leads_duplicate(leads[i], leads[j])
            if is_dup:
                union(i, j)
                match_reasons[(min(i, j), max(i, j))] = reason

    # Group into clusters
    clusters: Dict[int, List[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)

    # In each cluster with >1 lead, pick the primary lead
    for root, member_indices in clusters.items():
        cluster_id = f"CLUSTER-{root + 1}"
        for idx in member_indices:
            leads[idx]["dedup_cluster_id"] = cluster_id

        if len(member_indices) > 1:
            # Score leads by quality score, then presence of email, phone, linkedin
            def completeness_score(idx):
                ld = leads[idx]
                score = ld.get("data_quality_score", 0)
                if ld.get("email") and ld.get("is_valid_email"):
                    score += 20
                if ld.get("phone"):
                    score += 10
                if ld.get("linkedin_url"):
                    score += 10
                return score

            sorted_members = sorted(member_indices, key=completeness_score, reverse=True)
            primary_idx = sorted_members[0]
            leads[primary_idx]["is_duplicate"] = False
            leads[primary_idx]["primary_lead_id"] = None

            for dup_idx in sorted_members[1:]:
                leads[dup_idx]["is_duplicate"] = True
                leads[dup_idx]["primary_lead_id"] = leads[primary_idx]["temp_id"]
                pair_key = (min(primary_idx, dup_idx), max(primary_idx, dup_idx))
                reason = match_reasons.get(pair_key, f"Duplicate of primary contact #{leads[primary_idx]['temp_id']}")
                leads[dup_idx]["duplicate_reason"] = reason

    return leads
