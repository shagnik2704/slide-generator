import React, { useEffect } from 'react';
import { X, MessageSquare, ExternalLink } from 'lucide-react';

const FeedbackModal = ({ isOpen, onClose }) => {
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
                        <MessageSquare size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                            Send Feedback
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
                        Your feedback helps us improve! Report bugs, suggest features, or share your experience with us.
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
                        href="https://forms.gle/gZQChrYSiDn2aemr8"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={buttonStyle(true)}
                        onClick={onClose}
                    >
                        <MessageSquare size={18} />
                        Open Feedback Form
                        <ExternalLink size={14} />
                    </a>
                </div>
            </div>
        </div>
    );
};

export default FeedbackModal;
