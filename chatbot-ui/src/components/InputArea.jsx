import React, { useRef, useState } from 'react';
import { Upload, FileJson, Send, Sparkles, FileText, Mic, Video } from 'lucide-react';

const InputArea = ({ mode = 'upload', onSendMessage, onUploadScript, onSendText, disabled, isWelcome = false }) => {
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

    const handleSendText = () => {
        const value = textValue.trim();
        if (!value || disabled || !onSendText) return;
        onSendText(value);
        setTextValue('');
    };

    const outlineMode = mode === 'outline_chat';

    // Pill button style (Gemini-inspired, enhanced)
    const pillButtonStyle = (isDisabled) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        padding: '0.75rem 1.5rem',
        borderRadius: '999px',
        border: '1px solid var(--border-color)',
        background: isDisabled ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
        color: isDisabled ? 'var(--text-secondary)' : 'var(--text-primary)',
        fontSize: '0.9rem',
        fontWeight: 500,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.25s ease',
        opacity: isDisabled ? 0.5 : 1,
        boxShadow: isDisabled ? 'none' : 'var(--shadow-sm)',
    });

    // Primary button style
    const primaryButtonStyle = (isDisabled) => ({
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        background: isDisabled ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
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

    // Welcome screen for upload mode (Gemini-inspired)
    if (mode === 'upload' && isWelcome) {
        return (
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem',
                textAlign: 'center',
            }}>
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
                    accept=".json,.docx,.odt"
                    onChange={handleScriptSelect}
                    disabled={disabled}
                    style={{ display: 'none' }}
                />

                {/* Welcome text */}
                <div style={{
                    marginBottom: '2rem',
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        marginBottom: '0.5rem',
                        color: 'var(--accent-secondary)',
                        fontSize: '0.95rem',
                        fontWeight: 500,
                    }}>
                        <Sparkles size={18} />
                        <span>Welcome</span>
                    </div>
                    <h1 style={{
                        fontSize: '2rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        margin: 0,
                        lineHeight: 1.3,
                    }}>
                        What would you like to create today?
                    </h1>
                </div>

                {/* Input box (styled like Gemini) */}
                <div style={{
                    width: '100%',
                    maxWidth: '600px',
                    marginBottom: '1.5rem',
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '1rem 1.25rem',
                        background: 'var(--bg-secondary)',
                        borderRadius: '1.5rem',
                        border: '1px solid var(--border-color)',
                        boxShadow: 'var(--shadow-sm)',
                    }}>
                        <span style={{
                            flex: 1,
                            color: 'var(--text-secondary)',
                            fontSize: '0.95rem',
                        }}>
                            Upload content to start generating a tutorial...
                        </span>
                        <div style={{
                            display: 'flex',
                            gap: '0.5rem',
                            marginLeft: '1rem',
                        }}>
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={disabled}
                                style={{
                                    padding: '0.5rem',
                                    borderRadius: '50%',
                                    border: 'none',
                                    background: 'var(--accent-primary)',
                                    color: 'white',
                                    cursor: disabled ? 'not-allowed' : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'all 0.2s ease',
                                }}
                                onMouseEnter={(e) => {
                                    if (!disabled) {
                                        e.currentTarget.style.transform = 'scale(1.1)';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'scale(1)';
                                }}
                            >
                                <Upload size={18} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Quick action pills */}
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                    justifyContent: 'center',
                }}>
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={disabled}
                        style={pillButtonStyle(disabled)}
                        onMouseEnter={(e) => {
                            if (!disabled) {
                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0) scale(1)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                        }}
                    >
                        <FileText size={16} />
                        Generate Script
                    </button>

                    <button
                        onClick={() => scriptInputRef.current?.click()}
                        disabled={disabled}
                        style={pillButtonStyle(disabled)}
                        onMouseEnter={(e) => {
                            if (!disabled) {
                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0) scale(1)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                        }}
                    >
                        <FileJson size={16} />
                        Check Script
                    </button>

                    <button
                        disabled={true}
                        style={pillButtonStyle(true)}
                        title="Coming soon"
                    >
                        <Mic size={16} />
                        Generate Voice
                    </button>

                    <button
                        disabled={true}
                        style={pillButtonStyle(true)}
                        title="Coming soon"
                    >
                        <Video size={16} />
                        Create Video
                    </button>
                </div>
            </div>
        );
    }

    // Regular input area (for when messages exist)
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
                            style={primaryButtonStyle(disabled || !textValue.trim())}
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
                            accept=".json,.docx,.odt"
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
                                style={primaryButtonStyle(disabled)}
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
                                Upload Content
                            </button>

                            {/* Upload Script Button */}
                            <button
                                type="button"
                                onClick={() => scriptInputRef.current?.click()}
                                disabled={disabled}
                                style={primaryButtonStyle(disabled)}
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
                                Upload Script
                            </button>
                        </div>

                        <div style={{
                            textAlign: 'center',
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            marginTop: '0.75rem'
                        }}>
                            Upload content to generate script, or upload existing script to skip to slides.
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default InputArea;
