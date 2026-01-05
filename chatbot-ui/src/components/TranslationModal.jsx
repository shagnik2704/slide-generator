import React, { useState, useEffect } from 'react';
import { X, Languages, Check, Loader2, FileText, Download } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * TranslationModal - Modal for selecting languages and translating scripts
 */
export default function TranslationModal({
    isOpen,
    onClose,
    file,
    onTranslate
}) {
    const [languages, setLanguages] = useState({});
    const [selectedLanguages, setSelectedLanguages] = useState([]);
    const [translateVisualCues, setTranslateVisualCues] = useState(true);
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
            const response = await fetch(`${API_URL}/translation/languages`);
            if (response.ok) {
                const data = await response.json();
                setLanguages(data);
            }
        } catch (err) {
            console.error('Failed to fetch languages:', err);
            setError('Failed to load languages');
        }
    };

    const toggleLanguage = (code) => {
        setSelectedLanguages(prev =>
            prev.includes(code)
                ? prev.filter(l => l !== code)
                : [...prev, code]
        );
    };

    const handleTranslate = async () => {
        if (selectedLanguages.length === 0) return;

        // Close modal immediately
        onClose();

        // Start translation in background (don't await here)
        onTranslate({
            file,
            languages: selectedLanguages,
            translateVisualCues
        }).catch(err => {
            console.error('Translation failed:', err);
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

    const checkboxStyle = (isSelected) => ({
        width: '20px',
        height: '20px',
        borderRadius: '6px',
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
        border: 'none',
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
                        <Languages size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                            Translate Script
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
                    {/* File info */}
                    {file && (
                        <div style={{
                            padding: '1rem',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '10px',
                            marginBottom: '1.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                        }}>
                            <FileText size={20} style={{ color: 'var(--accent-primary)' }} />
                            <div>
                                <div style={{ fontWeight: 500 }}>{file.name}</div>
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                    {(file.size / 1024).toFixed(1)} KB
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Language selection */}
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '0.75rem',
                            fontWeight: 500,
                            color: 'var(--text-primary)'
                        }}>
                            Select languages to translate:
                        </label>

                        <div style={languageGridStyle}>
                            {Object.entries(languages).map(([code, info]) => (
                                <div
                                    key={code}
                                    style={languageCardStyle(selectedLanguages.includes(code))}
                                    onClick={() => toggleLanguage(code)}
                                >
                                    <div style={checkboxStyle(selectedLanguages.includes(code))}>
                                        {selectedLanguages.includes(code) && (
                                            <Check size={14} style={{ color: 'white' }} />
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

                    {/* Options */}
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            padding: '1rem',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '10px',
                            cursor: 'pointer',
                        }}
                        onClick={() => setTranslateVisualCues(!translateVisualCues)}
                    >
                        <div style={checkboxStyle(translateVisualCues)}>
                            {translateVisualCues && (
                                <Check size={14} style={{ color: 'white' }} />
                            )}
                        </div>
                        <div>
                            <div style={{ fontWeight: 500 }}>Translate visual cues</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                Also translate the visual cue descriptions
                            </div>
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
                        onClick={handleTranslate}
                        style={buttonStyle(true, selectedLanguages.length === 0 || isLoading)}
                        disabled={selectedLanguages.length === 0 || isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
                                Translating...
                            </>
                        ) : (
                            <>
                                <Languages size={18} />
                                Translate to {selectedLanguages.length} language{selectedLanguages.length !== 1 ? 's' : ''}
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
