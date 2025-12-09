import React from 'react';
import { Settings, FileText } from 'lucide-react';

const Sidebar = ({ isOpen }) => {
    return (
        <aside style={{
            width: isOpen ? '280px' : '0',
            opacity: isOpen ? 1 : 0,
            visibility: isOpen ? 'visible' : 'hidden',
            backgroundColor: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            padding: isOpen ? '1rem' : '0',
            flexShrink: 0,
            transition: 'all 0.3s ease-in-out',
            overflow: 'hidden'
        }}>
            {/* Header */}
            <div style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '1rem',
                paddingLeft: '0.5rem'
            }}>
                Spoken Tutorial Generator
            </div>

            {/* Info Card */}
            <div style={{
                padding: '1rem',
                background: 'var(--bg-tertiary)',
                borderRadius: '0.5rem',
                marginBottom: '1rem'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginBottom: '0.5rem',
                    color: 'var(--accent-primary)'
                }}>
                    <FileText size={16} />
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>How to use</span>
                </div>
                <ol style={{
                    margin: 0,
                    paddingLeft: '1.25rem',
                    color: 'var(--text-secondary)',
                    fontSize: '0.8rem',
                    lineHeight: 1.6
                }}>
                    <li>Upload your outline (.md, .docx, .txt)</li>
                    <li>Generate script from outline</li>
                    <li>Review and download PDF</li>
                </ol>
            </div>

            {/* Spacer */}
            <div style={{ flex: 1 }} />

            {/* Footer */}
            <div style={{
                borderTop: '1px solid var(--border-color)',
                paddingTop: '0.75rem',
                marginTop: '0.75rem',
                display: 'flex',
                gap: '0.5rem'
            }}>
                <button
                    style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.4rem',
                        padding: '0.5rem',
                        background: 'transparent',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.4rem',
                        color: 'var(--text-secondary)',
                        fontSize: '0.75rem',
                        cursor: 'pointer'
                    }}
                >
                    <Settings size={14} />
                    Settings
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
