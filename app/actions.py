# backend/app/actions.py
import re
import json
from typing import List, Dict, Optional
from dateutil import parser as date_parser
from rapidfuzz import process as rf_process, fuzz as rf_fuzz
import os

# Transformers imports
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import torch

# Model names (can be overridden via env)
NER_MODEL = os.getenv("NER_MODEL", "dslim/bert-base-NER")
HF_CACHE = os.getenv("HF_CACHE_DIR", r"D:\projects\ai-meeting-notes\models\hf_cache")

# Lazy-loaded HF pipeline
_NER_PIPE = None

def _device_idx():
    try:
        return 0 if torch.cuda.is_available() else -1
    except Exception:
        return -1

def get_ner_pipeline():
    global _NER_PIPE
    if _NER_PIPE is None:
        device = _device_idx()
        try:
            # load with explicit cache_dir to avoid network at runtime
            tokenizer = AutoTokenizer.from_pretrained(NER_MODEL, cache_dir=HF_CACHE)
            model = AutoModelForTokenClassification.from_pretrained(NER_MODEL, cache_dir=HF_CACHE)
            _NER_PIPE = pipeline("ner", model=model, tokenizer=tokenizer,
                                 aggregation_strategy="simple", device=device)
        except Exception as e:
            # if HF pipeline fails, set to None and fall back to regex
            print("NER pipeline load failed:", e)
            _NER_PIPE = None
    return _NER_PIPE

# Simple name regex fallback
NAME_PATTERN = r"\b([A-Z][a-z]{1,}\s?[A-Z]?[a-z]{0,})\b"

# Task detection keywords (expand as needed)
TASK_KEYWORDS = ("action", "todo", "task", "please", "we need to", "lets", "let's", "assign", "prepare", "finalize", "must", "will", "should", "follow up", "follow-up", "by", "deadline", "complete")

# Deadline regex patterns
DEADLINE_PATTERNS = [
    r"\bby\s+(?P<deadline>tomorrow|today|this week|next week|this weekend|end of week|end of month|EOD|end of day)\b",
    r"\b(?P<deadline>\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)\b",
    r"\b(?P<deadline>\d{1,2}(?:am|pm|AM|PM))\b",
    r"\b(?P<deadline>next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
]

def _parse_deadline(text: str) -> Optional[str]:
    for pat in DEADLINE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m and m.groupdict().get("deadline"):
            d = m.group("deadline")
            try:
                parsed = date_parser.parse(d, fuzzy=True, default=None)
                return parsed.isoformat()
            except Exception:
                return d
    # fallback: try fuzzy parse
    try:
        parsed = date_parser.parse(text, fuzzy=True)
        return parsed.isoformat()
    except Exception:
        return None

def _find_assignee_hf(sentence: str, participants: Optional[List[str]] = None) -> Optional[str]:
    pipe = get_ner_pipeline()
    if pipe:
        try:
            ents = pipe(sentence)
            # ents is a list of aggregated dicts: [{'entity_group':'PER','score':..,'word':'John Doe'}]
            persons = [e['word'].strip() for e in ents if e.get('entity_group') in ('PER','PERSON','ORG','MISC')]
            if persons:
                candidate = persons[0]
                if participants:
                    best = rf_process.extractOne(candidate, participants, scorer=rf_fuzz.WRatio)
                    if best and best[1] > 65:
                        return best[0]
                return candidate
        except Exception as e:
            print("NER pipeline error:", e)
            return None
    return None

def _find_assignee_regex(sentence: str) -> Optional[str]:
    names = re.findall(NAME_PATTERN, sentence)
    candidates = [n for n in names if len(n) > 2 and n.lower() not in ("team","today","tomorrow","thanks","everyone","we","this")]
    return candidates[0].strip() if candidates else None

def extract_action_items(text: str, participants: Optional[List[str]] = None) -> List[Dict]:
    """
    Returns list of action items:
    [{ "task": str, "assignee": Optional[str], "deadline": Optional[str], "context": str }]
    """
    items = []
    if not text:
        return items

    # split sentences (simple)
    sentences = re.split(r'(?<=[\.\?\!])\s+', text)
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        s_lower = s_strip.lower()

        # detect candidate task sentence
        if any(k in s_lower for k in TASK_KEYWORDS) or re.search(r'\bby\b', s_lower):
            task = re.sub(r'^(action:|todo:)\s*', '', s_strip, flags=re.IGNORECASE)
            deadline = _parse_deadline(s_strip)

            # assignee: HF NER -> fuzzy match -> regex fallback
            assignee = None
            try:
                assignee = _find_assignee_hf(s_strip, participants)
            except Exception:
                assignee = None
            if not assignee:
                assignee = _find_assignee_regex(s_strip)

            items.append({
                "task": task,
                "assignee": assignee,
                "deadline": deadline,
                "context": s_strip
            })

    # dedupe and return
    seen = set()
    out = []
    for it in items:
        key = it["task"][:120].lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out
