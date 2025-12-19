import React, { useRef, useState } from 'react';
import { Upload, FileJson, Send } from 'lucide-react';

const InputArea = ({ mode = 'upload', onSendMessage, onUploadScript, onSendText, disabled }) => {
    const fileInputRef = useRef(null);
    const scriptInputRef = useRef(null);
    const [textValue, setTextValue] = useState('');

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled) {
            onSendMessage(file);
            e.target.value = '';
        }
    };

    const handleScriptSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && onUploadScript) {
            onUploadScript(file);
            e.target.value = '';
        }
    };

    const buttonStyle = (isDisabled) => ({
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        background: isDisabled
            ? 'var(--bg-tertiary)'
            : 'var(--accent-primary)',
        color: isDisabled ? 'var(--text-secondary)' : 'white',
        border: 'none',
        borderRadius: '0.75rem',
        padding: '0.85rem 1rem',
        fontSize: '0.9rem',
        fontWeight: 600,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        boxShadow: isDisabled ? 'none' : 'var(--shadow-md)',
        transition: 'all 0.3s ease',
        opacity: isDisabled ? 0.6 : 1,
    });

    const handleSendText = () => {
        const value = textValue.trim();
        if (!value || disabled || !onSendText) return;
        onSendText(value);
        setTextValue('');
    };

    const outlineMode = mode === 'outline_chat';

    return (
        <div style={{
            padding: '1.5rem',
            background: 'linear-gradient(to top, var(--bg-primary) 80%, transparent)',
            position: 'relative',
            zIndex: 10
        }}>
            <div style={{
                maxWidth: '800px',
                margin: '0 auto',
                position: 'relative'
            }}>
                {outlineMode ? (
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                        <textarea
                            value={textValue}
                            onChange={(e) => setTextValue(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendText();
                                }
                            }}
                            disabled={disabled}
                            placeholder="Describe your topic, goals, audience, or ask to refine the outline..."
                            style={{
                                flex: 1,
                                minHeight: '80px',
                                padding: '0.85rem 1rem',
                                borderRadius: '0.75rem',
                                border: '1px solid var(--border-color)',
                                background: 'var(--bg-secondary)',
                                color: 'var(--text-primary)',
                                fontSize: '0.95rem',
                                resize: 'vertical',
                                boxShadow: 'var(--shadow-sm)'
                            }}
                        />
                        <button
                            type="button"
                            onClick={handleSendText}
                            disabled={disabled || !textValue.trim()}
                            style={buttonStyle(disabled || !textValue.trim())}
                            onMouseEnter={(e) => {
                                if (!disabled && textValue.trim()) {
                                    e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (!disabled) {
                                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                }
                            }}
                        >
                            <Send size={20} />
                            Send
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Hidden file inputs */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".md,.docx,.txt,.odt"
                            onChange={handleFileSelect}
                            disabled={disabled}
                            style={{ display: 'none' }}
                        />
                        <input
                            ref={scriptInputRef}
                            type="file"
                            accept=".json"
                            onChange={handleScriptSelect}
                            disabled={disabled}
                            style={{ display: 'none' }}
                        />

                        {/* Button row */}
                        <div style={{ display: 'flex', gap: '0.75rem' }}>
                            {/* Upload Outline Button */}
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={disabled}
                                style={buttonStyle(disabled)}
                                onMouseEnter={(e) => {
                                    if (!disabled) {
                                        e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                        e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!disabled) {
                                        e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                    }
                                }}
                            >
                                <Upload size={20} />
                                Upload Outline
                            </button>

                            {/* Upload Script Button */}
                            <button
                                type="button"
                                onClick={() => scriptInputRef.current?.click()}
                                disabled={disabled}
                                style={buttonStyle(disabled)}
                                onMouseEnter={(e) => {
                                    if (!disabled) {
                                        e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                        e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!disabled) {
                                        e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                    }
                                }}
                            >
                                <FileJson size={20} />
                                Upload Script (.json)
                            </button>
                        </div>

                        <div style={{
                            textAlign: 'center',
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            marginTop: '0.75rem'
                        }}>
                            Upload outline to generate script, or upload existing script to skip to slides.
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default InputArea;
