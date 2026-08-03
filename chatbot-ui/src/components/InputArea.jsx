import React, { useRef, useState } from 'react';
import { Upload, FileJson, Send, Sparkles, FileText, Mic, Video, X, Check, File, BookOpen, FileAudio, Layers, ListMusic, Clock } from 'lucide-react';
import { NoiseBackgroundButton } from './ui/noise-background-button';

// How the narration audio is produced.
// - combined: one continuous file, synthesized with as few seams as possible
// - stitched: one file per slide, joined into a full narration — keeps the
//   individual files so a slide that reads inconsistently can be redone alone
// - rowwise: one file per slide, left separate
const VOICE_MODES = [
    {
        id: 'combined',
        label: 'Combined',
        icon: FileAudio,
        hint: '📢 One audio file for the entire script',
    },
    {
        id: 'stitched',
        label: 'Per-slide + Join',
        icon: ListMusic,
        hint: '🔗 One file per slide, plus the slides joined into full audio',
    },
    {
        id: 'rowwise',
        label: 'Row-wise',
        icon: Layers,
        hint: '🎵 Separate audio file for each row',
    },
];

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
    const isVoice = uploadType === 'voice';
    const isTimedScript = uploadType === 'timed_script';
    const isWiki = uploadType === 'wiki';

    // Voice mode state - 'combined' or 'rowwise'
    const [voiceMode, setVoiceMode] = useState('combined');
    const [speaker, setSpeaker] = useState('ishita');
    const [pace, setPace] = useState(0.9);
 
    // Get the appropriate icon based on upload type
    const getIcon = () => {
        if (isScript) return <FileJson size={24} />;
        if (isTimedScript) return <Clock size={24} />;
        if (isVoice) return <Mic size={24} />;
        if (isWiki) return <BookOpen size={24} />;
        return <File size={24} />;
    };
 
    // Wrap onConfirm to include voiceMode, speaker, and pace for voice uploads
    const handleConfirm = () => {
        if (isVoice) {
            onConfirm({ voiceMode, speaker, pace });
        } else {
            onConfirm();
        }
    };

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '1rem',
            padding: '1.25rem',
            boxShadow: 'var(--shadow-lg)',
            animation: 'slideUp 0.3s ease-out',
            width: '100%',
            maxWidth: '450px',
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
                    {getIcon()}
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

            {/* Voice Mode Selector - Only for voice uploads */}
            {isVoice && (
                <div style={{
                    display: 'flex',
                    gap: '0.5rem',
                    marginBottom: '1rem',
                    padding: '0.5rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '0.75rem',
                }}>
                    {VOICE_MODES.map(({ id, label, icon: Icon }) => (
                        <button
                            key={id}
                            onClick={() => setVoiceMode(id)}
                            style={{
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.4rem',
                                padding: '0.6rem 0.5rem',
                                borderRadius: '0.5rem',
                                border: 'none',
                                background: voiceMode === id ? 'var(--accent-primary)' : 'transparent',
                                color: voiceMode === id ? 'white' : 'var(--text-secondary)',
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                            }}
                        >
                            <Icon size={16} />
                            {label}
                        </button>
                    ))}
                </div>
            )}
            {isVoice && (
                <div style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    marginBottom: '0.75rem',
                    textAlign: 'center',
                }}>
                    {VOICE_MODES.find((m) => m.id === voiceMode)?.hint}
                </div>
            )}

            {/* Voice Actor and Speed controls */}
            {isVoice && (
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    marginBottom: '1rem',
                    textAlign: 'left'
                }}>
                    {/* Voice Actor selection */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Voice Actor</label>
                        <select
                            value={speaker}
                            onChange={(e) => setSpeaker(e.target.value)}
                            style={{
                                padding: '0.55rem 0.75rem',
                                borderRadius: '0.5rem',
                                border: '1px solid var(--border-color)',
                                background: 'var(--bg-secondary)',
                                color: 'var(--text-primary)',
                                fontSize: '0.8rem',
                                cursor: 'pointer',
                                outline: 'none',
                                width: '100%'
                            }}
                        >
                            <option value="ishita">Ishita (Female - Dynamic & Entertaining)</option>
                            <option value="kavya">Kavya (Female - Clear & Engaging)</option>
                            <option value="neha">Neha (Female - Conversational)</option>
                            <option value="shreya">Shreya (Female - Warm)</option>
                            <option value="aditya">Aditya (Male - Energetic)</option>
                            <option value="shubh">Shubh (Male - Professional)</option>
                            <option value="manan">Manan (Male - Conversational)</option>
                        </select>
                    </div>

                    {/* Pace / Speed range slider */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Speaking Speed (Pace)</label>
                            <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', fontWeight: 600 }}>{pace}x</span>
                        </div>
                        <input
                            type="range"
                            min="0.5"
                            max="2.0"
                            step="0.05"
                            value={pace}
                            onChange={(e) => setPace(parseFloat(e.target.value))}
                            style={{
                                width: '100%',
                                accentColor: 'var(--accent-primary)',
                                cursor: 'pointer',
                                height: '6px',
                                borderRadius: '3px',
                                background: 'var(--border-color)',
                                outline: 'none'
                            }}
                        />
                    </div>
                </div>
            )}

            {/* Timed Script Description */}
            {isTimedScript && (
                <div style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '0.75rem',
                    marginBottom: '1rem',
                }}>
                    <div style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        fontWeight: 500,
                        marginBottom: '0.35rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}>
                        <Clock size={14} style={{ color: 'var(--accent-primary)' }} />
                        Generate Timed Script
                    </div>
                    <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.4,
                    }}>
                        Uses AI (Whisper) to transcribe your audio and generate sentence-level timestamps.
                        Results can be downloaded as a DOCX file.
                    </div>
                </div>
            )}

            {/* Wiki Conversion Description */}
            {isWiki && (
                <div style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '0.75rem',
                    marginBottom: '1rem',
                }}>
                    <div style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        fontWeight: 500,
                        marginBottom: '0.35rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}>
                        <BookOpen size={14} style={{ color: 'var(--accent-primary)' }} />
                        MediaWiki Conversion
                    </div>
                    <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.4,
                    }}>
                        Converts your DOCX script to MediaWiki format. Ideal for uploading tutorials to the Spoken Tutorial Wiki.
                    </div>
                </div>
            )}

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
                    onClick={handleConfirm}
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
                    {isTimedScript ? 'Generate Timed Script' : isWiki ? 'Convert to Wiki' : 'Confirm Upload'}
                </button>
            </div>
        </div>
    );
};

