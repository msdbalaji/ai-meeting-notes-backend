import sys
import os
# Ensure backend package is importable when running from repository root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.nlp import tasks

TEST = "This is a test transcript. Action: Alice to prepare the slides by Friday."

def main():
    print('Initializing spaCy (if available)...')
    tasks.init_spacy()
    print('Running extractor on test text:')
    items = tasks.extract_action_items(TEST)
    print('Extracted items:')
    for it in items:
        print(it)

    # Debug: print spaCy entities and token info for the sentence
    try:
        nlp = tasks._nlp
        if nlp is not None:
            doc = nlp(TEST)
            print('\nspaCy ents:')
            for ent in doc.ents:
                print(ent.text, ent.label_)
            print('\nTokens:')
            for tok in doc:
                print(f"{tok.text}\tpos={tok.pos_}\tdep={tok.dep_}\tlemma={tok.lemma_}\thead={tok.head.text}")
    except Exception as e:
        print('Debug failed:', e)

if __name__ == '__main__':
    main()
