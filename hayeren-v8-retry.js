// Preloaded by NODE_OPTIONS before hayeren-v8-host.js.
// Retries only safe read requests to the legacy v6 upstream so a Render cold start
// does not leave the Telegram Mini App on an empty/boot screen.
const nativeFetch = globalThis.fetch.bind(globalThis);
const UPSTREAM = 'https://hayeren-v6-live.onrender.com';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function requestUrl(input) {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.href;
  return input && typeof input.url === 'string' ? input.url : '';
}

function requestMethod(input, init) {
  return String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
}

globalThis.fetch = async function hayerenResilientFetch(input, init) {
  const url = requestUrl(input);
  const method = requestMethod(input, init);
  const shouldRetry = url.startsWith(UPSTREAM) && (method === 'GET' || method === 'HEAD');
  if (!shouldRetry) return nativeFetch(input, init);

  let lastError;
  for (let attempt = 1; attempt <= 6; attempt++) {
    try {
      const response = await nativeFetch(input, init);
      if (response.ok || (response.status !== 502 && response.status !== 503 && response.status !== 504)) {
        if (attempt > 1) console.log(`UPSTREAM_RECOVERED attempt=${attempt} status=${response.status}`);
        return response;
      }
      lastError = new Error(`upstream ${response.status}`);
      // Consume the transient response before retrying so sockets can be reused cleanly.
      try { await response.arrayBuffer(); } catch {}
    } catch (error) {
      lastError = error;
    }
    if (attempt < 6) {
      const delay = Math.min(1500 * attempt, 6000);
      console.warn(`UPSTREAM_RETRY attempt=${attempt} delay=${delay}ms reason=${lastError && lastError.message}`);
      await sleep(delay);
    }
  }
  throw lastError || new Error('upstream unavailable');
};
