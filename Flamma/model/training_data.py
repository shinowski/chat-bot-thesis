"""Normalize, audit, and group fictional intent examples before training."""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from model.config import PROJECT_DIR
from model.text_understanding import (
    LOCATION_WORDS, SYMPTOM_WORDS, SEVERITY_WORDS, MEDICATION_WORDS,
    DURATION_QUANTITY, DURATION_UNIT, clean_message, normalize_message,
)


def default_training_paths():
    return [PROJECT_DIR / 'data/intents.json', PROJECT_DIR / 'data/training_supplement.json']


def example_group(text):
    """Keep vocabulary substitutions within a template in the same fold."""
    text = clean_message(text)
    text = re.sub(r'\b(?:(?:about|roughly|nearly|around|a little over) )?(?:a )?'
                  + DURATION_QUANTITY + r'\s+' + DURATION_UNIT + r'\b', '<time>', text)
    product_pattern = r'\b(?:(?:a|an|some|any) )?(?:' + '|'.join(sorted(MEDICATION_WORDS, key=len, reverse=True)) + r')\b'
    text = re.sub(product_pattern, '<product>', text)
    for words, slot in [(LOCATION_WORDS, 'area'), (SYMPTOM_WORDS, 'symptom'), (SEVERITY_WORDS, 'severity')]:
        pattern = r'\b(?:(?:left|right|both|upper|lower)\s+)?(?:' + '|'.join(sorted(words, key=len, reverse=True)) + r')\b'
        text = re.sub(pattern, '<' + slot + '>', text)
    text = re.sub(r'\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b', '<number>', text)
    text = re.sub(r'\b' + DURATION_UNIT + r'\b', '<unit>', text)
    return ' '.join(re.sub(r'[^a-z0-9<>]+', ' ', text).split())


def load_training_examples(paths=None):
    paths = paths if paths is not None else default_training_paths()
    by_text = defaultdict(dict)
    sources, raw_count = [], 0
    for path in paths:
        path = Path(path)
        content = path.read_bytes()
        sources.append({'path': str(path), 'sha256': hashlib.sha256(content).hexdigest()})
        for intent in json.loads(content)['intents']:
            for pattern in intent['patterns']:
                normalized = normalize_message(pattern)
                if not re.search(r'[a-z]', normalized):
                    continue
                raw_count += 1
                by_text[clean_message(normalized)][intent['tag']] = normalized
    conflicts = [text for text, labels in by_text.items() if len(labels) > 1]
    examples = [dict(text=next(iter(labels.values())), label=next(iter(labels)), group=example_group(text))
                for text, labels in by_text.items() if len(labels) == 1]
    return examples, {
        'sources': sources, 'input_examples': raw_count, 'unique_examples': len(examples),
        'duplicates_removed': raw_count - sum(len(labels) for labels in by_text.values()), 'conflicts_excluded': conflicts,
        'class_counts': dict(Counter(item['label'] for item in examples)),
        'template_groups': len({item['group'] for item in examples}),
    }
