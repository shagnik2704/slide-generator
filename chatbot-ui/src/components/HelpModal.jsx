import React, { useEffect } from 'react';
import { X, HelpCircle, Video, ExternalLink } from 'lucide-react';

const HelpModal = ({ isOpen, onClose }) => {
    // Close on Escape key
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape') onClose();
        };
        if (isOpen) {
            document.addEventListener('keydown', handleEscape);
            document.body.style.overflow = 'hidden';
        }
        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.body.style.overflow = 'unset';
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const modalOverlayStyle = {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(4px)',
    };

    const modalContentStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '16px',
        border: '1px solid var(--border-primary)',
        width: '90%',
        maxWidth: '420px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    };

    const headerStyle = {
        padding: '1.25rem 1.5rem',
        borderBottom: '1px solid var(--border-primary)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    };

    const bodyStyle = {
        padding: '1.5rem',
    };

    const footerStyle = {
        padding: '1rem 1.5rem',
        borderTop: '1px solid var(--border-primary)',
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '0.75rem',
    };

    const buttonStyle = (isPrimary) => ({
        padding: '0.75rem 1.5rem',
        borderRadius: '10px',
        fontWeight: 600,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: isPrimary ? 'var(--accent-primary)' : 'transparent',
        color: isPrimary ? 'white' : 'var(--text-secondary)',
        border: isPrimary ? 'none' : '1px solid var(--border-primary)',
        textDecoration: 'none',
        transition: 'all 0.2s ease',
    });

    return (
        <div style={modalOverlayStyle} onClick={onClose}>
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={headerStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <HelpCircle size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                            Need Help?
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.5rem',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div style={bodyStyle}>
                    <p style={{
                        color: 'var(--text-secondary)',
                        fontSize: '0.95rem',
                        lineHeight: 1.6,
                        margin: 0
                    }}>
                        Watch our tutorial videos to get started quickly and learn how to make the most of all features.
                    </p>
                </div>

                {/* Footer */}
                <div style={footerStyle}>
                    <button
                        onClick={onClose}
                        style={buttonStyle(false)}
                    >
                        Cancel
                    </button>
                    <a
                        href="https://drive.google.com/drive/folders/1XBGWAC4QBWIIbLODmcc114haXez0ApxJ?usp=drive_link"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={buttonStyle(true)}
                        onClick={onClose}
                    >
                        <Video size={18} />
                        Watch Tutorials
                        <ExternalLink size={14} />
                    </a>
                </div>
            </div>
        </div>
    );
};

export default HelpModal;
