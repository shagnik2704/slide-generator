import React, { useRef } from 'react';
import { Upload, FileJson } from 'lucide-react';

const InputArea = ({ onSendMessage, onUploadScript, disabled }) => {
    const fileInputRef = useRef(null);
    const scriptInputRef = useRef(null);

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
            : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                {/* Hidden file inputs */}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".md,.docx,.txt"
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
            </div>
        </div>
    );
};

export default InputArea;
