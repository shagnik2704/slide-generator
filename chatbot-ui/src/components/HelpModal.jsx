import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
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
        background: 'rgba(15, 23, 42, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        backdropFilter: 'blur(8px)',
        animation: 'modalFadeIn 0.25s ease-out',
    };

    const modalContentStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '24px',
        border: '1px solid var(--border-color)',
        width: '90%',
        maxWidth: '440px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'var(--shadow-lg), var(--shadow-glow), 0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        animation: 'modalScaleUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
    };

    const headerStyle = {
        padding: '1.5rem 1.75rem 1.25rem 1.75rem',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    };

    const bodyStyle = {
        padding: '1.75rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1.25rem',
        textAlign: 'center',
    };

    const footerStyle = {
        padding: '1.25rem 1.75rem 1.5rem 1.75rem',
        borderTop: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '0.75rem',
    };

    const buttonStyle = {
        padding: '0.75rem 1.5rem',
        borderRadius: '12px',
        fontWeight: 600,
        fontSize: '0.95rem',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        textDecoration: 'none',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        border: 'none',
    };

    return createPortal(
        <div style={modalOverlayStyle} onClick={onClose}>
            <style>{`
                @keyframes modalFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes modalScaleUp {
                    from { transform: scale(0.95) translateY(20px); opacity: 0; }
                    to { transform: scale(1) translateY(0); opacity: 1; }
                }
                .modal-btn-primary {
                    background: var(--accent-primary) !important;
                    color: white !important;
                    box-shadow: 0 4px 14px rgba(45, 62, 142, 0.25);
                }
                .modal-btn-primary:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(45, 62, 142, 0.35), var(--shadow-glow);
                    opacity: 0.95;
                }
                .modal-btn-primary:active {
                    transform: translateY(0);
                }
                .modal-btn-secondary {
                    background: transparent !important;
                    color: var(--text-secondary) !important;
                    border: 1px solid var(--border-color) !important;
                }
                .modal-btn-secondary:hover {
                    background: var(--bg-tertiary) !important;
                    color: var(--text-primary) !important;
                    border-color: var(--text-secondary) !important;
                }
                .modal-btn-close {
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    padding: 0.5rem;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justifyContent: center;
                    transition: all 0.2s ease;
                }
                .modal-btn-close:hover {
                    background: var(--bg-tertiary);
                    color: var(--text-primary);
                    transform: rotate(90deg);
                }
                .gradient-illustration-container {
                    background: linear-gradient(135deg, rgba(45, 62, 142, 0.08) 0%, rgba(242, 101, 34, 0.08) 100%);
                    border: 1px solid var(--border-color);
                    border-radius: 20px;
                    width: 72px;
                    height: 72px;
                    display: flex;
                    align-items: center;
                    justifyContent: center;
                    margin-bottom: 0.25rem;
                    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.8);
                }
                [data-theme="dark"] .gradient-illustration-container {
                    background: linear-gradient(135deg, rgba(255, 130, 70, 0.15) 0%, rgba(107, 125, 200, 0.15) 100%);
                    box-shadow: none;
                }
            `}</style>
            
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={headerStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <HelpCircle size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            Need Help?
                        </h2>
                    </div>
                    <button onClick={onClose} className="modal-btn-close">
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div style={bodyStyle}>
                    <div className="gradient-illustration-container">
                        <Video size={36} style={{ color: 'var(--accent-primary)' }} />
                    </div>
                    <p style={{
                        color: 'var(--text-secondary)',
                        fontSize: '0.975rem',
                        lineHeight: 1.6,
                        margin: 0,
                        fontWeight: 500,
                    }}>
                        Watch our curated tutorial videos to get started quickly and learn how to master all features of EduPyramids Slide Generator.
                    </p>
                </div>

                {/* Footer */}
                <div style={footerStyle}>
                    <button
                        onClick={onClose}
                        style={buttonStyle}
                        className="modal-btn-secondary"
                    >
                        Cancel
                    </button>
                    <a
                        href="https://drive.google.com/drive/folders/1XBGWAC4QBWIIbLODmcc114haXez0ApxJ?usp=drive_link"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={buttonStyle}
                        className="modal-btn-primary"
                        onClick={onClose}
                    >
                        <Video size={18} />
                        Watch Tutorials
                        <ExternalLink size={14} style={{ marginLeft: '-2px' }} />
                    </a>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default HelpModal;
