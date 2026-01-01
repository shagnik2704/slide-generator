/**
 * Centralized API service for the chatbot UI.
 * Eliminates duplicated fetch + error handling code across handlers.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Base fetch wrapper with error handling.
 * @param {string} endpoint - API endpoint (e.g., '/upload_script')
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Response>} - Raw response object
 * @throws {Error} - With error detail from API
 */
export async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed: ${endpoint}`);
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
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${endpoint}`);
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
