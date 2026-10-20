"""Create reproducible, fictional English intent examples; never read chat data.

Examples describe language acts, not diagnoses or treatment recommendations.
Evaluation messages are read only to exclude exact and normalized duplicates.
Each template family is kept together by example_group during validation.
"""

import json
from pathlib import Path

from model.config import PROJECT_DIR
from model.text_understanding import clean_message
from model.training_data import default_training_paths, example_group, load_training_examples


AREAS = ['bellybutton', 'navel', 'tummy', 'torso', 'nape', 'underarm',
         'knuckle', 'fingertip', 'jawline', 'earlobe', 'toenail', 'shoulderblade']
SYMPTOMS = ['stinging', 'tingling', 'flaking', 'burning', 'itching', 'redness',
            'dryness', 'irritation', 'scaling', 'crusting', 'soreness', 'tightness']
TIMEFRAMES = ['thirteen days', 'twenty-one days', 'six nights', 'a couple of nights',
              'half an hour', 'about eleven weeks', 'roughly sixteen months',
              'nearly nine days', 'around fourteen hours', 'a little over six weeks']
LEVELS = ['mild', 'moderate', 'severe', 'slight', 'manageable', 'significant',
          'uncomfortable', 'bothersome', 'tolerable', 'intense', 'minimal', 'bearable']
PRODUCTS = ['a cream', 'an ointment', 'a lotion', 'a moisturizer', 'a gel', 'medication']


def reserve_evaluation_messages():
    # Do not copy evaluation wording into the training set.
    from eval.final_test_cases import FINAL_TEST_CASES
    from eval.check_english_chatbot import SCENARIOS
    messages = [text for text, _ in FINAL_TEST_CASES]
    messages.extend(turn['text'] for _, turns in SCENARIOS for turn in turns)
    for path in (PROJECT_DIR / 'eval').glob('*cases.json'):
        content = json.loads(path.read_text(encoding='utf-8'))
        for item in content:
            if 'message' in item:
                messages.append(item['message'])
            messages.extend(item.get('texts', []))
            messages.extend(turn['text'] for turn in item.get('turns', []))
    return {clean_message(text) for text in messages}


