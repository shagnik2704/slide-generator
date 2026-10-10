import { describe, it, expect } from 'vitest';
import { sanitizeErrorMessage } from './errorSanitizer';

describe('errorSanitizer', () => {
  describe('sanitizeErrorMessage', () => {
    it('returns default fallback when error is null or undefined', () => {
      expect(sanitizeErrorMessage(null)).toBe('An unexpected error occurred.');
      expect(sanitizeErrorMessage(undefined, 'Custom fallback')).toBe('Custom fallback');
    });

    it('redacts filesystem paths from error messages', () => {
      const raw = 'File not found at /Users/shagniksarkar/secret/path/to/script.py';
      const sanitized = sanitizeErrorMessage(raw);
      expect(sanitized).not.toContain('/Users/shagniksarkar/secret');
      expect(sanitized).toContain('[internal]');
    });

    it('redacts database and SQL internals', () => {
      const raw = 'psycopg2.OperationalError: SELECT * FROM users WHERE id = 1';
      const sanitized = sanitizeErrorMessage(raw);
      expect(sanitized).not.toContain('psycopg2');
      expect(sanitized).not.toContain('SELECT');
      expect(sanitized).not.toContain('FROM users');
    });

    it('redacts Python tracebacks', () => {
      const raw = 'Traceback (most recent call last):\n  File "server.py", line 40\nZeroDivisionError: division by zero';
      const sanitized = sanitizeErrorMessage(raw);
      expect(sanitized).not.toContain('Traceback (most recent call last)');
      expect(sanitized).not.toContain('ZeroDivisionError');
    });

    it('redacts sensitive API keys and tokens', () => {
      const raw = 'Authorization failed using sk-1234567890abcdef1234567890abcdef';
      const sanitized = sanitizeErrorMessage(raw);
      expect(sanitized).not.toContain('sk-1234567890abcdef1234567890abcdef');
      expect(sanitized).toContain('[internal]');
    });

    it('handles network failure errors gracefully', () => {
      const fetchError = new TypeError('Failed to fetch');
      expect(sanitizeErrorMessage(fetchError)).toBe(
        'Unable to reach the server. Please check your internet connection.'
      );

      const netError = new Error('NetworkError when attempting to fetch resource.');
      expect(sanitizeErrorMessage(netError)).toBe(
        'Unable to reach the server. Please check your internet connection.'
      );
    });

    it('maps HTTP status codes to friendly messages when no specific text exists', () => {
      expect(sanitizeErrorMessage({ status: 401 })).toBe(
        'Your session has expired. Please sign in again.'
      );
      expect(sanitizeErrorMessage({ status: 403 })).toBe(
        'Access denied: You do not have permission to perform this action.'
      );
      expect(sanitizeErrorMessage({ status: 404 })).toBe(
        'The requested resource could not be found.'
      );
      expect(sanitizeErrorMessage({ status: 429 })).toBe(
        'You are making requests too quickly. Please wait a moment and try again.'
      );
      expect(sanitizeErrorMessage({ status: 500 })).toBe(
        'An unexpected server error occurred. Our team has been notified.'
      );
    });

    it('formats FastAPI/Pydantic 422 validation array objects into readable text', () => {
      const pydanticError = {
        status: 422,
        data: {
          detail: [
            {
              loc: ['body', 'foss_name'],
              msg: 'Field required',
              type: 'missing',
            },
            {
              loc: ['body', 'slide_number'],
              msg: 'Input should be greater than 0',
              type: 'greater_than',
            },
          ],
        },
      };

      const result = sanitizeErrorMessage(pydanticError);
      expect(result).toContain('Foss name: Field required');
      expect(result).toContain('Slide number: Input should be greater than 0');
    });
  });
});
