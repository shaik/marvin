import Constants from 'expo-constants';

/**
 * Get configuration from Expo constants.
 * @returns {Object} { baseUrl, apiKey }
 * @throws {Error} If HEROKU_URL is not configured
 */
export function getConfig() {
  // Support both new expoConfig.extra and legacy manifest.extra
  const extra = Constants.expoConfig?.extra || Constants.manifest?.extra || {};
  
  const baseUrl = extra.HEROKU_URL;
  const apiKey = extra.API_AUTH_KEY;
  
  if (!baseUrl) {
    throw new Error("HEROKU_URL is not set. Please create app/.env file with HEROKU_URL=http://your-server-url");
  }
  
  return {
    baseUrl: baseUrl.trim(),
    apiKey: apiKey ? apiKey.trim() : ""
  };
}

/**
 * Make authenticated API request.
 * @param {string} endpoint - API endpoint path
 * @param {Object} body - Request body object
 * @returns {Promise<Object>} { ok, status, json }
 */
async function makeApiRequest(endpoint, body, extraHeaders = {}) {
  const { baseUrl, apiKey } = getConfig();
  
  const headers = {
    'Content-Type': 'application/json'
  };
  
  // Add API key header only if apiKey is non-empty
  if (apiKey) {
    headers['X-API-KEY'] = apiKey;
  }
  // Merge any extra headers
  Object.assign(headers, extraHeaders || {});
  
  const url = `${baseUrl}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    
    let json;
    try {
      json = await response.json();
    } catch (parseError) {
      // If JSON parsing fails, include response text in error
      const text = await response.text();
      json = { 
        error: "Failed to parse response as JSON", 
        responseText: text,
        parseError: parseError.message 
      };
    }
    
    return {
      ok: response.ok,
      status: response.status,
      json
    };
    
  } catch (networkError) {
    return {
      ok: false,
      status: 0,
      json: {
        error: "Network error",
        message: networkError.message,
        code: networkError.code || "NETWORK_ERROR"
      }
    };
  }
}

/**
 * Store a memory in Marvin.
 * @param {string} text - Memory text to store
 * @param {string} language - Language code (default: 'he')
 * @returns {Promise<Object>} API response { ok, status, json }
 */
export async function storeMemory(text, language = 'he') {
  if (!text || typeof text !== 'string' || !text.trim()) {
    throw new Error("Memory text is required and must be a non-empty string");
  }
  
  return makeApiRequest('/api/v1/store', {
    text: text.trim(),
    language
  });
}

/**
 * Query memories from Marvin.
 * @param {string} query - Search query
 * @returns {Promise<Object>} API response { ok, status, json }
 */
export async function queryMemory(query) {
  if (!query || typeof query !== 'string' || !query.trim()) {
    throw new Error("Query text is required and must be a non-empty string");
  }
  
  return makeApiRequest('/api/v1/query', {
    query: query.trim()
  });
}

/**
 * Auto-decide action (store/retrieve/clarify) via backend LLM.
 * @param {string} text - User input text
 * @param {{ force?: 'store' | 'retrieve' }} [opts] - Optional override to force action
 * @returns {Promise<{ ok: boolean, status: number, json: any }>}
 */
export async function auto(text, opts = {}) {
  if (!text || typeof text !== 'string' || !text.trim()) {
    throw new Error("Text is required and must be a non-empty string");
  }

  const body = { text: text.trim() };
  if (opts.force === 'store' || opts.force === 'retrieve') {
    body.force_action = opts.force;
  }
  if (opts.preferredLanguage) {
    body.preferredLanguage = opts.preferredLanguage;
  }
  const extraHeaders = opts.preferredLanguage ? { 'Accept-Language': opts.preferredLanguage } : {};
  return makeApiRequest('/api/v1/auto', body, extraHeaders);
}