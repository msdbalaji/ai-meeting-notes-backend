# backend/app/summarizer.py
import os
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "t5-small")
HF_CACHE = os.getenv("HF_CACHE_DIR", "D:\\projects\\ai-meeting-notes\\models\\hf_cache")

_summarizer = None

def _device_index():
    try:
        return 0 if torch.cuda.is_available() else -1
    except Exception:
        return -1

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        tokenizer = AutoTokenizer.from_pretrained(SUMMARIZER_MODEL, cache_dir=HF_CACHE)
        model = AutoModelForSeq2SeqLM.from_pretrained(SUMMARIZER_MODEL, cache_dir=HF_CACHE)
        device = _device_index()
        _summarizer = pipeline("summarization", model=model, tokenizer=tokenizer, device=device)
    return _summarizer

def _chunk_text(text: str, chunk_chars: int = 1200):
    import re
    sents = re.split(r'(?<=[\.\?\!])\s+', text)
    chunks = []
    cur = ""
    for s in sents:
        if len(cur) + len(s) + 1 <= chunk_chars:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)
    return chunks

def _choose_max_length(chunk: str):
    approx_tokens = max(32, int(len(chunk) / 4))
    max_summary_tokens = min(150, max(20, int(approx_tokens * 0.45)))
    return max_summary_tokens

def summarize_meeting(text: str, max_length: int = None, min_length: int = 20) -> str:
    if not text or not text.strip():
        return ""
    summarizer = get_summarizer()
    chunks = _chunk_text(text, chunk_chars=1200)
    summaries = []
    for c in chunks:
        use_max = _choose_max_length(c) if max_length is None else max_length
        try:
            out = summarizer(c, max_new_tokens=use_max, min_length=min_length, truncation=True)
            summaries.append(out[0]["summary_text"].strip())
        except TypeError:
            out = summarizer(c, max_length=use_max, min_length=min_length, truncation=True)
            summaries.append(out[0]["summary_text"].strip())
        except Exception as e:
            print("summarizer chunk error:", e)
    if not summaries:
        return ""
    if len(summaries) == 1:
        return summaries[0]
    final_text = " ".join(summaries)
    try:
        use_max = _choose_max_length(final_text)
        out = summarizer(final_text, max_new_tokens=use_max, min_length=min_length, truncation=True)
        return out[0]["summary_text"].strip()
    except Exception:
        return final_text
