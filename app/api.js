/**
 * Marvin Memory Assistant API Service
 * Handles communication with the backend memory service
 */

import { HEROKU_URL } from '@env';

// API Configuration
const API_BASE_URL = HEROKU_URL || 'http://localhost:5000';
const API_VERSION = 'v1';
const API_ENDPOINT = `${API_BASE_URL}/api/${API_VERSION}`;

// Request timeout in milliseconds
const REQUEST_TIMEOUT = 30000;

/**
 * Generic API request handler with error handling and timeout
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} API response data
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_ENDPOINT}${endpoint}`;
  
  // Default headers
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // Merge headers
  const headers = {
    ...defaultHeaders,
    ...options.headers,
  };

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    console.log(`[API] ${options.method || 'GET'} ${url}`);
    
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      throw new Error(`Invalid response format: ${contentType}`);
    }

    const data = await response.json();

    if (!response.ok) {
      // Handle API error responses
      const error = new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    console.log(`[API] Success: ${endpoint}`);
    return data;

  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout: ${endpoint}`);
    }
    
    console.error(`[API] Error: ${endpoint}`, error.message);
    throw error;
  }
}

/**
 * Store a new memory with optional metadata
 * @param {string} text - Memory text to store
 * @param {string} language - Language of the memory (default: 'he')
 * @param {string|null} location - Optional location context
 * @returns {Promise<Object>} Store response with duplicate detection info
 */
export async function storeMemory(text, language = 'he', location = null) {
  if (!text || !text.trim()) {
    throw new Error('Memory text cannot be empty');
  }

  const payload = {
    text: text.trim(),
    language,
    location,
  };

  try {
    const response = await apiRequest('/store', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Memory stored:', {
      memory_id: response.memory_id,
      duplicate_detected: response.duplicate_detected,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to store memory:', error.message);
    throw new Error(`Failed to store memory: ${error.message}`);
  }
}

/**
 * Query memories using semantic similarity search
 * @param {string} query - Search query text
 * @param {number} topK - Number of top results to return (default: 3)
 * @returns {Promise<Object>} Query response with memory candidates
 */
export async function queryMemory(query, topK = 3) {
  if (!query || !query.trim()) {
    throw new Error('Query cannot be empty');
  }

  if (topK <= 0 || topK > 100) {
    throw new Error('topK must be between 1 and 100');
  }

  const payload = {
    query: query.trim(),
    top_k: topK,
  };

  try {
    const response = await apiRequest('/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Memory query completed:', {
      query,
      results_count: response.candidates?.length || 0,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to query memories:', error.message);
    throw new Error(`Failed to query memories: ${error.message}`);
  }
}

/**
 * Update an existing memory
 * @param {string} memoryId - ID of the memory to update
 * @param {string} newText - New text content
 * @returns {Promise<Object>} Update response
 */
export async function updateMemory(memoryId, newText) {
  if (!memoryId || !memoryId.trim()) {
    throw new Error('Memory ID cannot be empty');
  }

  if (!newText || !newText.trim()) {
    throw new Error('New text cannot be empty');
  }

  const payload = {
    memory_id: memoryId.trim(),
    new_text: newText.trim(),
  };

  try {
    const response = await apiRequest('/update', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Memory updated:', {
      memory_id: memoryId,
      success: response.success,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to update memory:', error.message);
    throw new Error(`Failed to update memory: ${error.message}`);
  }
}

/**
 * Delete a memory
 * @param {string} memoryId - ID of the memory to delete
 * @returns {Promise<Object>} Delete response
 */
export async function deleteMemory(memoryId) {
  if (!memoryId || !memoryId.trim()) {
    throw new Error('Memory ID cannot be empty');
  }

  const payload = {
    memory_id: memoryId.trim(),
  };

  try {
    const response = await apiRequest('/delete', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Memory deleted:', {
      memory_id: memoryId,
      success: response.success,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to delete memory:', error.message);
    throw new Error(`Failed to delete memory: ${error.message}`);
  }
}

/**
 * Handle cancellation intent
 * @param {string} lastInput - Last user input to identify target memory
 * @returns {Promise<Object>} Cancel response with confirmation text
 */
export async function handleCancel(lastInput) {
  if (!lastInput || !lastInput.trim()) {
    throw new Error('Last input cannot be empty');
  }

  const payload = {
    last_input: lastInput.trim(),
  };

  try {
    const response = await apiRequest('/cancel', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Cancel request processed:', {
      target_memory_id: response.target_memory_id,
      has_target: !!response.target_memory_id,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to handle cancel:', error.message);
    throw new Error(`Failed to handle cancel: ${error.message}`);
  }
}

/**
 * Get clarification for ambiguous queries
 * @param {string} query - Ambiguous query text
 * @returns {Promise<Object>} Clarification response
 */
export async function getClarification(query) {
  if (!query || !query.trim()) {
    throw new Error('Query cannot be empty');
  }

  const payload = {
    query: query.trim(),
  };

  try {
    const response = await apiRequest('/clarify', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    console.log('[API] Clarification processed:', {
      query,
      has_clarification: !!response.clarification_question,
      candidates_count: response.candidates?.length || 0,
    });

    return response;
  } catch (error) {
    console.error('[API] Failed to get clarification:', error.message);
    throw new Error(`Failed to get clarification: ${error.message}`);
  }
}

/**
 * Check API health
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  try {
    const response = await apiRequest('/health', {
      method: 'GET',
    });

    console.log('[API] Health check passed:', response);
    return response;
  } catch (error) {
    console.error('[API] Health check failed:', error.message);
    throw new Error(`Health check failed: ${error.message}`);
  }
}

/**
 * Test API connectivity
 * @returns {Promise<boolean>} True if API is accessible
 */
export async function testConnection() {
  try {
    await checkHealth();
    return true;
  } catch (error) {
    console.warn('[API] Connection test failed:', error.message);
    return false;
  }
}

// Export configuration for debugging
export const API_CONFIG = {
  baseUrl: API_BASE_URL,
  endpoint: API_ENDPOINT,
  timeout: REQUEST_TIMEOUT,
  version: API_VERSION,
};