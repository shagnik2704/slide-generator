import React from 'react';
import { Link } from 'react-router-dom';
import { UploadCloud, MessageSquare, ArrowRight } from 'lucide-react';

const HomePage = () => {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-sans)',
      transition: 'background-color 0.3s ease, color 0.3s ease',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        marginBottom: '3rem',
        animation: 'fadeIn 0.5s ease-out',
      }}>
        <img
          src="/favicon.png"
          alt="EduPyramids"
          style={{ 
            height: '48px',
            filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))',
          }}
        />
        <div style={{
          fontWeight: 600,
          fontSize: '1.5rem',
          fontFamily: 'var(--font-sans)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem'
        }}>
          <span style={{ color: 'var(--accent-secondary)' }}>Spoken</span>
          <span style={{ color: 'var(--accent-primary)' }}>Tutorial Generator</span>
        </div>
      </div>

      {/* Main Content */}
      <div style={{
        maxWidth: '900px',
        width: '100%',
        textAlign: 'center',
        animation: 'fadeIn 0.6s ease-out 0.1s backwards',
      }}>
        <h1 style={{
          fontSize: 'clamp(2rem, 5vw, 2.75rem)',
          fontWeight: 700,
          marginBottom: '1rem',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-sans)',
          letterSpacing: '-0.02em',
        }}>
          Welcome!
        </h1>
        <p style={{
          fontSize: '1.125rem',
          color: 'var(--text-secondary)',
          marginBottom: '3rem',
          lineHeight: '1.7',
          maxWidth: '600px',
          margin: '0 auto 3rem',
        }}>
          Create professional Spoken Tutorial content with AI-powered tools.
          Choose a mode to get started.
        </p>

        {/* Navigation Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
          {/* Upload Mode Card */}
          <Link
            to="/upload"
            className="home-card"
            style={{
              background: 'var(--bg-secondary)',
              border: '2px solid var(--border-color)',
              borderRadius: '1rem',
              padding: '2.5rem 2rem',
              textDecoration: 'none',
              color: 'var(--text-primary)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1.25rem',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer',
              position: 'relative',
              overflow: 'hidden',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent-primary)';
              e.currentTarget.style.boxShadow = 'var(--shadow-lg), var(--shadow-glow)';
              e.currentTarget.style.transform = 'translateY(-6px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{
              width: '72px',
              height: '72px',
              borderRadius: '50%',
              background: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              boxShadow: 'var(--shadow-md)',
              transition: 'transform 0.3s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.1) rotate(5deg)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1) rotate(0deg)';
            }}
            >
              <UploadCloud size={36} strokeWidth={2} />
            </div>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              margin: 0,
              fontFamily: 'var(--font-sans)',
              color: 'var(--text-primary)',
            }}>
              Upload Mode
            </h2>
            <p style={{
              fontSize: '0.95rem',
              color: 'var(--text-secondary)',
              margin: 0,
              lineHeight: '1.6',
              textAlign: 'center',
            }}>
              Upload your content to generate scripts, slides, audio, and generate compliance reports.
              Requires authentication.
            </p>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--accent-primary)',
              fontWeight: 600,
              fontSize: '0.95rem',
              marginTop: '0.5rem',
              transition: 'gap 0.3s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.gap = '0.75rem';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.gap = '0.5rem';
            }}
            >
              Get Started <ArrowRight size={18} />
            </div>
          </Link>

          {/* Outline Chat Card */}
          <Link
            to="/outline-chat"
            className="home-card"
            style={{
              background: 'var(--bg-secondary)',
              border: '2px solid var(--border-color)',
              borderRadius: '1rem',
              padding: '2.5rem 2rem',
              textDecoration: 'none',
              color: 'var(--text-primary)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1.25rem',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer',
              position: 'relative',
              overflow: 'hidden',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent-secondary)';
              e.currentTarget.style.boxShadow = 'var(--shadow-lg), var(--shadow-glow)';
              e.currentTarget.style.transform = 'translateY(-6px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{
              width: '72px',
              height: '72px',
              borderRadius: '50%',
              background: 'var(--accent-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              boxShadow: 'var(--shadow-md)',
              transition: 'transform 0.3s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.1) rotate(-5deg)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1) rotate(0deg)';
            }}
            >
              <MessageSquare size={36} strokeWidth={2} />
            </div>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              margin: 0,
              fontFamily: 'var(--font-sans)',
              color: 'var(--text-primary)',
            }}>
              Outline Chat
            </h2>
            <p style={{
              fontSize: '0.95rem',
              color: 'var(--text-secondary)',
              margin: 0,
              lineHeight: '1.6',
              textAlign: 'center',
            }}>
              Create course outlines interactively with our AI assistant.
              No authentication required.
            </p>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--accent-secondary)',
              fontWeight: 600,
              fontSize: '0.95rem',
              marginTop: '0.5rem',
              transition: 'gap 0.3s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.gap = '0.75rem';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.gap = '0.5rem';
            }}
            >
              Start Chatting <ArrowRight size={18} />
            </div>
          </Link>
        </div>

        {/* Footer Info */}
        <div style={{
          marginTop: '3rem',
          padding: '1.5rem 1.75rem',
          background: 'var(--bg-secondary)',
          borderRadius: '0.75rem',
          border: '1px solid var(--border-color)',
          boxShadow: 'var(--shadow-sm)',
          animation: 'fadeIn 0.7s ease-out 0.2s backwards',
        }}>
          <p style={{
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
            margin: 0,
            lineHeight: '1.7',
            fontFamily: 'var(--font-sans)',
          }}>
            <strong style={{ 
              color: 'var(--text-primary)',
              fontWeight: 600,
            }}>Note:</strong> Upload Mode requires authentication with an @edupyramids.org email address. 
            Outline Chat is available to everyone and doesn't require login.
          </p>
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .home-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.1),
            transparent
          );
          transition: left 0.5s ease;
        }
        
        .home-card:hover::before {
          left: 100%;
        }
        
        [data-theme="dark"] .home-card::before {
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.05),
            transparent
          );
        }
      `}</style>
    </div>
  );
};

export default HomePage;
