import React from 'react';
import { MessageSquare, Plus, Settings, LogOut } from 'lucide-react';

const Sidebar = ({ isOpen }) => {
    return (
        <aside style={{
            width: isOpen ? '260px' : '0',
            opacity: isOpen ? 1 : 0,
            visibility: isOpen ? 'visible' : 'hidden',
            backgroundColor: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            padding: isOpen ? '1rem' : '0',
            flexShrink: 0,
            transition: 'all 0.3s ease-in-out',
            overflow: 'hidden',
            whiteSpace: 'nowrap'
        }}>
            <button className="btn-primary" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                width: '100%',
                justifyContent: 'center',
                marginBottom: '1.5rem'
            }}>
                <Plus size={18} />
                <span>New Chat</span>
            </button>

            <div style={{ flex: 1, overflowY: 'auto' }}>
                <div style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.5rem',
                    paddingLeft: '0.5rem'
                }}>
                    Recent
                </div>
                {/* Mock History Items */}
                {[1, 2, 3].map((i) => (
                    <button key={i} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        width: '100%',
                        padding: '0.75rem',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        borderRadius: '0.5rem',
                        textAlign: 'left',
                        transition: 'background 0.2s'
                    }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        <MessageSquare size={16} color="var(--text-secondary)" />
                        <span style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            fontSize: '0.9rem'
                        }}>
                            Previous Chat Session {i}
                        </span>
                    </button>
                ))}
            </div>

            <div style={{
                borderTop: '1px solid var(--border-color)',
                paddingTop: '1rem',
                marginTop: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                <button className="btn-icon" style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}>
                    <Settings size={18} />
                    <span>Settings</span>
                </button>
                <button className="btn-icon" style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}>
                    <LogOut size={18} />
                    <span>Log out</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
