import React, { useRef, useState } from 'react';
import { Upload, FileJson, Send, Sparkles, FileText, Mic, Video, X, Check, File, BookOpen } from 'lucide-react';

// Helper to format file size
const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

// Helper to get file extension
const getFileExtension = (filename) => {
    return filename.split('.').pop().toUpperCase();
};

// File Preview Card Component
const FilePreviewCard = ({ file, uploadType, onConfirm, onCancel, disabled }) => {
    const extension = getFileExtension(file.name);
    const isScript = uploadType === 'script';

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '1rem',
            padding: '1.25rem',
            marginBottom: '1rem',
            boxShadow: 'var(--shadow-md)',
            animation: 'slideUp 0.3s ease-out',
        }}>
            {/* File info row */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                marginBottom: '1rem',
            }}>
                {/* File icon */}
                <div style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '0.75rem',
                    background: 'var(--accent-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    flexShrink: 0,
                }}>
                    {isScript ? <FileJson size={24} /> : <File size={24} />}
                </div>

                {/* File details */}
                <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                    <div style={{
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        fontSize: '0.95rem',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        textAlign: 'left',
                    }}>
                        {file.name}
                    </div>
                    <div style={{
                        display: 'flex',
                        gap: '0.75rem',
                        marginTop: '0.25rem',
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)',
                    }}>
                        <span>{formatFileSize(file.size)}</span>
                        <span>•</span>
                        <span style={{
                            background: 'var(--bg-tertiary)',
                            padding: '0.1rem 0.5rem',
                            borderRadius: '0.25rem',
                            fontWeight: 500,
                        }}>
                            {extension}
                        </span>
                    </div>
                </div>
            </div>

            {/* Action buttons */}
            <div style={{
                display: 'flex',
                gap: '0.75rem',
            }}>
                <button
                    onClick={onCancel}
                    disabled={disabled}
                    style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        padding: '0.7rem 1rem',
                        borderRadius: '0.6rem',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                        fontSize: '0.85rem',
                        fontWeight: 500,
                        cursor: disabled ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                        opacity: disabled ? 0.5 : 1,
                    }}
                    onMouseEnter={(e) => {
                        if (!disabled) {
                            e.currentTarget.style.background = 'var(--bg-secondary)';
                            e.currentTarget.style.borderColor = 'var(--text-secondary)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.borderColor = 'var(--border-color)';
                    }}
                >
                    <X size={16} />
                    Cancel
                </button>
                <button
                    onClick={onConfirm}
                    disabled={disabled}
                    style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        padding: '0.7rem 1rem',
                        borderRadius: '0.6rem',
                        border: 'none',
                        background: disabled ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                        color: disabled ? 'var(--text-secondary)' : 'white',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        cursor: disabled ? 'not-allowed' : 'pointer',
                        boxShadow: disabled ? 'none' : 'var(--shadow-sm)',
                        transition: 'all 0.2s ease',
                        opacity: disabled ? 0.5 : 1,
                    }}
                    onMouseEnter={(e) => {
                        if (!disabled) {
                            e.currentTarget.style.transform = 'translateY(-1px)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                    }}
                >
                    <Check size={16} />
                    Confirm Upload
                </button>
            </div>
        </div>
    );
};

const InputArea = ({
    mode = 'upload',
    onSendMessage,
    onUploadScript,
    onSendText,
    onScriptToWiki,
    disabled,
    isWelcome = false,
    // Shared staging props (from useChatArea)
    stagedFile,
    setStagedFile,
    onConfirmStagedFile,
    onCancelStagedFile,
}) => {
    const fileInputRef = useRef(null);
    const scriptInputRef = useRef(null);
    const scriptToWikiRef = useRef(null);
    const [textValue, setTextValue] = useState('');

    // Stage file instead of uploading immediately
    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && setStagedFile) {
            setStagedFile({ file, type: 'outline' });
            e.target.value = '';
        }
    };

    // Stage script instead of uploading immediately
    const handleScriptSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && setStagedFile) {
            setStagedFile({ file, type: 'script' });
            e.target.value = '';
        }
    };

    // Stage script for wiki conversion
    const handleScriptToWikiSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && setStagedFile) {
            setStagedFile({ file, type: 'wiki' });
            e.target.value = '';
        }
    };

    // Confirm upload - use shared handler
    const handleConfirmUpload = () => {
        if (onConfirmStagedFile) {
            onConfirmStagedFile();
        }
    };

    // Cancel upload - use shared handler
    const handleCancelUpload = () => {
        if (onCancelStagedFile) {
            onCancelStagedFile();
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
                <input
                    ref={scriptToWikiRef}
                    type="file"
                    accept=".docx"
                    onChange={handleScriptToWikiSelect}
                    disabled={disabled}
                    style={{ display: 'none' }}
                />

                {/* Show staged file preview if a file is selected */}
                {stagedFile && (
                    <div style={{ width: '100%', maxWidth: '500px', marginBottom: '1.5rem' }}>
                        <FilePreviewCard
                            file={stagedFile.file}
                            uploadType={stagedFile.type}
                            onConfirm={handleConfirmUpload}
                            onCancel={handleCancelUpload}
                            disabled={disabled}
                        />
                    </div>
                )}

                {/* Welcome text - only show when no file is staged */}
                {!stagedFile && (
                    <>
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
                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                }}
                            >
                                <FileJson size={16} />
                                Check Script
                            </button>

                            <button
                                onClick={() => scriptToWikiRef.current?.click()}
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
                                <BookOpen size={16} />
                                Script to Wiki
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
                                <FileText size={16} />
                                Create Slides
                            </button>
                        </div>
                    </>
                )}
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

                        {/* Show staged file preview if a file is selected */}
                        {stagedFile ? (
                            <FilePreviewCard
                                file={stagedFile.file}
                                uploadType={stagedFile.type}
                                onConfirm={handleConfirmUpload}
                                onCancel={handleCancelUpload}
                                disabled={disabled}
                            />
                        ) : (
                            <>
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
                    </>
                )}
            </div>
        </div>
    );
};

export default InputArea;
