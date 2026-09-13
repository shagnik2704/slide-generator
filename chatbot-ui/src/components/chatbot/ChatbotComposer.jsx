import React, { useState, useRef, useCallback } from 'react';
import { Mic, Send, Loader2 } from 'lucide-react';
import { useVoiceRecorder } from './useVoiceRecorder';

export function ChatbotComposer({ onSend, disabled, voiceEnabled }) {
    const [input, setInput] = useState('');
    const [voiceError, setVoiceError] = useState(null);
    const textareaRef = useRef(null);
    const inputRef = useRef(input);
    inputRef.current = input;

    const resize = useCallback(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
    }, []);

    const submit = () => {
        const trimmed = input.trim();
        if (!trimmed || disabled) return;
        onSend(trimmed);
        setInput('');
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleVoiceTextUpdate = useCallback(
        (text) => {
            setVoiceError(null);
            setInput(text.slice(0, 2000));
            resize();
        },
        [resize]
    );

    const getCurrentText = useCallback(() => inputRef.current, []);

    const { isRecording, isProcessing, toggleRecording } = useVoiceRecorder({
        onTextUpdate: handleVoiceTextUpdate,
        getCurrentText,
        onError: setVoiceError,
    });

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
        }
    };

    const handleMicClick = () => {
        if (!voiceEnabled) {
            setVoiceError('Voice input is not configured. (Missing SARVAM_API_KEY)');
            return;
        }
        toggleRecording();
    };

    return (
        <div style={{ width: '100%', maxWidth: '820px', margin: '0 auto', padding: '0 1rem' }}>
            <div
                style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '1rem',
                    border: isRecording ? '1.5px solid #ef4444' : '1px solid var(--border-color)',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)',
                    padding: '0.65rem 0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem',
                    transition: 'border-color 0.2s',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
                    {/* Microphone Button */}
                    <button
                        type="button"
                        onClick={handleMicClick}
                        disabled={disabled || isProcessing}
                        title={
                            isRecording
                                ? 'Recording... click to stop'
                                : isProcessing
                                ? 'Transcribing speech...'
                                : 'Speak your question (Sarvam AI)'
                        }
                        style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            border: 'none',
                            background: isRecording
                                ? '#ef4444'
                                : isProcessing
                                ? 'var(--bg-tertiary)'
                                : 'var(--bg-tertiary)',
                            color: isRecording ? '#ffffff' : 'var(--text-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            flexShrink: 0,
                        }}
                    >
                        {isProcessing ? (
                            <Loader2 size={18} className="spin" />
                        ) : (
                            <Mic size={18} />
                        )}
                    </button>

                    {/* Text Area */}
                    <textarea
                        ref={textareaRef}
                        rows={1}
                        value={input}
                        disabled={disabled}
                        onChange={(e) => {
                            setInput(e.target.value);
                            setVoiceError(null);
                            resize();
                        }}
                        onKeyDown={handleKeyDown}
                        placeholder={
                            isRecording
                                ? 'Listening… speak your question now'
                                : isProcessing
                                ? 'Transcribing speech with Sarvam AI…'
                                : 'Ask a question about Spoken Tutorial (Master Batch, Tests, Certificates)...'
                        }
                        style={{
                            flex: 1,
                            background: 'transparent',
                            border: 'none',
                            outline: 'none',
                            resize: 'none',
                            color: 'var(--text-primary)',
                            fontSize: '0.925rem',
                            lineHeight: '1.5',
                            padding: '0.4rem 0.2rem',
                            maxHeight: '140px',
                        }}
                    />

                    {/* Send Button */}
                    <button
                        type="button"
                        onClick={submit}
                        disabled={disabled || isProcessing || !input.trim()}
                        style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            border: 'none',
                            background: input.trim() && !disabled ? 'var(--accent-primary, #6366f1)' : 'var(--bg-tertiary)',
                            color: input.trim() && !disabled ? '#ffffff' : 'var(--text-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: input.trim() && !disabled ? 'pointer' : 'default',
                            transition: 'all 0.15s',
                            flexShrink: 0,
                        }}
                    >
                        <Send size={16} />
                    </button>
                </div>

                {/* Voice Error Display */}
                {voiceError && (
                    <div style={{ fontSize: '0.75rem', color: '#ef4444', paddingLeft: '0.5rem' }}>
                        {voiceError}
                    </div>
                )}
            </div>

            {/* Hint Under Composer */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.35rem 0.75rem 0.75rem 0.75rem',
                    fontSize: '0.72rem',
                    color: 'var(--text-secondary)',
                }}
            >
                <span>
                    {isRecording
                        ? 'Listening… stops automatically on pause or tap mic to finish'
                        : isProcessing
                        ? 'Transcribing your audio…'
                        : 'Press Enter to send · Shift+Enter for new line'}
                </span>
                <span>Grounded with official Spoken Tutorial FAQs</span>
            </div>
        </div>
    );
}
