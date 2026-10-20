// Model outputs need a visible meaning; old unsourced scores are not interpretable.
export function formatModelPercent(value) {
  if (!Number.isFinite(value) || value < 0 || value > 1) return null;
  if (value > 0 && value < .0005) return '<0.1%';
  if (value < 1 && value >= .9995) return '>99.9%';
  return `${(value * 100).toFixed(1).replace(/\.0$/, '')}%`;
}

export function modelScore(value, source) {
  if (!Number.isFinite(value) || value < 0 || value > 1) return null;
  if (source === 'intent_model') return {
    label: 'Message intent score', percent: formatModelPercent(value),
    explanation: 'How strongly the text model matched a message category. This is not medical accuracy or a disease probability.',
  };
  if (source === 'image_model') return {
    label: 'Photo model score', percent: formatModelPercent(value),
    explanation: 'The image model output for its screening match. This is not a diagnosis, measured clinical accuracy, or your probability of having a disease.',
  };
  return null;
}
