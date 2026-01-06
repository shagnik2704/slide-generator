import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const [showHi, setShowHi] = useState(false);
  const [welcomeText, setWelcomeText] = useState('');

  const fullWelcomeText = 'Welcome to ';
  const brandText = 'EduPyramids';

  useEffect(() => {
    // Show Hi! first
    const hiTimer = setTimeout(() => setShowHi(true), 300);

    // Start typewriter effect after Hi appears
    let charIndex = 0;
    const typewriterDelay = 1200; // Start after Hi appears

    const startTypewriter = setTimeout(() => {
      const typeInterval = setInterval(() => {
        if (charIndex < fullWelcomeText.length + brandText.length) {
          if (charIndex < fullWelcomeText.length) {
            setWelcomeText(fullWelcomeText.slice(0, charIndex + 1));
          } else {
            setWelcomeText(fullWelcomeText + brandText.slice(0, charIndex - fullWelcomeText.length + 1));
          }
          charIndex++;
        } else {
          clearInterval(typeInterval);
        }
      }, 60); // Speed of each character

      return () => clearInterval(typeInterval);
    }, typewriterDelay);

    return () => {
      clearTimeout(hiTimer);
      clearTimeout(startTypewriter);
    };
  }, []);

  // Split welcomeText into "Welcome to " and "EduPyramids" parts for coloring
  const displayedWelcome = welcomeText.slice(0, fullWelcomeText.length);
  const displayedBrand = welcomeText.slice(fullWelcomeText.length);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      padding: '2rem',
      fontFamily: 'var(--font-sans, system-ui, -apple-system, sans-serif)',
    }}>
      {/* Animated Greeting - Horizontal Row */}
      <div style={{
        marginBottom: '2rem',
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1rem',
        flexWrap: 'wrap',
      }}>
        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: '600',
          color: 'var(--accent-primary, #4285F4)',
          margin: 0,
          opacity: showHi ? 1 : 0,
          transform: showHi ? 'translateX(0)' : 'translateX(-20px)',
          transition: 'opacity 0.6s ease-out, transform 0.6s ease-out',
        }}>
          Hi! 👋
        </h1>
        <p style={{
          fontSize: '2.5rem',
          fontWeight: '500',
          color: 'var(--text-primary, #202124)',
          margin: 0,
          minWidth: '1ch',
        }}>
          {displayedWelcome}
          <span style={{ color: 'var(--accent-secondary, #34A853)' }}>{displayedBrand}</span>
          <span style={{
            display: welcomeText.length > 0 && welcomeText.length < fullWelcomeText.length + brandText.length ? 'inline-block' : 'none',
            width: '3px',
            height: '2.5rem',
            backgroundColor: 'var(--accent-primary, #4285F4)',
            marginLeft: '2px',
            animation: 'blink 0.8s infinite',
          }} />
        </p>
      </div>

      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>

      {/* Login Card - Always Visible */}
      <div style={{
        maxWidth: '420px',
        width: '100%',
        background: '#fff',
        borderRadius: '12px',
        padding: '3rem 2.5rem',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
        textAlign: 'center',
      }}>
        {/* Google Logo */}
        <div style={{ marginBottom: '2rem' }}>
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            style={{ margin: '0 auto' }}
          >
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
        </div>

        <h2 style={{
          fontSize: '1.5rem',
          marginBottom: '0.5rem',
          fontWeight: '400',
          color: '#202124',
          letterSpacing: '0',
        }}>
          Sign In
        </h2>
        <p style={{
          fontSize: '0.875rem',
          marginBottom: '2rem',
          color: '#5f6368',
          lineHeight: '1.5',
        }}>
          Continue to Slide Generator
        </p>

        <button
          onClick={login}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem',
            width: '100%',
            padding: '0.75rem 1.5rem',
            fontSize: '0.875rem',
            fontWeight: '500',
            color: '#3c4043',
            backgroundColor: '#fff',
            border: '1px solid #dadce0',
            borderRadius: '4px',
            cursor: 'pointer',
            transition: 'all 0.2s',
            boxShadow: '0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15)',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.boxShadow = '0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15)';
            e.currentTarget.style.backgroundColor = '#f8f9fa';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.boxShadow = '0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15)';
            e.currentTarget.style.backgroundColor = '#fff';
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          <span>Sign in with Google</span>
        </button>

        <div style={{
          marginTop: '2rem',
          padding: '1rem',
          background: '#f8f9fa',
          borderRadius: '4px',
          border: '1px solid #e8eaed',
        }}>
          <p style={{
            fontSize: '0.75rem',
            color: '#5f6368',
            margin: 0,
            lineHeight: '1.5',
          }}>
            <strong style={{ color: '#202124' }}>Access restricted:</strong> Only @edupyramids.org email addresses are allowed.
          </p>
        </div>

        {/* Footer */}
        <div style={{
          marginTop: '2rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e8eaed',
        }}>
          <p style={{
            fontSize: '0.75rem',
            color: '#5f6368',
            margin: 0,
          }}>
            brought to you by EduPyramids Educational Services Private Limited,SINE,IIT Bombay
          </p>
        </div>
      </div>
    </div>
  );
}
