// Presentation metadata only — actual classification happens server-side
// via your trained model at POST /predict. This just maps whatever
// `intent` string comes back to a color + default quick-reply chips
// so the UI has something sensible to show even before you wire up
// real follow-up logic on the backend.
export const INTENTS = {
  greeting:     { color: '#0F5C56', label: 'greeting' },
  symptom:      { color: '#E8592A', label: 'symptom' },
  answer:       { color: '#8A6D3B', label: 'answer' },
  medication:   { color: '#4C6FBF', label: 'medication' },
  emergency:    { color: '#C43A3A', label: 'emergency' },
  image_upload: { color: '#7A5CC0', label: 'image upload' },
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
