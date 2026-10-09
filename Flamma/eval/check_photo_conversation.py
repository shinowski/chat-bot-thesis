"""Replay the reported text using the trained classifier and a fixed image result.

Run from Flamma: venv/Scripts/python.exe -B -m eval.check_photo_conversation
The fixture isolates conversation handling; this does not measure image accuracy.
"""

import contextlib
import io
from pathlib import Path
import json

from app import create_app
from model.semantic_chatbot import SemanticChatbot
from test_image_integration import FakeImageClassifier
from test_image_integration import make_bot
from werkzeug.datastructures import FileStorage
from test_text_understanding import prepare_bot


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        image = FakeImageClassifier()
        image.result['confidence'] = 0.758
        bot = SemanticChatbot(image_classifier=image)
        cases = json.loads((Path(__file__).parent / 'language_cases.json').read_text(encoding='utf-8'))
        for case in cases:
            prepared = prepare_bot(case['stage'])
            prepared.classifier = bot.classifier
            result = prepared.reply(case['message'])
            assert result['intent'] == case['intent'], (case, result['intent'], result['predictedIntent'])

        for raw, name in [('atopic_dermatitis', 'Atopic Dermatitis'), ('contact_dermatitis', 'Contact Dermatitis'),
                          ('lichen_planus', 'Lichen Planus'), ('psoriasis', 'Psoriasis'), ('rosacea', 'Rosacea'),
                          ('normal_skin', 'No Condition Detected')]:
            prepared = make_bot()
            prepared.classifier = bot.classifier
            prepared.image_classifier.result.update(predicted_class=raw, condition=name)
            prepared.reply('', FileStorage(filename='skin.png'))
            result = prepared.reply('what is this disease?')
            assert result['intent'] == 'knowledge_question', (raw, result)
            assert prepared.knowledge.get(raw, 'overview') in result['reply'], (raw, result)

        app = create_app(bot)
        client = app.test_client()
        try:
            for message in ['hello', 'can you help me', 'banana', 'lala mo', 'o my god']:
                result = client.post('/predict', json={'message': message, 'conversation_id': 'unrelated-text-report'}).get_json()
                if message in {'banana', 'lala mo', 'o my god'}:
                    assert result['intent'] in {'clarification', 'unknown'}, result
                    assert "I've noted" not in result['reply'], result
            summary = client.post('/predict', json={'message': 'summarize our conversation', 'conversation_id': 'unrelated-text-report'}).get_json()
            for field in ['Skin symptoms', 'Affected area', 'How long', 'Medication used']:
                assert f'{field}: not provided' in summary['reply'], summary
            for message, expected in [
                ('dsds', 'unknown'), ('hello', 'greeting'),
                ('i have a skin rashes can you help me', 'symptom'),
                ('can i send a photo?', 'image_request'),
            ]:
                result = client.post('/predict', json={'message': message}).get_json()
                assert result['intent'] == expected, (message, result)
            result = client.post('/predict', data={'image': (io.BytesIO(b'image-fixture'), 'skin.png')}).get_json()
            assert result['intent'] == 'image_classification', result
            assert 'Can you describe your skin problem' not in result['reply']
            unsure = client.post('/predict', json={'message': 'i dont know'}).get_json()
            assert unsure['intent'] == 'uncertain_answer'
            assert 'upload' not in unsure['reply'].lower()
            for message in ['what do you think in that images', 'i mean what is your thoiughts about it']:
                result = client.post('/predict', json={'message': message}).get_json()
                assert result['intent'] == 'image_explanation', result
                assert result['confidenceSource'] == 'image_model'
                assert 'Atopic Dermatitis' in result['reply']
                assert result['action'] is None
            assert image.calls == 1
            for message, expected in [
                ('dssd', {'unknown', 'clarification'}), ('hello', {'greeting'}),
                ('can i send a image for my skin disease?', {'image_request'}),
            ]:
                result = client.post('/predict', json={'message': message, 'conversation_id': 'latest-report'}).get_json()
                assert result['intent'] in expected, (message, result)
            result = client.post('/predict', data={
                'conversation_id': 'latest-report', 'message': 'can you help me',
                'image': (io.BytesIO(b'image-fixture'), 'skin.png'),
            }).get_json()
            assert result['reply'].startswith("The image model's closest match"), result
            treatment = client.post('/predict', json={'message': 'how can i treat it?', 'conversation_id': 'latest-report'}).get_json()
            assert treatment['intent'] == 'knowledge_question', treatment
            assert 'To continue the screening' not in treatment['reply']
            unsure = client.post('/predict', json={'message': 'i dont know', 'conversation_id': 'latest-report'}).get_json()
            assert 'shorter explanation' in unsure['reply'], unsure
            simple = client.post('/predict', json={'message': 'explane simply', 'conversation_id': 'latest-report'}).get_json()
            assert 'Short version' in simple['reply'], simple
            summary = client.post('/predict', json={'message': 'summarize our conversation', 'conversation_id': 'latest-report'}).get_json()
            assert 'Skin symptoms: not provided' in summary['reply'], summary
            assert 'How long: not provided' in summary['reply'], summary
            resumed = client.post('/predict', json={'message': 'continue screening', 'conversation_id': 'latest-report'}).get_json()
            assert 'Can you describe' in resumed['reply'], resumed
            for expected in ['Where', 'How long', 'Have you applied']:
                result = client.post('/predict', json={'message': 'i dont know', 'conversation_id': 'latest-report'}).get_json()
                assert expected in result['reply'], result
            for message in ['123', '456']:
                result = client.post('/predict', json={'message': message, 'conversation_id': 'latest-report'}).get_json()
                assert result['intent'] == 'invalid_medication', result
            result = client.post('/predict', json={'message': 'skip', 'conversation_id': 'latest-report'}).get_json()
            assert 'ask about your photo result' in result['reply']

            # Follow the knowledge topic without converting short replies into
            # patient facts. These calls use the real trained text classifier.
            for message, topic in [
                ('what causes psoriasis and how can I treat it?', 'causes'),
                ('and contagious?', 'contagious'),
                ('when should I see a doctor?', 'referral'),
            ]:
                result = client.post('/predict', json={'message': message, 'conversation_id': 'dialogue-check'}).get_json()
                assert result['intent'] == 'knowledge_question', result
                assert bot.knowledge.get('psoriasis', topic) in result['reply'], result
            result = client.post('/predict', json={'message': 'summarize our conversation', 'conversation_id': 'dialogue-check'}).get_json()
            assert 'Skin symptoms: not provided' in result['reply'], result
            assert 'Last classified photo:' not in result['reply'], result
        finally:
            app.extensions['chat_history'].db.close()
    print(f'Trained text model: {len(cases)}/{len(cases)} language cases passed.')
    print('Reported conversation: rash saved, uncertainty accepted, both photo follow-ups explained.')
    print('Latest conversation: no random location, no greeting on photo, no forced screening in care answers.')
    print('Dialogue: context-aware uncertainty, simple explanations, summaries, resume, and multi-part questions passed.')
    print('Disease explanations: all six photo labels and named conditions are routed with the trained text classifier.')
    print('Unrelated-text report: banana, lala mo, and o my god never become patient facts.')
    print('Image inference uses a fixed fixture in this conversation check.')


if __name__ == '__main__':
    main()
