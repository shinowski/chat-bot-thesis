"""Freeze authored final cases and prepare separate development examples."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
from model.text_understanding import clean_message, normalize_message
from model.training_data import example_group, load_training_examples

def normalized(text):
    return clean_message(normalize_message(text))

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def main():
    if (HERE / 'final-set.lock.json').exists():
        raise SystemExit('Final set is already frozen; do not silently replace it.')
    previous = set()
    scanned = []
    for folder in [PROJECT/'data', PROJECT/'eval']:
        for path in folder.rglob('*.json'):
            if HERE in path.parents:
                continue
            for value in strings(json.loads(path.read_text(encoding='utf-8'))):
                previous.add(normalized(value))
            scanned.append(str(path.relative_to(PROJECT)))
    for path in [*PROJECT.glob('test*.py'), *(PROJECT/'eval').glob('*.py')]:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        previous.update(normalized(node.value) for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str))
        scanned.append(str(path.relative_to(PROJECT)))
    cases, intent = [], None
    for line in (HERE/'final_messages.txt').read_text(encoding='utf-8').splitlines():
        if line.startswith('['):
            intent = line.strip('[]')
        elif line.strip():
            cases.append({'id': f'F{len(cases)+1:03d}', 'text': line, 'expected': intent,
                          'short_reply': len(line.split()) <= 6, 'ambiguous': intent == 'unknown'})
    counts = dict(Counter(x['expected'] for x in cases))
    assert len(cases) == 260 and set(counts.values()) == {20}, counts
    conflicts = [x for x in cases if normalized(x['text']) in previous]
    assert not conflicts, 'Historical overlap; revise before freezing: ' + repr(conflicts)
    assert len({normalized(x['text']) for x in cases}) == len(cases)
    manifest = json.loads((PROJECT/'artifacts/intent_v5.metadata.json').read_text())
    sources = [Path(s['path']) if Path(s['path']).is_absolute() else PROJECT/s['path'] for s in manifest['training_audit']['sources']]
    training, audit = load_training_examples(sources)
    groups = {x['group'] for x in training}
    write('final-cases.json', cases)
    write('final-set.lock.json', {
        'frozen_at': datetime.now(timezone.utc).isoformat(), 'samples': len(cases), 'class_counts': counts,
        'sha256': hashlib.sha256((HERE/'final-cases.json').read_bytes()).hexdigest(),
        'protocol_sha256': hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),
        'historical_normalized_exact_overlap': 0, 'historical_files_scanned': scanned,
        'v5_template_group_overlap_count': sum(example_group(x['text']) in groups for x in cases),
        'authorship': 'New fictional messages authored by the coding assistant; independent human label review pending.',
        'label_policy': 'Single-turn dominant intent. Location requires a named anatomical site. Image upload includes intent to share a photo. Unknown means underspecified referent or question. Mixed-intent edge cases require human adjudication.',
        'limitations': 'Exact deduplication cannot establish semantic novelty. Shared intent vocabulary is expected. No predictions were made before this lock.',
    })

    # These development templates address known error families. They are never
    # derived from final predictions and never include old benchmark sentences.
    examples = {k: [] for k in counts}
    for description in ['itchy irritation', 'flaky rash', 'red scaly skin', 'new rough bumps', 'irritated skin', 'dry peeling patches', 'persistent itching', 'uncomfortable red spots']:
        for template in ["I am reporting {x} but have not said where it is.", "What I can describe is {x}.", "There are patches of {x} on the skin.", "I can see areas of {x} appearing.", "I have noticed some {x} developing.", "The skin changes include {x}.", "A patch of {x} keeps bothering me.", "My concern is {x}, with no area specified yet."]:
            examples['symptom'].append(template.format(x=description))
    for area in ['left shoulder', 'right shoulder', 'left ankle', 'right wrist', 'neck', 'right elbow', 'left calf', 'right ear', 'upper back', 'left palm', 'right knee', 'lower abdomen']:
        for template in ["The skin change is situated near my {x}.", "The irritated part is beside my {x}.", "My {x} is where the skin issue shows up.", "The problem appears at my {x}.", "The affected spot is close to my {x}.", "I am pointing to the skin around my {x}."]:
            examples['location'].append(template.format(x=area))
    for period in ['several days', 'a couple of weeks', 'many weeks', 'some months', 'fourteen days', 'three nights', 'six weeks', 'a few days']:
        for template in ["The rash has persisted for {x}.", "My irritation has lasted {x} already.", "The skin issue began {x} ago.", "It has been present for {x} so far.", "For {x}, this skin change has remained.", "I first noticed the skin problem {x} back."]:
            examples['duration'].append(template.format(x=period))
    for noun in ['image', 'picture', 'photo', 'photograph', 'snapshot']:
        for template in ["I attached a {x} showing my skin concern.", "Here is the {x} of my skin that I am sharing.", "I have uploaded my skin {x} for screening.", "The {x} I sent shows the affected skin.", "I've included a {x} of this irritated area.", "I would like you to screen the {x} I am attaching.", "I am submitting a close-up {x} of the rash.", "Please accept the {x} of my skin here.", "I want to share this {x} of an affected spot.", "I'm sending a {x} showing the patch."]:
            examples['image_upload'].append(template.format(x=noun))
    examples['unknown'] = [
        'What do you mean by the other option?', 'I have not decided what I want to ask.',
        'Can you clarify which thing you mean?', 'That is confusing without more information.',
        'I cannot tell what you are referring to here.', 'Which one are we discussing, exactly?',
        'What is the next bit supposed to mean?', 'Can we clarify the question before answering?',
        'I mean the other thing, but I cannot name it.', 'I have too little information to answer that.',
        'Something about this is not clear to me.', 'Maybe this thing, maybe the other one.',
        'Does that count if I have not described anything?', 'I was asking something else but forgot it.',
        'I need to understand which question you are asking.', 'How would you know without any details?',
    ]
    from eval.final_test_cases import FINAL_TEST_CASES
    old = {normalized(text) for text, _ in FINAL_TEST_CASES}
    final = {normalized(x['text']) for x in cases}
    supplement = {'description': 'Fictional development examples addressing known old benchmark errors; excludes new final set.', 'intents': []}
    for tag, texts in examples.items():
        kept = [t for t in texts if normalized(t) not in old | final]
        if kept:
            supplement['intents'].append({'tag': tag, 'patterns': kept, 'responses': []})
    write('development-supplement.json', supplement)
    print(json.dumps({'final_samples': len(cases), 'counts': counts, 'development_patterns': sum(len(x['patterns']) for x in supplement['intents']), 'template_overlap': sum(example_group(x['text']) in groups for x in cases)}, indent=2))

if __name__ == '__main__':
    main()
