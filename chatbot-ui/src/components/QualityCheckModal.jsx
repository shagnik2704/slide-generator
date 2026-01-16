import React, { useState, useEffect } from 'react';
import { X, Languages, Check, Loader2, FileText, ShieldCheck } from 'lucide-react';
import { apiJson } from '../services/api';

/**
 * QualityCheckModal - Modal for selecting a single language for quality compliance check
 * Uses back-translation method to verify translation quality
 */
export default function QualityCheckModal({
    isOpen,
    onClose,
    file,
    jsonScript,
    onSubmit
}) {
    const [languages, setLanguages] = useState({});
    const [selectedLanguage, setSelectedLanguage] = useState('hi'); // Default to Hindi
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // Fetch supported languages on mount
    useEffect(() => {
        if (isOpen) {
            fetchLanguages();
        }
    }, [isOpen]);

    const fetchLanguages = async () => {
        try {
            const data = await apiJson('/translation/languages');
            setLanguages(data);
        } catch (err) {
            console.error('Failed to fetch languages:', err);
            setError('Failed to load languages');
        }
    };

    const handleSubmit = async () => {
        if (!selectedLanguage) return;

        // Close modal immediately
        onClose();

        // Start quality check in background
        onSubmit({
            file,
            jsonScript,
            languageCode: selectedLanguage
        }).catch(err => {
            console.error('Quality check failed:', err);
        });
    };

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
        maxWidth: '500px',
        maxHeight: '80vh',
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
        overflowY: 'auto',
        flex: 1,
    };

    const footerStyle = {
        padding: '1rem 1.5rem',
        borderTop: '1px solid var(--border-primary)',
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '0.75rem',
    };

    const languageGridStyle = {
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '0.75rem',
        marginBottom: '1.5rem',
    };

    const languageCardStyle = (isSelected) => ({
        padding: '1rem',
        borderRadius: '12px',
        border: `2px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-primary)'}`,
        background: isSelected ? 'rgba(99, 102, 241, 0.1)' : 'var(--bg-tertiary)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
    });

    // Radio button style instead of checkbox
    const radioStyle = (isSelected) => ({
        width: '20px',
        height: '20px',
        borderRadius: '50%', // Circle for radio button
        border: `2px solid ${isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)'}`,
        background: isSelected ? 'var(--accent-primary)' : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
    });

    const buttonStyle = (isPrimary, isDisabled) => ({
        padding: '0.75rem 1.5rem',
        borderRadius: '10px',
        fontWeight: 600,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: isPrimary
            ? (isDisabled ? 'var(--bg-tertiary)' : 'var(--accent-primary)')
            : 'transparent',
        color: isPrimary
            ? (isDisabled ? 'var(--text-secondary)' : 'white')
            : 'var(--text-secondary)',
        border: isPrimary ? 'none' : '1px solid var(--border-primary)',
        opacity: isDisabled ? 0.6 : 1,
    });

    return (
        <div style={modalOverlayStyle} onClick={onClose}>
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={headerStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <ShieldCheck size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                            Quality Compliance Check
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
                    {/* Info card */}
                    <div style={{
                        padding: '1rem',
                        background: 'var(--bg-tertiary)',
                        borderRadius: '10px',
                        marginBottom: '1.5rem',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.75rem',
                        borderLeft: '3px solid var(--accent-primary)',
                    }}>
                        <Languages size={20} style={{ color: 'var(--accent-primary)', flexShrink: 0, marginTop: '2px' }} />
                        <div>
                            <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>
                                Back-Translation Quality Check
                            </div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                This check translates your script to the selected language, then back to English.
                                By comparing the original with the back-translation, we can verify translation accuracy.
                            </div>
                        </div>
                    </div>

                    {/* Language selection */}
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '0.75rem',
                            fontWeight: 500,
                            color: 'var(--text-primary)'
                        }}>
                            Select a language for quality check:
                        </label>

                        <div style={languageGridStyle}>
                            {Object.entries(languages).map(([code, info]) => (
                                <div
                                    key={code}
                                    style={languageCardStyle(selectedLanguage === code)}
                                    onClick={() => setSelectedLanguage(code)}
                                >
                                    <div style={radioStyle(selectedLanguage === code)}>
                                        {selectedLanguage === code && (
                                            <div style={{
                                                width: '10px',
                                                height: '10px',
                                                borderRadius: '50%',
                                                background: 'white',
                                            }} />
                                        )}
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 500 }}>{info.name}</div>
                                        <div style={{
                                            fontSize: '1rem',
                                            color: 'var(--text-secondary)',
                                            fontFamily: 'system-ui'
                                        }}>
                                            {info.native}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Error message */}
                    {error && (
                        <div style={{
                            marginTop: '1rem',
                            padding: '0.75rem 1rem',
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderRadius: '8px',
                            color: '#ef4444',
                            fontSize: '0.9rem',
                        }}>
                            {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={footerStyle}>
                    <button
                        onClick={onClose}
                        style={buttonStyle(false, false)}
                        disabled={isLoading}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        style={buttonStyle(true, !selectedLanguage || isLoading)}
                        disabled={!selectedLanguage || isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
                                Checking...
                            </>
                        ) : (
                            <>
                                <ShieldCheck size={18} />
                                Run Quality Check ({languages[selectedLanguage]?.name || 'Hindi'})
                            </>
                        )}
                    </button>
                </div>

                {/* Inline CSS for spinner */}
                <style>{`
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        </div>
    );
}