const InputArea = ({
    mode = 'create',
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
    const scriptToWikiRef = useRef(null);
    const voiceInputRef = useRef(null);
    const [textValue, setTextValue] = useState('');


    // Stage script for wiki conversion
    const handleScriptToWikiSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && setStagedFile) {
            // Validate file type - only DOCX for wiki conversion
            const filename = file.name.toLowerCase();
            if (!filename.endsWith('.docx')) {
                alert('Please upload a .docx file for MediaWiki conversion');
                e.target.value = '';
                return;
            }

            setStagedFile({ file, type: 'wiki' });
            e.target.value = '';
        }
    };

    // Stage voice file for voice generation
    const handleVoiceSelect = (e) => {
        const file = e.target.files[0];
        if (file && !disabled && setStagedFile) {
            // Validate file type
            const filename = file.name.toLowerCase();
            const validExtensions = ['.json', '.docx', '.odt'];
            const isValid = validExtensions.some(ext => filename.endsWith(ext));

            if (!isValid) {
                alert('Please upload a .json, .docx, or .odt file');
                e.target.value = '';
                return;
            }

            setStagedFile({ file, type: 'voice' });
            e.target.value = '';
        }
    };

    // Confirm upload - use shared handler (pass through options from FilePreviewCard)
    const handleConfirmUpload = (options) => {
        if (onConfirmStagedFile) {
            onConfirmStagedFile(options);
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
    if (mode === 'create' && isWelcome) {
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
                    ref={scriptToWikiRef}
                    type="file"
                    accept=".docx"
                    onChange={handleScriptToWikiSelect}
                    disabled={disabled}
                    style={{ display: 'none' }}
                />
                <input
                    ref={voiceInputRef}
                    type="file"
                    accept=".json,.docx,.odt"
                    onChange={handleVoiceSelect}
                    disabled={disabled}
                    style={{ display: 'none' }}
                />

                {/* Staging is now handled by the overlay at component root */}

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
                            <h1 className="welcome-heading" style={{
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
                            <div className="welcome-input-box" style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '1rem 1.25rem',
                                background: 'var(--bg-secondary)',
                                borderRadius: '1.5rem',
                                border: '1px solid var(--border-color)',
                                boxShadow: 'var(--shadow-sm)',
                            }}>
                                <span className="welcome-disclaimer" style={{
                                    flex: 1,
                                    color: 'var(--text-secondary)',
                                    fontSize: '0.95rem',
                                }}>
                                    AI generated content may have mistakes, please cross check.
                                </span>
                                <div style={{
                                    display: 'flex',
                                    gap: '0.5rem',
                                    marginLeft: '1rem',
                                }}>
                                    {/* <button
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
                                    </button> */}
                                </div>
                            </div>
                        </div>

                        {/* Quick action pills */}
                        <div className="action-pills-container" style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '0.75rem',
                            justifyContent: 'center',
                        }}>
                            <style>{`
                                @media (max-width: 768px) {
                                    .welcome-heading {
                                        font-size: 1.5rem !important;
                                    }
                                    .welcome-disclaimer {
                                        font-size: 0.85rem !important;
                                    }
                                    .action-pills-container {
                                        flex-direction: column !important;
                                        align-items: stretch !important;
                                        width: 100% !important;
                                        max-width: 300px !important;
                                        margin: 0 auto !important;
                                    }
                                    .action-pill {
                                        width: 100% !important;
                                        justify-content: center !important;
                                    }
                                }
                            `}</style>

                            <NoiseBackgroundButton
                                className="action-pill"
                                gradient="blue"
                                onClick={() => scriptToWikiRef.current?.click()}
                                disabled={disabled}
                            >
                                <BookOpen size={16} />
                                Script to Wiki
                            </NoiseBackgroundButton>



                            <NoiseBackgroundButton
                                className="action-pill"
                                gradient="orange"
                                onClick={() => voiceInputRef.current?.click()}
                                disabled={disabled}
                            >
                                <Mic size={16} />
                                Generate Voice
                            </NoiseBackgroundButton>

                            <NoiseBackgroundButton
                                className="action-pill"
                                gradient="muted"
                                disabled={true}
                                title="Coming soon"
                            >
                                <FileText size={16} />
                                Create Slides
                            </NoiseBackgroundButton>
                        </div>
                    </>
                )}

                {/* Staging Overlay - Centered modal for file preview (also needed on welcome screen) */}
                {stagedFile && (
                    <div
                        style={{
                            position: 'fixed',
                            inset: 0,
                            background: 'rgba(0, 0, 0, 0.6)',
                            backdropFilter: 'blur(4px)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 100,
                            padding: '1rem',
                        }}
                        onClick={(e) => {
                            // Close on backdrop click
                            if (e.target === e.currentTarget) {
                                handleCancelUpload();
                            }
                        }}
                    >
                        <FilePreviewCard
                            file={stagedFile.file}
                            uploadType={stagedFile.type}
                            onConfirm={handleConfirmUpload}
                            onCancel={handleCancelUpload}
                            disabled={false}
                        />
                    </div>
                )}
            </div>
        );
    }

    // Regular input area (for when messages exist)
    return (
        <div style={{
            padding: '0.5rem',
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
                    <>
                        {/* Staging is now handled by the overlay at component root */}
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
                    </>
                ) : (
                    <>
                        {/* Staging is now handled by the overlay at component root */}

                        {/* No redundant buttons - use sidebar or welcome screen for uploads */}
                        {!stagedFile && (
                            <div style={{
                                textAlign: 'center',
                                fontSize: '0.8rem',
                                color: 'var(--text-secondary)',
                                padding: '0.5rem',
                            }}>
                                AI may make mistakes, please cross check.
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Staging Overlay - Centered modal for file preview */}
            {stagedFile && (
                <div
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0, 0, 0, 0.6)',
                        backdropFilter: 'blur(4px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 100,
                        padding: '1rem',
                    }}
                    onClick={(e) => {
                        // Close on backdrop click
                        if (e.target === e.currentTarget) {
                            handleCancelUpload();
                        }
                    }}
                >
                    <FilePreviewCard
                        file={stagedFile.file}
                        uploadType={stagedFile.type}
                        onConfirm={handleConfirmUpload}
                        onCancel={handleCancelUpload}
                        disabled={false}
                    />
                </div>
            )}
        </div>
    );
};

export default InputArea;
