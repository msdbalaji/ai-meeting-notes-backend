# backend/app/precache_models.py
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForTokenClassification, pipeline

HF_CACHE = os.getenv("HF_CACHE_DIR", r"D:\projects\ai-meeting-notes\models\hf_cache")
os.makedirs(HF_CACHE, exist_ok=True)

SUM_MODEL = os.getenv("SUMMARIZER_MODEL", "t5-small")
NER_MODEL = os.getenv("NER_MODEL", "dslim/bert-base-NER")

print("Cache dir:", HF_CACHE)

# Summarizer
print("Pre-downloading summarizer:", SUM_MODEL)
AutoTokenizer.from_pretrained(SUM_MODEL, cache_dir=HF_CACHE)
AutoModelForSeq2SeqLM.from_pretrained(SUM_MODEL, cache_dir=HF_CACHE)
print("Summarizer cached.")

# NER model + tokenizer (use cache_dir here)
print("Pre-downloading NER:", NER_MODEL)
tokenizer = AutoTokenizer.from_pretrained(NER_MODEL, cache_dir=HF_CACHE)
model = AutoModelForTokenClassification.from_pretrained(NER_MODEL, cache_dir=HF_CACHE)
print("NER model + tokenizer cached.")

# Build a pipeline using the already-loaded model/tokenizer (do NOT pass cache_dir to pipeline)
print("Creating a token-classification pipeline (to ensure full initialization)...")
ner_pipe = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=-1)
print("NER pipeline initialized and cached.")

print("Done precaching models.")
