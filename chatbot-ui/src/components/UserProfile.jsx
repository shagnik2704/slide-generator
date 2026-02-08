import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LogOut, User, ChevronDown } from 'lucide-react';

export default function UserProfile({ compact = false }) {
  const { user, logout } = useAuth();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  if (!user) return null;

  // Get user initials for avatar
  const getInitials = (name) => {
    if (!name) return user.email[0].toUpperCase();
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const handleLogout = async () => {
    await logout();
    setIsDropdownOpen(false);
  };

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: compact ? '0.5rem' : '0.75rem',
          padding: compact ? '0.25rem' : '0.5rem',
          background: isDropdownOpen ? 'var(--bg-tertiary)' : 'transparent',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          width: compact ? 'auto' : '100%',
          transition: 'all 0.2s ease',
          color: 'var(--text-primary)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--bg-tertiary)';
        }}
        onMouseLeave={(e) => {
          if (!isDropdownOpen) {
            e.currentTarget.style.background = 'transparent';
          }
        }}
      >
        {/* Avatar - Shows Google picture if available, otherwise initials */}
        <div
          style={{
            width: compact ? '36px' : '40px',
            height: compact ? '36px' : '40px',
            borderRadius: '50%',
            background: user.picture ? 'transparent' : 'linear-gradient(135deg, #34a853 0%, #2d8a47 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: compact ? '0.875rem' : '0.75rem',
            fontWeight: '600',
            flexShrink: 0,
            overflow: 'hidden',
          }}
        >
          {user.picture ? (
            <img
              src={user.picture}
              alt={user.name || 'User'}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              referrerPolicy="no-referrer"
            />
          ) : (
            getInitials(user.name)
          )}
        </div>
        {!compact && (
          <>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                flex: 1,
                minWidth: 0,
              }}
            >
              <span
                style={{
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: 'var(--text-primary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  width: '100%',
                }}
              >
                {user.name || user.email.split('@')[0]}
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  width: '100%',
                }}
              >
                {user.email}
              </span>
            </div>
            <ChevronDown
              size={16}
              style={{
                transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease',
                color: 'var(--text-secondary)',
                flexShrink: 0,
              }}
            />
          </>
        )}
      </button>

      {/* Dropdown Menu - Opens UP in sidebar (dropup), DOWN in header (dropdown) */}
      {isDropdownOpen && (
        <div
          style={{
            position: 'absolute',
            // Dropup in sidebar, dropdown in header
            ...(compact
              ? { top: '100%', marginTop: '0.5rem' }  // Header: opens down
              : { bottom: '100%', marginBottom: '0.5rem' }  // Sidebar: opens up
            ),
            left: compact ? 'auto' : 0,
            right: compact ? 0 : 'auto',
            width: compact ? '260px' : '100%',
            maxWidth: compact ? 'calc(100vw - 2rem)' : 'none',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '0.75rem',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden',
            zIndex: 1000,
          }}
        >
          {/* Profile Info */}
          <div
            style={{
              padding: '0.75rem',
              borderBottom: '1px solid var(--border-color)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.5rem',
              }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  background: user.picture ? 'transparent' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  overflow: 'hidden',
                }}
              >
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt={user.name || 'User'}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  getInitials(user.name)
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    marginBottom: '2px',
                  }}
                >
                  {user.name || 'User'}
                </div>
                <div
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {user.email}
                </div>
              </div>
            </div>
          </div>

          {/* Logout */}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              width: '100%',
              padding: '0.75rem 1rem',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <LogOut size={18} />
            <span style={{ fontWeight: 500 }}>Log out</span>
          </button>
        </div>
      )}
    </div>
  );
}
