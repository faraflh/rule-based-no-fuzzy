"""Quick test to verify KP vs KP MBKM routing"""
import json
import re
from pathlib import Path
from thefuzz import fuzz, process

# Minimal test without streamlit
import sys
import importlib.util

# We can't import app.py directly because of streamlit decorators,
# so let's simulate the core logic

BASE_PATH = Path(__file__).parent

# Load data
with open(BASE_PATH / "informasi_umum_chatbot.json", "r", encoding="utf-8") as f:
    informasi_umum_raw = json.load(f)
informasi_umum_data = informasi_umum_raw.get("intents", [])

with open(BASE_PATH / "sop_jte_fixed.json", "r", encoding="utf-8") as f:
    sop_jte_data = json.load(f)

def fuzzy_search_intent(user_query, data_list, threshold=80, exclude_prefixes=None):
    best_item = None
    highest_score = 0
    for item in data_list:
        if exclude_prefixes:
            intent_name = item.get("intent", "")
            if any(intent_name.startswith(prefix) for prefix in exclude_prefixes):
                continue
        keywords = item.get("keywords", []) or item.get("keyword", [])
        if not keywords:
            continue
        match = process.extractOne(user_query, keywords, scorer=fuzz.token_set_ratio)
        if match and match[1] > highest_score:
            highest_score = match[1]
            best_item = item
    return best_item if highest_score >= threshold else None

def fuzzy_search_sop(user_query, data_list, threshold=70, limit=2):
    scored = []
    for item in data_list:
        targets = [
            str(item.get("topik_utama", "")),
            str(item.get("sub_topik", "")),
            str(item.get("full_context", "")),
        ]
        konten = str(item.get("konten", ""))
        if konten:
            targets.append(konten[:400])
        targets = [t for t in targets if t]
        if not targets:
            continue
        match = process.extractOne(user_query, targets, scorer=fuzz.token_set_ratio)
        if match and match[1] >= threshold:
            scored.append((match[1], item))
    if not scored:
        return []
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]

# Test queries
test_queries = ["syarat kp", "prosedur kp", "alur kp", "kp mbkm", "prosedur kp mbkm", "syarat kp mbkm"]

for query in test_queries:
    expanded = query.lower().strip()
    is_mbkm = any(kw in expanded for kw in ["mbkm", "merdeka belajar"])
    
    print(f"\n{'='*60}")
    print(f"Query: '{query}' | is_mbkm: {is_mbkm}")
    print(f"{'='*60}")
    
    # Check if MBKM intent would match
    if is_mbkm:
        for item in informasi_umum_data:
            if item.get("intent") == "info_prosedur_kp_mbkm":
                print(f"  -> MBKM intent matched (explicit)")
                break
    
    # Check general informasi_umum (with MBKM excluded)
    best_info = fuzzy_search_intent(
        expanded,
        informasi_umum_data,
        threshold=80,
        exclude_prefixes=["info_surat_kpti_", "info_surat_sti_", "info_overview_kpti", "info_overview_sti", "info_prosedur_kp_mbkm"]
    )
    if best_info:
        print(f"  -> Informasi Umum: intent='{best_info.get('intent', 'N/A')}'")
    else:
        print(f"  -> Informasi Umum: No match")
    
    # Check SOP JTE
    sop_hits = fuzzy_search_sop(expanded, sop_jte_data, threshold=70, limit=2)
    if sop_hits:
        for hit in sop_hits:
            print(f"  -> SOP JTE: '{hit.get('sub_topik', 'N/A')}'")
    else:
        print(f"  -> SOP JTE: No match")
