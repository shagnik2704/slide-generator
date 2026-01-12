/**
 * Centralized API service for the chatbot UI.
 * Eliminates duplicated fetch + error handling code across handlers.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'auth_token';

/**
 * Get JWT token from localStorage.
 * @returns {string|null} - JWT token or null
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Handle authentication errors (401/403).
 * @param {Response} response - Fetch response object
 * @param {string} endpoint - API endpoint to check if it's public
 * @throws {Error} - If authentication/authorization error occurs
 */
function handleAuthError(response, endpoint = '') {
    // Skip auth error handling for public outline_chat endpoints
    if (endpoint.includes('/outline_chat') || endpoint.includes('/general_chat')) {
        return; // Don't redirect for public endpoints
    }
    
    if (response.status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem(TOKEN_KEY);
        // Use replaceState to avoid adding to history
        if (window.location.pathname !== '/') {
            window.location.replace('/');
        }
    } else if (response.status === 403) {
        // Forbidden - show access denied message
        const error = new Error('Access denied: Invalid email domain');
        error.status = 403;
        error.name = 'AuthorizationError';
        throw error;
    }
}

/**
 * Base fetch wrapper with error handling and JWT token injection.
 * @param {string} endpoint - API endpoint (e.g., '/upload_script')
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Response>} - Raw response object
 * @throws {Error} - With error detail from API
 */
export async function apiRequest(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add Authorization header if token exists
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });

    // Handle auth errors before checking response.ok (skip for public endpoints)
    handleAuthError(response, endpoint);

    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch {
            errorData = { detail: `Request failed: ${endpoint}` };
        }
        
        const error = new Error(errorData.detail || errorData.message || `Request failed: ${endpoint}`);
        error.status = response.status;
        error.code = errorData.error_code;
        error.name = errorData.error_code || 'APIError';
        throw error;
    }

    return response;
}

/**
 * Fetch wrapper that returns parsed JSON.
 * @param {string} endpoint - API endpoint
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} - Parsed JSON response
 */
export async function apiJson(endpoint, options = {}) {
    const response = await apiRequest(endpoint, options);
    return response.json();
}

/**
 * Fetch wrapper for FormData uploads (no Content-Type header).
 * @param {string} endpoint - API endpoint
 * @param {FormData} formData - Form data to upload
 * @returns {Promise<any>} - Parsed JSON response
 */
export async function apiFormData(endpoint, formData) {
    const token = getToken();
    const headers = {};

    // Add Authorization header if token exists
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers,
        body: formData,
    });

    // Handle auth errors before checking response.ok (skip for public endpoints)
    handleAuthError(response, endpoint);

    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch {
            errorData = { detail: `Upload failed: ${endpoint}` };
        }
        
        const error = new Error(errorData.detail || errorData.message || `Upload failed: ${endpoint}`);
        error.status = response.status;
        error.code = errorData.error_code;
        error.name = errorData.error_code || 'APIError';
        throw error;
    }

    return response.json();
}

/**
 * Fetch wrapper that returns a Blob (for file downloads).
 * @param {string} endpoint - API endpoint
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Blob>} - Blob response
 */
export async function apiBlob(endpoint, options = {}) {
    const response = await apiRequest(endpoint, options);
    return response.blob();
}

export { API_URL };
