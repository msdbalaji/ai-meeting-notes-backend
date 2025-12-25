import re
from typing import List, Dict, Optional
import os

try:
    import spacy
    from spacy.lang.en import English
except Exception:
    spacy = None

DEFAULT_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")

_nlp = None

DEADLINE_PATTERNS = [
    r"\bby\s+(?P<deadline>tomorrow|today|this week|next week|this weekend|end of week|end of month|EOD|end of day)\b",
    r"\b(?P<deadline>\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)\b",
    r"\b(?P<deadline>next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    # plain weekday names (e.g. 'Friday')
    r"\b(?P<deadline>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
]

def init_spacy(model_name: Optional[str] = None):
    """Ensure spaCy and the model are available. Downloads model if missing."""
    global _nlp, spacy
    if spacy is None:
        try:
            import spacy as sp
            spacy = sp
        except Exception:
            print("[nlp.tasks] spaCy not installed; task extraction disabled")
            return

    model = model_name or DEFAULT_MODEL
    try:
        _nlp = spacy.load(model)
        print(f"[nlp.tasks] loaded spaCy model: {model}")
    except Exception as e:
        try:
            # attempt to download model
            import spacy.cli
            print(f"[nlp.tasks] spaCy model {model} missing, attempting to download...")
            spacy.cli.download(model)
            _nlp = spacy.load(model)
            print(f"[nlp.tasks] downloaded and loaded spaCy model: {model}")
        except Exception as e2:
            print("[nlp.tasks] failed to load or download spaCy model:", e2)
            _nlp = None


def _parse_deadline(text: str) -> Optional[str]:
    for pat in DEADLINE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m and m.groupdict().get("deadline"):
            return m.group("deadline")
    return None


def extract_action_items(text: str, participants: Optional[List[str]] = None) -> List[Dict]:
    """Extract action items using spaCy dependency parsing + NER.

    Returns list of {task, assignee, deadline, context}
    """
    items: List[Dict] = []
    if not text:
        return items

    # Ensure spaCy is initialized (lazy initialization when server didn't run startup)
    if _nlp is None:
        try:
            init_spacy()
        except Exception:
            pass

    # fallback to simple sentence splitting
    sentences = re.split(r'(?<=[\.\?\!])\s+', text)

    # if spaCy not available, fall back to simple heuristics
    if _nlp is None:
        for s in sentences:
            s_strip = s.strip()
            if not s_strip:
                continue
            if any(k in s_strip.lower() for k in ("action","todo","task","please","assign","follow up","due","by")):
                items.append({"task": s_strip, "assignee": None, "deadline": _parse_deadline(s_strip), "context": s_strip})
        return items

    for sent in _nlp.pipe(sentences):
        s_text = sent.text.strip()
        if not s_text:
            continue

        

        # Detect verbs that look like assignments (root verbs, imperative mood)
        verbs = [tok for tok in sent if tok.pos_ == "VERB" or tok.dep_ == "ROOT"]
        candidate = None
        for v in verbs:
            # common assignment verbs
            if v.lemma_.lower() in ("assign","do","create","prepare","finalize","send","follow","complete","setup","schedule","organize","book","present"):
                candidate = v
                break
        # also treat sentences with 'please' or 'we need' as tasks
        if candidate is None and ("please" in s_text.lower() or "we need" in s_text.lower() or "we should" in s_text.lower()):
            candidate = verbs[0] if verbs else None

        # if no candidate verb, skip unless sentence contains 'by' or task keywords
        if candidate is None and not any(k in s_text.lower() for k in ("by","deadline","due","todo","action","task","follow up")):
            continue

        # assemble task description (verb subtree or full sentence)
        task_desc = s_text
        try:
            if candidate is not None:
                subtree = " ".join([t.text for t in candidate.subtree])
                if len(subtree) > 10:
                    task_desc = subtree
        except Exception:
            pass

        # find persons via NER in the sentence
        assignee = None
        for ent in sent.ents:
            if ent.label_ in ("PERSON", "ORG"):
                assignee = ent.text
                break

        

        # fallback: look for patterns like 'Alice to prepare' where name precedes 'to <verb>'
        if assignee is None:
            m = re.search(r"\b([A-Z][a-z]+)\s+to\s+\w+", s_text)
            if m:
                assignee = m.group(1)
                

        deadline = _parse_deadline(s_text)

        items.append({"task": task_desc, "assignee": assignee, "deadline": deadline, "context": s_text})

    # dedupe
    seen = set()
    out = []
    for it in items:
        k = (it.get("task") or "").strip().lower()[:160]
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out