def generated_patterns():
    families = {
        'location': (AREAS, [
            'The affected site I can identify is my {value}',
            'To answer where, I would point at my {value}',
            'The area involved is just beside my {value}',
            'I am indicating the skin surrounding my {value}',
            'The place I meant was my {value}',
            'Please record my {value} as the affected body area',
            'The visible change is limited to the {value} area',
            'It sits along the edge of my {value}',
        ]),
        'symptom': (SYMPTOMS, [
            'What I notice on the skin is {value}',
            'The sensation I want to describe is {value}',
            'I am reporting {value} of the skin',
            'My main skin complaint would be {value}',
            'I keep noticing some {value}',
            'The change that stands out to me is {value}',
            'There has been noticeable {value}',
            'The skin seems to have developed {value}',
        ]),
        'duration': (TIMEFRAMES, [
            'For the timeframe, I would say {value}',
            'The total time so far is {value}',
            'Counting from the start, that makes {value}',
            'My best estimate of its duration is {value}',
            'It first showed up {value} ago',
            'By now the problem has lasted {value}',
            'I would put the onset at {value} ago',
            'The elapsed time is {value}',
        ]),
        'severity': (LEVELS, [
            'I would describe the discomfort as {value}',
            'The level of discomfort is {value}',
            'For severity, my answer is {value}',
            'Overall it feels {value} to me',
            'My description of how bad it feels is {value}',
            'I would rate the symptoms as {value}',
            'The intensity feels {value}',
            'It remains {value} rather than changing',
        ]),
        'medication': (PRODUCTS, [
            'I have already tried {value} for this problem',
            'I used {value} before starting this conversation',
            'I am using {value} at the moment',
            'I have not used {value} for the affected skin',
            'So far I have tried only {value}',
            'I was using {value} before I contacted you',
            'The product I have used is {value}',
            'For treatment history, I tried {value}',
        ]),
    }
    patterns = {tag: [template.format(value=value) for template in templates for value in values]
                for tag, (values, templates) in families.items()}
    patterns.update({
        'greeting': [
            'Hello, is somebody available to chat?', 'Hey there, may I ask for help?',
            'Good morning, are you available?', 'Hi, I am here to start a conversation',
            'Hello again, can we chat for a moment?', 'Hi there, I have just arrived',
            'Greetings, is the assistant ready?', 'Hello, I would like to begin',
            'Hi, is now a good time to talk?', 'Hey, are you around to help today?',
            'Morning, can we begin our chat?', 'Good evening, I would like some help',
        ],
        'confirmation': [
            'Yes, that matches what I intended', 'Correct, you understood that detail',
            'Exactly, that is the information I gave', 'Yes, please keep that detail',
            'That interpretation matches what I meant', 'I can confirm that part is right',
            'No, that does not match my description', 'That is inaccurate, I meant something else',
            'I disagree with that detail', 'The information you repeated is not correct',
            'That assumption does not fit what I said', 'Yes, you have the right information',
        ],
        'emergency': [
            'My throat is swelling and air is difficult to get in',
            'I cannot swallow and my tongue is swollen',
            'My lips have swollen and I am struggling to breathe',
            'My mouth is swelling and I cannot breathe normally',
            'I am having difficulty swallowing with a swollen throat',
            'My tongue is swollen and breathing is difficult',
            'My eyes are swelling and I have trouble breathing',
            'I have swollen lips and difficulty swallowing right now',
            'My throat is swollen and I am barely able to breathe',
            'My face is swelling and I cannot swallow properly',
            'I am struggling to breathe with swelling of my tongue',
            'My lips are swelling and I am short of breath',
        ],
        'image_upload': [
            'I would like to attach a close-up photo for the screening',
            'May I provide a photograph of the affected skin?',
            'I am ready to share a skin photograph now',
            'Let me supply a new photo for you to look at',
            'Could I submit another photograph of the area?',
            'I want to choose an image from my device',
            'Can I attach a skin photo to this conversation?',
            'I would like to send a clearer photograph',
            'Please let me provide an image for the skin screening',
            'I plan to upload a close-up of the patch',
            'May I share the picture I took of the area?',
            'I have a photograph to upload for this screening',
        ],
        'goodbye': [
            'I am leaving the conversation now, goodbye',
            'That concludes my questions for today, bye',
            'I will close the chat now, take care',
            'I need to leave now, we can talk another time',
            'I am signing out of this conversation, goodbye',
            'I have finished for today, see you another time',
            'I am heading off now, bye for the moment',
            'Let us end the conversation here, goodbye',
            'I am going now, thank you and goodbye',
            'Nothing more to ask today, bye',
            'I will come back another day, goodbye for now',
            'It is time for me to go, see you later',
        ],
        'thanks': [
            'I appreciate the clear explanation you gave',
            'Thank you for taking time to explain that',
            'That was useful information, thank you',
            'Your explanation helped me understand, thanks',
            'Many thanks for answering my concern',
            'I appreciate your patience with my questions',
            'Thank you, I understand the explanation better now',
            'I am grateful for the information',
            'Thank you for walking me through the information',
            'That clarification was helpful, much appreciated',
            'Thanks for helping me organize those details',
            'I appreciate you answering that question',
        ],
        'bot_identity': [
            'Which tasks can this skin assistant help me with?',
            'What kinds of questions are supported here?',
            'Can you describe the purpose of this assistant?',
            'What are this chatbot\'s limitations?',
            'Is this chat a replacement for a dermatologist?',
            'Can this chatbot confirm a medical diagnosis?',
            'Where is my conversation history kept?',
            'Are messages stored after I close the browser?',
            'Will my conversation be used to retrain the assistant?',
            'Does this assistant learn automatically as we talk?',
            'Which skin conditions are covered by the screening?',
            'How is a photo screening different from a diagnosis?',
        ],
        'unknown': [
            'The arm of this sofa has a broken seam',
            'My garden path has dry patches of concrete',
            'Please write a song about the moon',
            'Can you calculate the tax on a new laptop?',
            'How do I connect this printer to wireless internet?',
            'My computer screen keeps showing red pixels',
            'Recommend a camera for photographing landscapes',
            'I need a recipe for a cream sauce',
            'Explain how a football league ranks teams',
            'Can you translate a restaurant menu into Spanish?',
            'The wall paint is flaking near the window',
            'My bicycle tire has a bulging patch',
            'The palm tree in my yard needs pruning',
            'How do I renew a parking permit?',
            'Please debug a spreadsheet formula',
            'The torso of my mannequin needs painting',
            'Can you resize a company logo for me?',
            'I am shopping for a moisturizer display shelf',
            'Which train goes to the airport tomorrow?',
            'My jacket has a stain on the elbow patch',
            'Write a birthday invitation for a colleague',
            'How many calories are in this pasta recipe?',
            'Tell me the weather forecast for my holiday',
            'Explain the plot of a mystery novel',
        ],
    })
    return patterns


def main():
    existing, _ = load_training_examples([
        *default_training_paths(), PROJECT_DIR / 'data/english_location_supplement.json',
    ])
    reserved = reserve_evaluation_messages()
    existing_texts = {clean_message(item['text']) for item in existing}
    patterns = generated_patterns()
    intents, excluded = [], 0
    for tag, texts in patterns.items():
        kept = []
        for text in texts:
            normalized = clean_message(text)
            if normalized in reserved or normalized in existing_texts:
                excluded += 1
                continue
            kept.append(text)
            existing_texts.add(normalized)
        intents.append({'tag': tag, 'patterns': kept})
    path = PROJECT_DIR / 'data/english_intent_supplement.json'
    path.write_text(json.dumps({
        'description': 'Fictional English language acts; no patient chats, photographs, diagnoses, or treatment instructions.',
        'generator': 'eval/create_english_intent_supplement.py',
        'intents': intents,
    }, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(path), 'examples': sum(len(i['patterns']) for i in intents),
                      'reserved_or_existing_excluded': excluded,
                      'template_groups': len({example_group(text) for i in intents for text in i['patterns']})}, indent=2))


if __name__ == '__main__':
    main()
