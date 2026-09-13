import React, { useState } from 'react';
import { Volume2, Square, Loader2, Bot, User, CheckCircle2, AlertCircle, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { FormattedAnswer } from './formatAnswer';
import { synthesizeSpeech, playAudioDataUrl } from './voice';

export function ChatbotMessage({ message, voiceEnabled }) {
    const isUser = message.role === 'user';
    const isBot = message.role === 'assistant' || message.role === 'bot';

    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isSpeechLoading, setIsSpeechLoading] = useState(false);
    const [audioElement, setAudioElement] = useState(null);
    const [showSources, setShowSources] = useState(false);

    const handleSpeak = async () => {
        if (isSpeaking && audioElement) {
            audioElement.pause();
            audioElement.currentTime = 0;
            setIsSpeaking(false);
            return;
        }

        setIsSpeechLoading(true);
        try {
            const dataUrl = await synthesizeSpeech(message.content);
            const audio = playAudioDataUrl(dataUrl);
            setAudioElement(audio);
            setIsSpeaking(true);

            audio.onended = () => {
                setIsSpeaking(false);
            };
            audio.onerror = () => {
                setIsSpeaking(false);
            };
        } catch (err) {
            console.error('Speech playback failed:', err);
            setIsSpeaking(false);
        } finally {
            setIsSpeechLoading(false);
        }
    };

    return (
        <div
            style={{
                display: 'flex',
                flexDirection: isUser ? 'row-reverse' : 'row',
                gap: '0.75rem',
                alignItems: 'flex-start',
                width: '100%',
                marginBottom: '1rem',
            }}
        >
            {/* Avatar */}
            <div
                style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: '50%',
                    background: isUser ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    flexShrink: 0,
                    boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
                }}
            >
                {isUser ? <User size={18} /> : <Bot size={18} />}
            </div>

            {/* Bubble Content */}
            <div
                style={{
                    maxWidth: '82%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                }}
            >
                <div
                    style={{
                        padding: '0.875rem 1.15rem',
                        borderRadius: isUser ? '1.15rem 1.15rem 0.25rem 1.15rem' : '1.15rem 1.15rem 1.15rem 0.25rem',
                        background: isUser ? 'var(--accent-primary, #6366f1)' : 'var(--bg-secondary)',
                        color: isUser ? '#ffffff' : 'var(--text-primary)',
                        border: isUser ? 'none' : '1px solid var(--border-color)',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                    }}
                >
                    {message.loading ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                            <Loader2 size={16} className="spin" />
                            <span style={{ fontSize: '0.875rem' }}>Thinking...</span>
                        </div>
                    ) : message.error ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#ef4444' }}>
                            <AlertCircle size={16} />
                            <span>{message.content}</span>
                        </div>
                    ) : isUser ? (
                        <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.925rem', lineHeight: '1.5' }}>
                            {message.content}
                        </div>
                    ) : (
                        <div>
                            <FormattedAnswer text={message.content} />
                        </div>
                    )}
                </div>

                {/* Footer Metadata & Actions for Bot Responses */}
                {isBot && !message.loading && !message.error && (
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '0.5rem',
                            marginTop: '0.5rem',
                            paddingLeft: '0.25rem',
                        }}
                    >
                        {/* Listen Button (Sarvam TTS) */}
                        {voiceEnabled && (
                            <button
                                onClick={handleSpeak}
                                disabled={isSpeechLoading}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.35rem',
                                    padding: '0.3rem 0.65rem',
                                    borderRadius: '999px',
                                    fontSize: '0.75rem',
                                    fontWeight: '500',
                                    background: isSpeaking ? 'rgba(99, 102, 241, 0.2)' : 'var(--bg-tertiary)',
                                    color: isSpeaking ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                    border: '1px solid var(--border-color)',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s',
                                }}
                            >
                                {isSpeechLoading ? (
                                    <Loader2 size={13} className="spin" />
                                ) : isSpeaking ? (
                                    <Square size={12} fill="currentColor" />
                                ) : (
                                    <Volume2 size={13} />
                                )}
                                <span>{isSpeaking ? 'Stop' : 'Listen'}</span>
                            </button>
                        )}

                        {/* Confidence Badge */}
                        {message.confidence && (
                            <span
                                style={{
                                    fontSize: '0.72rem',
                                    fontWeight: '500',
                                    padding: '0.25rem 0.6rem',
                                    borderRadius: '999px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    background: message.confidence === 'high' ? 'rgba(34, 197, 94, 0.12)' : 'rgba(234, 179, 8, 0.12)',
                                    color: message.confidence === 'high' ? '#22c55e' : '#eab308',
                                    border: `1px solid ${message.confidence === 'high' ? 'rgba(34, 197, 94, 0.25)' : 'rgba(234, 179, 8, 0.25)'}`,
                                }}
                            >
                                <CheckCircle2 size={11} />
                                <span style={{ textTransform: 'capitalize' }}>{message.confidence} confidence</span>
                            </span>
                        )}

                        {/* Category Tag */}
                        {message.category && (
                            <span
                                style={{
                                    fontSize: '0.72rem',
                                    padding: '0.25rem 0.55rem',
                                    borderRadius: '999px',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-secondary)',
                                    border: '1px solid var(--border-color)',
                                }}
                            >
                                {message.category}
                            </span>
                        )}

                        {/* Sources Toggle */}
                        {message.sources && message.sources.length > 0 && (
                            <button
                                onClick={() => setShowSources(!showSources)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    padding: '0.25rem 0.6rem',
                                    borderRadius: '999px',
                                    fontSize: '0.72rem',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-secondary)',
                                    border: '1px solid var(--border-color)',
                                    cursor: 'pointer',
                                }}
                            >
                                <FileText size={11} />
                                <span>Sources ({message.sources.length})</span>
                                {showSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            </button>
                        )}
                    </div>
                )}

                {/* Sources List Dropdown */}
                {showSources && message.sources && (
                    <div
                        style={{
                            marginTop: '0.5rem',
                            padding: '0.65rem 0.85rem',
                            borderRadius: '0.5rem',
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-color)',
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            width: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.35rem',
                        }}
                    >
                        <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '2px' }}>
                            Referenced FAQ Excerpts:
                        </div>
                        {message.sources.map((s, idx) => (
                            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <span style={{ color: 'var(--accent-primary)' }}>•</span>
                                <span>{s.question || s.id}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
