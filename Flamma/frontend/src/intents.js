// Display metadata. The backend resolves intent and supplies follow-up choices.
export const INTENTS = {
  greeting:     { color: '#0F5C56', label: 'greeting' },
  symptom:      { color: '#E8592A', label: 'symptom' },
  answer:       { color: '#8A6D3B', label: 'answer' },
  medication:   { color: '#4C6FBF', label: 'medication' },
  emergency:    { color: '#C43A3A', label: 'emergency' },
  image_upload: { color: '#7A5CC0', label: 'image upload' },
  image_request: { color: '#7A5CC0', label: 'photo request' },
  image_declined: { color: '#9A9188', label: 'continue in text' },
  image_followup: { color: '#7A5CC0', label: 'photo follow-up' },
  image_explanation: { color: '#7A5CC0', label: 'result explanation' },
  uncertain_answer: { color: '#8A6D3B', label: 'unsure answer' },
  knowledge_question: { color: '#2E7D8C', label: 'skin information' },
  conversation_summary: { color: '#2E7D8C', label: 'conversation summary' },
  simple_explanation: { color: '#2E7D8C', label: 'simple explanation' },
  screening_pause: { color: '#5C6D68', label: 'questions paused' },
  screening_resume: { color: '#0F5C56', label: 'continue screening' },
  image_classification: { color: '#7A5CC0', label: 'image result' },
  image_rejected: { color: '#9A9188', label: 'image rejected' },
  image_error: { color: '#9A9188', label: 'image unavailable' },
  goodbye:      { color: '#5C6D68', label: 'goodbye' },
  thanks:       { color: '#3E9C6E', label: 'thanks' },
  bot_identity: { color: '#2E7D8C', label: 'bot identity' },
  unknown:      { color: '#9A9188', label: 'unknown' },
};

export const DEFAULT_FOLLOWUPS = {
  symptom: ["It's on my arm", "It's on my face", "It's been a few days", "It's very itchy"],
  answer: ['Yes', 'No', "It's getting worse"],
  medication: ['Intact skin', 'Broken / weeping'],
  unknown: ["It's a rash", "It's itchy", "It's painful"],
};

export function intentMeta(intent) {
  return INTENTS[intent] || { color: '#0F5C56', label: intent || 'unknown' };
}
