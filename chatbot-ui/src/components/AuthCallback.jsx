import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * Component to handle OAuth callback from backend.
 * The AuthContext already processes the token from URL params,
 * so this component just waits for authentication and redirects.
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, loading } = useAuth();
  const token = searchParams.get('token');

  useEffect(() => {
    // If we have a token in the URL, the AuthContext will process it
    // Once authenticated, redirect to upload page
    if (!loading && isAuthenticated) {
      navigate('/upload', { replace: true });
    } else if (!loading && !isAuthenticated && !token) {
      // No token and not authenticated, redirect to login
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, loading, navigate, token]);

  // Show loading while processing
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary, #f0f0ed)',
    }}>
      <div style={{
        textAlign: 'center',
        color: 'var(--text-primary, #2D3E8E)',
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid var(--border-color, #e0e4ed)',
          borderTop: '4px solid var(--accent-primary, #2D3E8E)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          margin: '0 auto 1rem',
        }}></div>
        <p>Completing authentication...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}
