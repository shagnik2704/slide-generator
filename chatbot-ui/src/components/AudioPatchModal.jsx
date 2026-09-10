import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, Play, Pause, Download, Volume2, Sparkles, Clock, Trash2, RotateCcw } from 'lucide-react';
import { apiJson } from '../services/api';

const API_URL = import.meta.env.VITE_API_URL || '';

const SPEAKERS = [
    { id: 'priya', name: 'Priya', badge: 'Tier 1 ★ Female', gender: 'female' },
    { id: 'ishita', name: 'Ishita', badge: 'Tier 1 Female', gender: 'female' },
    { id: 'mani', name: 'Mani', badge: 'Tier 1 ★ Male', gender: 'male' },
    { id: 'shubh', name: 'Shubh', badge: 'Tier 1 Male', gender: 'male' },
    { id: 'kavya', name: 'Kavya', badge: 'Standard Female', gender: 'female' },
];

const PACES = [
    { value: 0.80, label: '0.80x (Slow)' },
    { value: 0.85, label: '0.85x (Recommended)' },
    { value: 0.90, label: '0.90x (Standard)' },
    { value: 1.00, label: '1.00x (Normal)' },
];

const LANGUAGES = [
    { code: 'en-IN', name: 'English (India)' },
    { code: 'hi-IN', name: 'Hindi' },
    { code: 'ta-IN', name: 'Tamil' },
    { code: 'te-IN', name: 'Telugu' },
    { code: 'mr-IN', name: 'Marathi' },
    { code: 'bn-IN', name: 'Bengali' },
    { code: 'kn-IN', name: 'Kannada' },
    { code: 'gu-IN', name: 'Gujarati' },
    { code: 'ml-IN', name: 'Malayalam' },
    { code: 'pa-IN', name: 'Punjabi' },
    { code: 'od-IN', name: 'Odia' },
];

