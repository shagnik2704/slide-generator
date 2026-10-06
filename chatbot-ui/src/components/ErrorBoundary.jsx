import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { sanitizeErrorMessage } from '../utils/errorSanitizer';

/**
 * Top-level React Error Boundary.
 * Catches unhandled JavaScript exceptions in child component renders
 * and displays a user-friendly recovery screen instead of a blank white page.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log sanitized error context to console for debugging
    console.error('Unhandled UI rendering error:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      const isDev = Boolean(import.meta.env?.DEV);
      const safeMessage = sanitizeErrorMessage(
        this.state.error,
        'An unexpected interface error occurred.'
      );

      return (
        <div
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            padding: '2rem',
            backgroundColor: 'var(--bg-primary, #f0f0ed)',
            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            color: 'var(--text-primary, #1e293b)',
          }}
        >
          <div
            style={{
              maxWidth: '520px',
              width: '100%',
              backgroundColor: 'var(--bg-secondary, #ffffff)',
              padding: '2.5rem',
              borderRadius: '16px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
              border: '1px solid var(--border-color, #e2e8f0)',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: '#fee2e2',
                color: '#dc2626',
                marginBottom: '1.25rem',
              }}
            >
              <AlertTriangle size={32} />
            </div>

            <h1
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                marginBottom: '0.75rem',
                color: 'var(--text-primary, #1e293b)',
              }}
            >
              Something went wrong
            </h1>

            <p
              style={{
                fontSize: '0.95rem',
                color: 'var(--text-secondary, #64748b)',
                lineHeight: 1.6,
                marginBottom: '1.75rem',
              }}
            >
              {safeMessage}
            </p>

            <div
              style={{
                display: 'flex',
                gap: '0.75rem',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <button
                type="button"
                onClick={this.handleReload}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  backgroundColor: 'var(--accent-primary, #2D3E8E)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'opacity 0.2s',
                }}
              >
                <RefreshCw size={16} />
                Reload Page
              </button>

              <button
                type="button"
                onClick={this.handleHome}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  backgroundColor: 'var(--bg-tertiary, #f1f5f9)',
                  color: 'var(--text-primary, #334155)',
                  border: '1px solid var(--border-color, #cbd5e1)',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                }}
              >
                <Home size={16} />
                Return to Home
              </button>
            </div>

            {/* Development-only technical details toggle */}
            {isDev && this.state.error && (
              <div style={{ marginTop: '2rem', textAlign: 'left' }}>
                <button
                  type="button"
                  onClick={this.toggleDetails}
                  style={{
                    fontSize: '0.75rem',
                    color: '#64748b',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                    padding: 0,
                  }}
                >
                  {this.state.showDetails ? 'Hide developer details' : 'Show developer details (dev only)'}
                </button>

                {this.state.showDetails && (
                  <pre
                    style={{
                      marginTop: '0.75rem',
                      padding: '0.75rem',
                      backgroundColor: '#1e293b',
                      color: '#f8fafc',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      overflowX: 'auto',
                      maxHeight: '160px',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {this.state.error?.stack || this.state.error?.message}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
