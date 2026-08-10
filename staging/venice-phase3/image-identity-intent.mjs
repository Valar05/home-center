const IMAGE_REQUEST = /\b(?:make|generate|create|draw|paint|show me)\s+(?:me\s+)?(?:an?\s+)?(?:picture|image|photo|portrait|scene)\b\s*(?:of|with|showing|where)?\s*(.*)$/i;
const CITY_MARKERS = /\b(?:city|canals?|gondolas?|lagoon|italy|italian|piazza|san marco|rialto|adriatic|flooded streets?)\b/i;
const PERSON_MARKERS = /\b(?:woman|girl|person|character|her|she|herself|face|eyes|hair|wearing|dressed|portrait|selfie|body|standing|sitting|walking|smiling|looking)\b/i;
const DIRECT_PERSON_PATTERNS = [
  /\bportrait\s+(?:of\s+)?Venice\b/i,
  /\b(?:draw|paint|render|show|depict|illustrate)\s+(?:me\s+)?Venice\b/i,
  /\bVenice\s+(?:herself|the\s+woman|the\s+character)\b/i,
];

function clean(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

export function extractVoiceImagePrompt(transcript) {
  const match = clean(transcript).match(IMAGE_REQUEST);
  if (!match) return null;
  const subject = clean(match[1]).replace(/^[,;:\-]+|[,;:\-]+$/g, '').trim();
  if (!subject || /^(?:it|this|that|something|anything|a picture|an image|a photo|a portrait|a scene)$/i.test(subject)) return null;
  return subject;
}

export function requestsVeniceIdentity(prompt) {
  const text = clean(prompt);
  if (!/\bVenice\b/i.test(text)) return false;
  if (DIRECT_PERSON_PATTERNS.some((pattern) => pattern.test(text))) return true;
  const hasPerson = PERSON_MARKERS.test(text);
  const hasCity = CITY_MARKERS.test(text);
  if (hasCity && !hasPerson) return false;
  return true;
}
