/**
 * Error Sanitizer utility for the frontend application.
 *
 * Prevents sensitive internal backend details (tracebacks, file paths, SQL errors,
 * credentials) from leaking to end users, formats FastAPI/Pydantic validation errors
 * cleanly instead of displaying `[object Object]`, and maps HTTP error status codes
 * to helpful, user-friendly messages.
 */

// Regex patterns for sensitive internal data that should never be shown in UI
const SENSITIVE_PATTERNS = [
  /(\/(?:app|Users|home|var|tmp|etc)[\w\-./\\]*)/gi,                                  // File system paths
  /(?:psycopg2|sqlalchemy|asyncpg|OperationalError|IntegrityError|SELECT|INSERT|UPDATE|DELETE|FROM\s+\w+)/gi, // Database & SQL
  /(?:Traceback\s+\(most\s+recent\s+call\s+last\):[\s\S]*)/gi,                         // Python tracebacks
  /(?:sk-[a-zA-Z0-9_-]{20,}|Bearer\s+[\w\-._~+/]+=*|AIza[0-9A-Za-z-_]{35})/gi,       // API keys & JWTs
  /(?:https?:\/\/(?:backend|redis|postgres|localhost):\d+)/gi,                         // Internal endpoints
];

/**
 * Strips technical internals from a raw error string.
 * @param {string} text - Raw error message
 * @returns {string} - Cleaned message
 */
function redactTechnicalDetails(text) {
  if (typeof text !== 'string') return '';
  let cleaned = text;
  for (const pattern of SENSITIVE_PATTERNS) {
    cleaned = cleaned.replace(pattern, '[internal]');
  }
  return cleaned.trim();
}

/**
 * Formats FastAPI/Pydantic validation error lists into readable text.
 * @param {Array<any>} details - Pydantic error list
 * @returns {string|null} - Formatted string or null
 */
function formatPydanticErrors(details) {
  if (!Array.isArray(details) || details.length === 0) return null;

  const messages = details
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return typeof item === 'string' ? item : null;
      }
      // If loc is present, extract the field name
      const loc = Array.isArray(item.loc) ? item.loc : [];
      // Ignore generic 'body', 'query', etc. if another segment exists
      const field = loc.filter((segment) => segment !== 'body' && segment !== 'query').pop();
      const rawMsg = item.msg || item.message || 'Invalid value';
      
      if (field) {
        // Format snake_case to Title Case (e.g., 'tutorial_name' -> 'Tutorial name')
        const formattedField = String(field)
          .replace(/_/g, ' ')
          .replace(/^\w/, (c) => c.toUpperCase());
        return `${formattedField}: ${rawMsg}`;
      }
      return rawMsg;
    })
    .filter(Boolean);

  if (messages.length === 0) return null;
  return messages.join('. ');
}

/**
 * Friendly fallbacks for common HTTP status codes.
 */
const STATUS_FALLBACKS = {
  400: 'Invalid request. Please verify your inputs and try again.',
  401: 'Your session has expired. Please sign in again.',
  403: 'Access denied: You do not have permission to perform this action.',
  404: 'The requested resource could not be found.',
  409: 'The operation could not be completed due to a conflict with current state.',
  413: 'The uploaded file is too large. Please select a smaller file.',
  415: 'The uploaded file format is not supported.',
  422: 'Invalid data submitted. Please check the required fields.',
  429: 'You are making requests too quickly. Please wait a moment and try again.',
  500: 'An unexpected server error occurred. Our team has been notified.',
  502: 'The server is temporarily unavailable. Please try again shortly.',
  503: 'The service is undergoing maintenance. Please try again in a few moments.',
  504: 'The request took too long to complete. Please try again.',
};

/**
 * Primary error sanitization function.
 *
 * @param {any} error - The caught error object, API error response, or string
 * @param {string} [contextFallback] - Optional contextual fallback message
 * @returns {string} - Clean, safe, user-friendly error message
 */
export function sanitizeErrorMessage(error, contextFallback = 'An unexpected error occurred.') {
  if (!error) return contextFallback;

  // 1. Direct string input
  if (typeof error === 'string') {
    const trimmed = error.trim();
    if (!trimmed) return contextFallback;
    const redacted = redactTechnicalDetails(trimmed);
    if (redacted.replace(/\[internal\]/g, '').trim().length < 4) {
      return contextFallback;
    }
    return redacted;
  }

  // 2. Browser network failures
  if (
    (error.name === 'TypeError' && error.message === 'Failed to fetch') ||
    error.message?.includes('NetworkError') ||
    error.message?.includes('net::ERR_')
  ) {
    return 'Unable to reach the server. Please check your internet connection.';
  }

  // 3. Status-based handling
  const status = error.status || error.statusCode;

  // 4. FastAPI / Pydantic 422 validation array check
  const rawData = error.rawData || error.data;
  const detail = rawData?.detail || error.detail;

  if (Array.isArray(detail)) {
    const formatted = formatPydanticErrors(detail);
    if (formatted) return formatted;
  }

  // 5. Server-side 5xx errors: NEVER leak technical backend internals to users
  if (status && status >= 500) {
    return STATUS_FALLBACKS[status] || STATUS_FALLBACKS[500];
  }

  // 6. Inspect detail/message string if available
  let candidate = '';
  if (typeof detail === 'string' && detail.trim()) {
    candidate = detail.trim();
  } else if (typeof error.message === 'string' && error.message.trim()) {
    candidate = error.message.trim();
  }

  if (candidate) {
    // Avoid repeating meaningless technical error wrappers
    if (candidate.startsWith('[object Object]')) {
      return (status && STATUS_FALLBACKS[status]) || contextFallback;
    }

    const redacted = redactTechnicalDetails(candidate);
    // If redacting scrubbed out virtually the entire message, use status fallback
    if (redacted.replace(/\[internal\]/g, '').trim().length < 4) {
      return (status && STATUS_FALLBACKS[status]) || contextFallback;
    }
    return redacted;
  }

  // 7. Fallback to status mapping or provided context
  if (status && STATUS_FALLBACKS[status]) {
    return STATUS_FALLBACKS[status];
  }

  return contextFallback;
}

/**
 * Creates a sanitized Error object suitable for throwing from API clients.
 *
 * @param {any} errorData - Parsed JSON payload from error response
 * @param {number} status - HTTP status code
 * @param {string} endpoint - API endpoint for fallback context
 * @returns {Error} - Sanitized Error instance with status and code properties
 */
export function createSanitizedError(errorData, status, endpoint) {
  const fallback = `Request failed: ${endpoint}`;
  const cleanMessage = sanitizeErrorMessage(
    {
      status,
      detail: errorData?.detail,
      message: errorData?.message,
      rawData: errorData,
    },
    fallback
  );

  const error = new Error(cleanMessage);
  error.status = status;
  error.code = errorData?.error_code;
  error.name = errorData?.error_code || 'APIError';
  error.rawData = errorData;

  return error;
}
