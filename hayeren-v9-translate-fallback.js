// Loaded before hayeren-v9-assets.js.
// Keeps the existing Google translator as primary and uses independent Lingva
// public instances only when Google rate-limits or is temporarily unavailable.
const nativeFetch = globalThis.fetch.bind(globalThis);
const INSTANCES = [
  'https://lingva.ml',
  'https://lingva.lunar.icu',
  'https://translate.plausibility.cloud',
  'https://translate.projectsegfau.lt'
];

function validTranslation(text, target) {
  text = String(text || '').trim();
  if (!text) return false;
  if (target === 'hy') return /[Ա-Ֆա-ֆև]/.test(text);
  if (target === 'ru') return /[А-Яа-яЁё]/.test(text);
  return true;
}

async function lingvaTranslate(source, target, query) {
  let lastError;
  for (const base of INSTANCES) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 7000);
    try {
      const url = `${base}/api/v1/${encodeURIComponent(source)}/${encodeURIComponent(target)}/${encodeURIComponent(query)}`;
      const response = await nativeFetch(url, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json', 'User-Agent': 'Hayeren/10 Lingva fallback' }
      });
      if (!response.ok) throw new Error(`${base} HTTP ${response.status}`);
      const data = await response.json();
      const translated = String(data && data.translation || '').trim();
      if (!validTranslation(translated, target)) throw new Error(`${base} invalid translation`);
      console.warn(`TRANSLATOR_LINGVA_OK host=${new URL(base).host} pair=${source}|${target}`);
      return translated;
    } catch (error) {
      lastError = error;
      console.warn(`TRANSLATOR_LINGVA_RETRY host=${new URL(base).host} reason=${error && error.message}`);
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError || new Error('Lingva unavailable');
}

globalThis.fetch = async function hayerenLingvaFallback(input, init) {
  const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : (input && input.url) || '';
  if (!/translate\.googleapis\.com\/translate_a\/single/.test(raw)) return nativeFetch(input, init);

  let primary;
  let primaryError;
  try {
    primary = await nativeFetch(input, init);
    if (primary.ok) return primary;
    if (![403, 429, 500, 502, 503, 504].includes(primary.status)) return primary;
  } catch (error) {
    primaryError = error;
  }

  try {
    const url = new URL(raw);
    const query = url.searchParams.get('q') || '';
    const source = (url.searchParams.get('sl') || 'ru').slice(0, 2);
    const target = (url.searchParams.get('tl') || 'hy').slice(0, 2);
    const translated = await lingvaTranslate(source, target, query);
    return new Response(JSON.stringify([[[translated, query, null, null, 10]], null, source]), {
      status: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'X-Hayeren-Translator': 'lingva-fallback' }
    });
  } catch (fallbackError) {
    console.error(`TRANSLATOR_LINGVA_ERROR primary=${primary ? primary.status : (primaryError && primaryError.message) || 'network'} fallback=${fallbackError && fallbackError.message}`);
    if (primary) return primary;
    throw primaryError || fallbackError;
  }
};
