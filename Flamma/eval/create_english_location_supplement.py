"""Create fictional location examples from the supported body-area vocabulary.

No test utterances, saved chats, photos, or patient data are read. Template
families remain together in grouped validation through training_data.py.
"""

import json
from model.config import PROJECT_DIR
from model.training_data import load_training_examples
from model.text_understanding import clean_message


AREAS = ['forearm', 'wrist', 'palm', 'elbow', 'ankle', 'heel', 'calf', 'shin',
         'thigh', 'knee', 'shoulder', 'scalp', 'forehead', 'cheek', 'chin', 'nose',
         'neck', 'upper back', 'lower back', 'chest', 'abdomen', 'ear', 'finger',
         'toe', 'sole', 'armpit', 'groin', 'hand', 'leg', 'arm']
TEMPLATES = [
    'My {area} is the body area I am asking about',
    'I can point to the problem on my {area}',
    'The patch I want to discuss sits on my {area}',
    'This spot has appeared on my {area}',
    'What bothers me is the skin on my {area}',
    'Please note that my {area} is affected',
    'I am describing the changes on my {area}',
    'The changes are confined to my {area}',
    'I mean the surface of my {area}',
    'My {area} is the part with the dry patch',
    'The patch of redness is on my {area}',
    'The spot that itches is on my {area}',
    'The part showing flakes is my {area}',
    'It is the skin over my {area} that feels irritated',
    'I am talking about a small patch on my {area}',
    'For the affected area, please put my {area}',
]


def main():
    existing, _ = load_training_examples()
    existing_texts = {clean_message(item['text']) for item in existing}
    patterns = [template.format(area=area) for template in TEMPLATES for area in AREAS
                if clean_message(template.format(area=area)) not in existing_texts]
    path = PROJECT_DIR / 'data/english_location_supplement.json'
    path.write_text(json.dumps({
        'description': 'Fictional body-area intent descriptions, not medical diagnoses or real patient records.',
        'intents': [{'tag': 'location', 'patterns': patterns}],
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Created {len(patterns)} fictional location examples in {path.name}.')


if __name__ == '__main__':
    main()