export default function AudioPatchModal({ isOpen, onClose }) {
    const [text, setText] = useState('');
    const [speaker, setSpeaker] = useState('priya');
    const [pace, setPace] = useState(0.85);
    const [language, setLanguage] = useState('en-IN');
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);

    // Current active result
    const [currentResult, setCurrentResult] = useState(null);

    // Session history of generated patches
    const [history, setHistory] = useState([]);

    // Player state for active result
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const activeAudioRef = useRef(null);

    // Close on Escape
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onClose();
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                if (text.trim() && !isGenerating) {
                    handleGenerate();
                }
            }
        };
        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'hidden';
        }
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'unset';
        };
    }, [isOpen, text, isGenerating, speaker, pace, language]);

    // Clean up audio when modal closes
    useEffect(() => {
        if (!isOpen && activeAudioRef.current) {
            activeAudioRef.current.pause();
            setIsPlaying(false);
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleGenerate = async () => {
        if (!text.trim()) return;

        setIsGenerating(true);
        setError(null);

        try {
            const data = await apiJson('/generate_voice_patch', {
                method: 'POST',
                body: JSON.stringify({
                    text: text.trim(),
                    speaker,
                    pace: parseFloat(pace),
                    language_code: language,
                }),
            });

            if (data.success) {
                setCurrentResult(data);
                setIsPlaying(false);
                setCurrentTime(0);

                // Add to history (newest first, max 6)
                setHistory((prev) => [
                    {
                        id: data.patch_id || Date.now(),
                        text: text.trim(),
                        speaker,
                        pace,
                        audio_url: data.audio_url,
                        duration_estimate: data.duration_estimate,
                        createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    },
                    ...prev.slice(0, 5),
                ]);
            } else {
                setError(data.error || 'Failed to generate audio patch');
            }
        } catch (err) {
            console.error('Patch generation failed:', err);
            setError(err.message || 'An error occurred during audio generation');
        } finally {
            setIsGenerating(false);
        }
    };

    const togglePlay = () => {
        if (!activeAudioRef.current) return;
        if (isPlaying) {
            activeAudioRef.current.pause();
            setIsPlaying(false);
        } else {
            activeAudioRef.current.play();
            setIsPlaying(true);
        }
    };

    const formatTime = (time) => {
        if (isNaN(time)) return '0:00';
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
    const charCount = text.length;

    const resolveAudioUrl = (url) => {
        if (!url) return '';
        if (url.startsWith('http')) return url;
        return `${API_URL}${url}`;
    };

    return createPortal(
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(15, 23, 42, 0.7)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                padding: '1rem',
                animation: 'patchModalFadeIn 0.2s ease-out',
            }}
            onClick={onClose}
        >
            <style>{`
                @keyframes patchModalFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes patchModalScale {
                    from { transform: scale(0.96) translateY(10px); opacity: 0; }
                    to { transform: scale(1) translateY(0); opacity: 1; }
                }
                .patch-input:focus {
                    outline: none;
                    border-color: var(--accent-primary) !important;
                    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
                }
                .patch-history-card:hover {
                    background: var(--bg-tertiary) !important;
                    border-color: var(--accent-primary) !important;
                }
            `}</style>

            <div
                style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '1.25rem',
                    border: '1px solid var(--border-color)',
                    width: '100%',
                    maxWidth: '680px',
                    maxHeight: '92vh',
                    display: 'flex',
                    flexDirection: 'column',
                    boxShadow: 'var(--shadow-lg), 0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                    animation: 'patchModalScale 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                    overflow: 'hidden',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '1.25rem 1.5rem',
                        borderBottom: '1px solid var(--border-color)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: 'var(--bg-secondary)',
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div
                            style={{
                                width: '38px',
                                height: '38px',
                                borderRadius: '10px',
                                background: 'linear-gradient(135deg, var(--accent-primary), #818cf8)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                            }}
                        >
                            <Sparkles size={20} />
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                                Audio Patch Generator
                            </h2>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                                Generate quick speech clips or test pronunciation without full scripts
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.4rem',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Modal Body */}
                <div style={{ padding: '1.25rem 1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Text Area */}
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                            <label style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                                Text or Sentence to Synthesize
                            </label>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                {wordCount} words · {charCount} chars
                            </span>
                        </div>
                        <textarea
                            className="patch-input"
                            rows={3}
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            placeholder="Enter the phrase or sentence that needs to be generated (e.g. 'In this tutorial, we will learn how to open salary.py on Desktop')..."
                            style={{
                                width: '100%',
                                padding: '0.85rem',
                                borderRadius: '0.75rem',
                                border: '1px solid var(--border-color)',
                                background: 'var(--bg-tertiary)',
                                color: 'var(--text-primary)',
                                fontSize: '0.95rem',
                                lineHeight: '1.5',
                                resize: 'vertical',
                                boxSizing: 'border-box',
                                fontFamily: 'inherit',
                                transition: 'all 0.2s ease',
                            }}
                        />
                    </div>

                    {/* Controls Grid */}
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                            gap: '0.75rem',
                        }}
                    >
                        {/* Voice Selector */}
                        <div>
                            <label style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>
                                Speaker Voice
                            </label>
                            <select
                                value={speaker}
                                onChange={(e) => setSpeaker(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem 0.75rem',
                                    borderRadius: '0.6rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.85rem',
                                    outline: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                {SPEAKERS.map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {s.name} ({s.badge})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Pace Selector */}
                        <div>
                            <label style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>
                                Speed / Pace
                            </label>
                            <select
                                value={pace}
                                onChange={(e) => setPace(parseFloat(e.target.value))}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem 0.75rem',
                                    borderRadius: '0.6rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.85rem',
                                    outline: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                {PACES.map((p) => (
                                    <option key={p.value} value={p.value}>
                                        {p.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Language Selector */}
                        <div>
                            <label style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>
                                Target Language
                            </label>
                            <select
                                value={language}
                                onChange={(e) => setLanguage(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.6rem 0.75rem',
                                    borderRadius: '0.6rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.85rem',
                                    outline: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                {LANGUAGES.map((l) => (
                                    <option key={l.code} value={l.code}>
                                        {l.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Action Bar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            Tip: Press <kbd style={{ padding: '2px 5px', borderRadius: '4px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}>Ctrl+Enter</kbd> to generate
                        </span>
                        <button
                            onClick={handleGenerate}
                            disabled={isGenerating || !text.trim()}
                            style={{
                                padding: '0.7rem 1.5rem',
                                borderRadius: '0.6rem',
                                border: 'none',
                                background: isGenerating || !text.trim() ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                                color: isGenerating || !text.trim() ? 'var(--text-secondary)' : 'white',
                                fontWeight: 600,
                                fontSize: '0.9rem',
                                cursor: isGenerating || !text.trim() ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.2s ease',
                                boxShadow: isGenerating || !text.trim() ? 'none' : '0 4px 12px rgba(99, 102, 241, 0.3)',
                            }}
                        >
                            {isGenerating ? (
                                <>
                                    <RotateCcw size={16} className="animate-spin" />
                                    Synthesizing...
                                </>
                            ) : (
                                <>
                                    <Volume2 size={16} />
                                    Generate Audio Patch
                                </>
                            )}
                        </button>
                    </div>

                    {/* Error Banner */}
                    {error && (
                        <div
                            style={{
                                padding: '0.75rem 1rem',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                borderRadius: '0.6rem',
                                color: '#ef4444',
                                fontSize: '0.85rem',
                            }}
                        >
                            {error}
                        </div>
                    )}

                    {/* Active Result Audio Player */}
                    {currentResult && currentResult.audio_url && (
                        <div
                            style={{
                                padding: '1rem',
                                borderRadius: '0.75rem',
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--accent-primary)',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.6rem',
                                animation: 'patchModalFadeIn 0.3s ease-out',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                    <button
                                        onClick={togglePlay}
                                        style={{
                                            width: '42px',
                                            height: '42px',
                                            borderRadius: '50%',
                                            border: 'none',
                                            background: 'var(--accent-primary)',
                                            color: 'white',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            transition: 'transform 0.15s ease',
                                        }}
                                        onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.08)')}
                                        onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
                                    >
                                        {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" style={{ marginLeft: '2px' }} />}
                                    </button>
                                    <div>
                                        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>
                                            Audio Patch Ready
                                        </span>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                            {speaker} · {pace}x · {formatTime(currentTime)} / {formatTime(duration)}
                                        </span>
                                    </div>
                                </div>

                                <a
                                    href={resolveAudioUrl(currentResult.audio_url)}
                                    download={`patch_${currentResult.patch_id || 'clip'}.wav`}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                        padding: '0.5rem 0.85rem',
                                        borderRadius: '0.5rem',
                                        background: 'var(--bg-secondary)',
                                        border: '1px solid var(--border-color)',
                                        color: 'var(--text-primary)',
                                        textDecoration: 'none',
                                        fontSize: '0.8rem',
                                        fontWeight: 500,
                                        transition: 'all 0.15s ease',
                                    }}
                                >
                                    <Download size={15} />
                                    Download .wav
                                </a>
                            </div>

                            {/* Scrubber */}
                            <input
                                type="range"
                                min="0"
                                max={duration || 0}
                                step="0.01"
                                value={currentTime}
                                onChange={(e) => {
                                    const val = parseFloat(e.target.value);
                                    if (activeAudioRef.current) {
                                        activeAudioRef.current.currentTime = val;
                                        setCurrentTime(val);
                                    }
                                }}
                                style={{
                                    width: '100%',
                                    accentColor: 'var(--accent-primary)',
                                    cursor: 'pointer',
                                }}
                            />

                            <audio
                                ref={activeAudioRef}
                                src={resolveAudioUrl(currentResult.audio_url)}
                                onTimeUpdate={() => setCurrentTime(activeAudioRef.current?.currentTime || 0)}
                                onLoadedMetadata={() => setDuration(activeAudioRef.current?.duration || 0)}
                                onEnded={() => {
                                    setIsPlaying(false);
                                    setCurrentTime(0);
                                }}
                                style={{ display: 'none' }}
                            />
                        </div>
                    )}

                    {/* Session History */}
                    {history.length > 0 && (
                        <div style={{ marginTop: '0.5rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    Recent Patches in this session ({history.length})
                                </span>
                                <button
                                    onClick={() => setHistory([])}
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: 'var(--text-secondary)',
                                        fontSize: '0.75rem',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                    }}
                                >
                                    <Trash2 size={13} /> Clear
                                </button>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '180px', overflowY: 'auto' }}>
                                {history.map((item) => (
                                    <div
                                        key={item.id}
                                        className="patch-history-card"
                                        style={{
                                            padding: '0.65rem 0.85rem',
                                            borderRadius: '0.6rem',
                                            background: 'var(--bg-secondary)',
                                            border: '1px solid var(--border-color)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            gap: '0.75rem',
                                            transition: 'all 0.15s ease',
                                        }}
                                    >
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <p
                                                style={{
                                                    fontSize: '0.85rem',
                                                    color: 'var(--text-primary)',
                                                    margin: 0,
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap',
                                                }}
                                            >
                                                {item.text}
                                            </p>
                                            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                                                {item.speaker} · {item.pace}x · {item.duration_estimate || 'clip'} · {item.createdAt}
                                            </span>
                                        </div>

                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                            <button
                                                onClick={() => {
                                                    setText(item.text);
                                                    setSpeaker(item.speaker);
                                                    setPace(item.pace);
                                                }}
                                                title="Load into editor"
                                                style={{
                                                    background: 'transparent',
                                                    border: '1px solid var(--border-color)',
                                                    color: 'var(--text-secondary)',
                                                    borderRadius: '6px',
                                                    padding: '0.3rem 0.5rem',
                                                    fontSize: '0.75rem',
                                                    cursor: 'pointer',
                                                }}
                                            >
                                                Reuse
                                            </button>
                                            <a
                                                href={resolveAudioUrl(item.audio_url)}
                                                download={`patch_${item.id}.wav`}
                                                title="Download"
                                                style={{
                                                    color: 'var(--accent-primary)',
                                                    padding: '0.35rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    borderRadius: '6px',
                                                }}
                                            >
                                                <Download size={15} />
                                            </a>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>,
        document.body
    );
}
