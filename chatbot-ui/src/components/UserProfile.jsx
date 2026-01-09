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
          padding: compact ? '0.375rem' : '0.5rem 0.75rem',
          background: isDropdownOpen ? 'var(--bg-tertiary)' : 'transparent',
          border: '1px solid var(--border-color)',
          borderRadius: '50%',
          cursor: 'pointer',
          width: compact ? 'auto' : '100%',
          transition: 'all 0.2s ease',
          color: 'var(--text-primary)',
        }}
        onMouseEnter={(e) => {
          if (!isDropdownOpen) {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isDropdownOpen) {
            e.currentTarget.style.background = 'transparent';
          }
        }}
      >
        {/* Avatar */}
        <div
          style={{
            width: compact ? '36px' : '32px',
            height: compact ? '36px' : '32px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #4285f4 0%, #34a853 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: compact ? '0.875rem' : '0.75rem',
            fontWeight: '600',
            flexShrink: 0,
          }}
        >
          {getInitials(user.name)}
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

      {/* Dropdown Menu */}
      {isDropdownOpen && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: compact ? 'auto' : 0,
            right: compact ? 0 : 'auto',
            marginTop: '0.5rem',
            minWidth: compact ? '280px' : 'auto',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '0.5rem',
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
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: '600',
                }}
              >
                {getInitials(user.name)}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    color: 'var(--text-primary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {user.name || 'User'}
                </div>
                <div
                  style={{
                    fontSize: '0.75rem',
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

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              width: '100%',
              padding: '0.75rem',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.875rem',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      )}
    </div>
  );
}
