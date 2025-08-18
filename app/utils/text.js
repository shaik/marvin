// Simple RTL detection based on presence of strong RTL Unicode ranges
// Hebrew (0590–05FF), Arabic (0600–06FF), Syriac (0700–074F), etc.
export function detectRtl(text) {
  if (!text || typeof text !== 'string') return false;
  const rtlRegex = /[\u0590-\u08FF]/; // covers common RTL blocks
  return rtlRegex.test(text);
}

export default detectRtl;


