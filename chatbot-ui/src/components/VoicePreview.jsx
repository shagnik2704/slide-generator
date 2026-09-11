import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Play, Pause, Download, Volume2, Clock, Sparkles, Edit3, Check, X, RotateCcw, AlertCircle, FileAudio } from 'lucide-react';
import AudioPatchModal from './AudioPatchModal';
import { apiJson } from '../services/api';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * VoicePreview - Displays script narration text and audio players
 * Supports:
 * - Seeing the actual narration text for every row
 * - Selecting any word/phrase to patch in the AudioPatchModal
 * - In-place row editing & regeneration (re-records single slide & re-stitches)
 * - Single combined audio player & individual row players
 */
export default function VoicePreview({ voiceData, jsonScript, projectId, isOpen = true }) {
    const [playingSlide, setPlayingSlide] = useState(null);

    // Audio state that can be updated on in-place regeneration
    const initialSlideAudio = voiceData?.audio_urls || voiceData?.slide_audio_urls || {};
    const [localSlideAudio, setLocalSlideAudio] = useState(initialSlideAudio);
    const [localFullAudio, setLocalFullAudio] = useState(voiceData?.audio_url || null);
    const [localZipUrl, setLocalZipUrl] = useState(voiceData?.zip_url || null);

    // Sync with incoming voiceData
    useEffect(() => {
        if (voiceData) {
            setLocalSlideAudio(voiceData.audio_urls || voiceData.slide_audio_urls || {});
            setLocalFullAudio(voiceData.audio_url || null);
            setLocalZipUrl(voiceData.zip_url || null);
        }
    }, [voiceData]);

    // Map slides from jsonScript for quick lookup by slide_number
    const [slidesMap, setSlidesMap] = useState({});
    useEffect(() => {
        const map = {};
        if (jsonScript && Array.isArray(jsonScript.slides)) {
            jsonScript.slides.forEach((s, idx) => {
                const num = s.slide_number || idx + 1;
                map[num] = {
                    title: s.title || `Slide ${num}`,
                    narration: s.narration || '',
                };
            });
        }
        setSlidesMap(map);
    }, [jsonScript]);

    // Audio Patch Modal state
    const [isPatchModalOpen, setIsPatchModalOpen] = useState(false);
    const [patchModalText, setPatchModalText] = useState('');

    // In-place Row Editing state
    const [editingSlideNum, setEditingSlideNum] = useState(null);
    const [editingText, setEditingText] = useState('');
    const [regeneratingSlideNum, setRegeneratingSlideNum] = useState(null);
    const [regenError, setRegenError] = useState(null);

    // Floating selection tooltip: { text, slideNum, x, y }
    const [selectionTooltip, setSelectionTooltip] = useState(null);
    const previewContainerRef = useRef(null);

    if (!voiceData || !isOpen) return null;

    const {
        total_slides,
        generated_slides,
        errors,
        duration_estimate,
    } = voiceData;

    const hasSlideAudio = Object.keys(localSlideAudio).length > 0;
    const hasFullAudio = Boolean(localFullAudio);

    const handlePlay = (slideNum, audioRef) => {
        if (playingSlide === slideNum) {
            audioRef.pause();
            setPlayingSlide(null);
        } else {
            // Pause any currently playing audio
            document.querySelectorAll('audio').forEach((a) => a.pause());
            audioRef.play();
            setPlayingSlide(slideNum);
        }
    };

    const handleEnded = () => {
        setPlayingSlide(null);
    };

    // Text selection detection inside row narration
    const handleMouseUp = (slideNum) => {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        if (selectedText && selectedText.length > 0 && selectedText.length < 250) {
            try {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                setSelectionTooltip({
                    text: selectedText,
                    slideNum,
                    x: rect.left + rect.width / 2,
                    y: rect.top - 10,
                });
            } catch (e) {
                setSelectionTooltip(null);
            }
        } else {
            setSelectionTooltip(null);
        }
    };

    // Open Patch Modal pre-filled
    const handleOpenPatch = (textToPatch) => {
        setPatchModalText(textToPatch || '');
        setIsPatchModalOpen(true);
        setSelectionTooltip(null);
    };

    // Start editing row inline
    const handleStartEdit = (slideNum, currentNarration) => {
        setEditingSlideNum(slideNum);
        setEditingText(currentNarration || '');
        setRegenError(null);
    };

    // Cancel inline editing
    const handleCancelEdit = () => {
        setEditingSlideNum(null);
        setEditingText('');
        setRegenError(null);
    };

    // Save and re-record row
    const handleSaveAndRegenerate = async (slideNum) => {
        if (!editingText.trim()) return;

        setRegeneratingSlideNum(slideNum);
        setRegenError(null);

        const activeProjectId = projectId || voiceData.project_id;

        try {
            if (activeProjectId) {
                // Call dedicated regenerate endpoint that updates slide & re-stitches full audio
                const res = await apiJson('/regenerate_slide', {
                    method: 'POST',
                    body: JSON.stringify({
                        project_id: activeProjectId,
                        slide_number: parseInt(slideNum, 10),
                        text: editingText.trim(),
                    }),
                });

                if (res.success) {
                    // Update slide audio URL (with cache-busting timestamp)
                    const bustUrl = `${res.slide_audio_url}?t=${Date.now()}`;
                    setLocalSlideAudio((prev) => ({
                        ...prev,
                        [slideNum]: bustUrl,
                    }));

                    if (res.full_audio_url) {
                        setLocalFullAudio(`${res.full_audio_url}?t=${Date.now()}`);
                    }
                    if (res.zip_url) {
                        setLocalZipUrl(`${res.zip_url}?t=${Date.now()}`);
                    }

                    // Update local narration text
                    setSlidesMap((prev) => ({
                        ...prev,
                        [slideNum]: {
                            ...prev[slideNum],
                            narration: editingText.trim(),
                        },
                    }));

                    setEditingSlideNum(null);
                } else {
                    setRegenError(res.error || 'Failed to regenerate row');
                }
            } else {
                // Fallback to standalone patch if no projectId is available
                const res = await apiJson('/generate_voice_patch', {
                    method: 'POST',
                    body: JSON.stringify({
                        text: editingText.trim(),
                    }),
                });

                if (res.success) {
                    setLocalSlideAudio((prev) => ({
                        ...prev,
                        [slideNum]: `${res.audio_url}?t=${Date.now()}`,
                    }));
                    setSlidesMap((prev) => ({
                        ...prev,
                        [slideNum]: {
                            ...prev[slideNum],
                            narration: editingText.trim(),
                        },
                    }));
                    setEditingSlideNum(null);
                }
            }
        } catch (err) {
            console.error('Failed to regenerate slide:', err);
            setRegenError(err.message || 'Error re-recording row');
        } finally {
            setRegeneratingSlideNum(null);
        }
    };

    const resolveUrl = (url) => {
        if (!url) return '';
        if (url.startsWith('http')) return url;
        return `${API_URL}${url}`;
    };

    return (
        <div
            ref={previewContainerRef}
            style={{
                marginTop: '1rem',
                padding: '1.25rem',
                background: 'var(--bg-secondary)',
                borderRadius: '0.85rem',
                border: '1px solid var(--border-color)',
                position: 'relative',
            }}
        >
            {/* Header */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '1.25rem',
                    paddingBottom: '0.85rem',
                    borderBottom: '1px solid var(--border-color)',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <Volume2 size={20} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1rem' }}>
                        Audio Studio & Review
                    </span>
                    <span
                        style={{
                            fontSize: '0.8rem',
                            color: 'var(--text-secondary)',
                            background: 'var(--bg-tertiary)',
                            padding: '0.2rem 0.55rem',
                            borderRadius: '0.4rem',
                        }}
                    >
                        {generated_slides == null ? `${total_slides || Object.keys(localSlideAudio).length} Rows` : `${generated_slides}/${total_slides} Rows`}
                    </span>
                    {duration_estimate && (
                        <span
                            style={{
                                fontSize: '0.8rem',
                                color: 'var(--accent-primary)',
                                background: 'var(--bg-tertiary)',
                                padding: '0.2rem 0.55rem',
                                borderRadius: '0.4rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                fontWeight: 500,
                            }}
                        >
                            <Clock size={13} />
                            {duration_estimate}
                        </span>
                    )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <button
                        onClick={() => handleOpenPatch('')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.45rem 0.85rem',
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-color)',
                            color: 'var(--text-primary)',
                            borderRadius: '0.5rem',
                            fontSize: '0.82rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                        }}
                        title="Open standalone audio patch sandbox"
                    >
                        <Sparkles size={14} style={{ color: 'var(--accent-primary)' }} />
                        Audio Patch Sandbox
                    </button>

                    {(localZipUrl || localFullAudio) && (
                        <a
                            href={resolveUrl(localZipUrl || localFullAudio)}
                            download
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.45rem 0.95rem',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                borderRadius: '0.5rem',
                                textDecoration: 'none',
                                fontSize: '0.82rem',
                                fontWeight: 500,
                            }}
                        >
                            <Download size={15} />
                            {localZipUrl ? 'Download All (ZIP)' : 'Download Audio'}
                        </a>
                    )}
                </div>
            </div>

            {/* Combined Audio - Single Player Card */}
            {hasFullAudio && (
                <div style={{ marginBottom: '1.25rem' }}>
                    <AudioPlayer
                        slideNum="full"
                        title="Full Continuous Narration"
                        url={resolveUrl(localFullAudio)}
                        isPlaying={playingSlide === 'full'}
                        onPlay={handlePlay}
                        onEnded={handleEnded}
                        isCombined={true}
                    />
                </div>
            )}

            {/* Per-Slide Section */}
            {hasSlideAudio && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            Script Rows & Audio ({Object.keys(localSlideAudio).length})
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            💡 Tip: Highlight any word to patch it, or click Edit to re-record
                        </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                        {Object.entries(localSlideAudio).map(([slideNum, url]) => {
                            const slideInfo = slidesMap[slideNum] || {};
                            const isEditing = editingSlideNum === slideNum;
                            const isRegenerating = regeneratingSlideNum === slideNum;

                            return (
                                <div
                                    key={slideNum}
                                    style={{
                                        padding: '1rem',
                                        borderRadius: '0.75rem',
                                        background: 'var(--bg-tertiary)',
                                        border: isEditing ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '0.75rem',
                                        transition: 'all 0.2s ease',
                                    }}
                                >
                                    {/* Row Header */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                            <span
                                                style={{
                                                    fontSize: '0.78rem',
                                                    fontWeight: 600,
                                                    background: 'var(--accent-primary)',
                                                    color: 'white',
                                                    padding: '0.2rem 0.5rem',
                                                    borderRadius: '0.4rem',
                                                }}
                                            >
                                                Row {slideNum}
                                            </span>
                                            {slideInfo.title && (
                                                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                                    {slideInfo.title}
                                                </span>
                                            )}
                                        </div>

                                        {/* Row Actions */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                            <button
                                                onClick={() => handleOpenPatch(slideInfo.narration || '')}
                                                title="Send this row to Audio Patch sandbox"
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.25rem',
                                                    padding: '0.25rem 0.5rem',
                                                    background: 'transparent',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '0.4rem',
                                                    color: 'var(--text-secondary)',
                                                    fontSize: '0.75rem',
                                                    cursor: 'pointer',
                                                }}
                                            >
                                                <Sparkles size={12} style={{ color: 'var(--accent-primary)' }} />
                                                Patch
                                            </button>

                                            {!isEditing ? (
                                                <button
                                                    onClick={() => handleStartEdit(slideNum, slideInfo.narration || '')}
                                                    title="Edit text and re-record this row"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.25rem',
                                                        padding: '0.25rem 0.5rem',
                                                        background: 'transparent',
                                                        border: '1px solid var(--border-color)',
                                                        borderRadius: '0.4rem',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.75rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    <Edit3 size={12} />
                                                    Edit
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={handleCancelEdit}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.25rem',
                                                        padding: '0.25rem 0.5rem',
                                                        background: 'transparent',
                                                        border: '1px solid var(--border-color)',
                                                        borderRadius: '0.4rem',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.75rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    <X size={12} />
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Narration Content: Read-only or Editable */}
                                    {!isEditing ? (
                                        <div
                                            onMouseUp={() => handleMouseUp(slideNum)}
                                            style={{
                                                fontSize: '0.92rem',
                                                lineHeight: '1.55',
                                                color: 'var(--text-primary)',
                                                background: 'var(--bg-secondary)',
                                                padding: '0.65rem 0.85rem',
                                                borderRadius: '0.5rem',
                                                border: '1px solid var(--border-color)',
                                                cursor: 'text',
                                                userSelect: 'text',
                                            }}
                                        >
                                            {slideInfo.narration || <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No narration text recorded for this slide</span>}
                                        </div>
                                    ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            <textarea
                                                rows={3}
                                                value={editingText}
                                                onChange={(e) => setEditingText(e.target.value)}
                                                style={{
                                                    width: '100%',
                                                    padding: '0.65rem',
                                                    borderRadius: '0.5rem',
                                                    border: '1px solid var(--accent-primary)',
                                                    background: 'var(--bg-secondary)',
                                                    color: 'var(--text-primary)',
                                                    fontSize: '0.92rem',
                                                    lineHeight: '1.5',
                                                    resize: 'vertical',
                                                    boxSizing: 'border-box',
                                                    fontFamily: 'inherit',
                                                }}
                                            />
                                            {regenError && (
                                                <span style={{ fontSize: '0.78rem', color: '#ef4444' }}>
                                                    {regenError}
                                                </span>
                                            )}
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <button
                                                    onClick={handleCancelEdit}
                                                    disabled={isRegenerating}
                                                    style={{
                                                        padding: '0.4rem 0.75rem',
                                                        borderRadius: '0.4rem',
                                                        border: '1px solid var(--border-color)',
                                                        background: 'transparent',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.8rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    onClick={() => handleSaveAndRegenerate(slideNum)}
                                                    disabled={isRegenerating || !editingText.trim()}
                                                    style={{
                                                        padding: '0.4rem 0.85rem',
                                                        borderRadius: '0.4rem',
                                                        border: 'none',
                                                        background: 'var(--accent-primary)',
                                                        color: 'white',
                                                        fontSize: '0.8rem',
                                                        fontWeight: 600,
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.35rem',
                                                        cursor: isRegenerating || !editingText.trim() ? 'not-allowed' : 'pointer',
                                                    }}
                                                >
                                                    {isRegenerating ? (
                                                        <>
                                                            <RotateCcw size={13} className="animate-spin" />
                                                            Re-recording row...
                                                        </>
                                                    ) : (
                                                        <>
                                                            <RotateCcw size={13} />
                                                            Save & Re-record Row
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Audio Player for this row */}
                                    <AudioPlayer
                                        slideNum={slideNum}
                                        url={resolveUrl(url)}
                                        isPlaying={playingSlide === slideNum}
                                        onPlay={handlePlay}
                                        onEnded={handleEnded}
                                        isCombined={false}
                                    />
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Floating Highlight-to-Patch Tooltip */}
            {selectionTooltip && (
                <div
                    style={{
                        position: 'fixed',
                        left: `${selectionTooltip.x}px`,
                        top: `${selectionTooltip.y}px`,
                        transform: 'translate(-50%, -100%)',
                        zIndex: 10000,
                        animation: 'fadeIn 0.15s ease-out',
                    }}
                >
                    <button
                        onClick={() => handleOpenPatch(selectionTooltip.text)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '20px',
                            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        <Sparkles size={13} />
                        Patch "{selectionTooltip.text.length > 18 ? selectionTooltip.text.slice(0, 18) + '...' : selectionTooltip.text}"
                    </button>
                </div>
            )}

            {/* Audio Patch Modal (shares engine with Sidebar) */}
            <AudioPatchModal
                isOpen={isPatchModalOpen}
                onClose={() => setIsPatchModalOpen(false)}
                initialText={patchModalText}
            />

            {/* Errors display */}
            {errors && errors.length > 0 && (
                <div
                    style={{
                        marginTop: '1rem',
                        padding: '0.75rem',
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderRadius: '0.5rem',
                        fontSize: '0.85rem',
                        color: '#ef4444',
                    }}
                >
                    <strong>Failed rows:</strong>
                    <ul style={{ margin: '0.5rem 0 0 1rem', padding: 0 }}>
                        {errors.map((err, i) => (
                            <li key={i}>{err}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

/**
 * Individual audio player component with scrub bar
 */
function AudioPlayer({ slideNum, title, url, isPlaying, onPlay, onEnded, isCombined = false }) {
    const audioRef = useRef(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isSeeking, setIsSeeking] = useState(false);

    const handleTimeUpdate = () => {
        if (audioRef.current && !isSeeking) {
            setCurrentTime(audioRef.current.currentTime);
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const formatTime = (time) => {
        if (isNaN(time)) return '0:00';
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const handleSeek = (e) => {
        const time = parseFloat(e.target.value);
        if (audioRef.current) {
            audioRef.current.currentTime = time;
            setCurrentTime(time);
        }
    };

    return (
        <div
            className="audio-player-card"
            style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                padding: isCombined ? '1rem' : '0.6rem 0.8rem',
                background: isCombined ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                borderRadius: '0.6rem',
                border: isPlaying ? '1px solid var(--accent-primary)' : '1px solid transparent',
                transition: 'all 0.2s ease',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <button
                    onClick={() => onPlay(slideNum, audioRef.current)}
                    style={{
                        width: isCombined ? '42px' : '34px',
                        height: isCombined ? '42px' : '34px',
                        borderRadius: '50%',
                        border: 'none',
                        background: isPlaying ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                        color: isPlaying ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.15s ease',
                    }}
                >
                    {isPlaying ? <Pause size={isCombined ? 18 : 15} fill="currentColor" /> : <Play size={isCombined ? 18 : 15} fill="currentColor" style={{ marginLeft: '2px' }} />}
                </button>

                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: isCombined ? '0.92rem' : '0.82rem', fontWeight: 500, color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{title || (isCombined ? 'Full Narration' : `Audio Clip (Row ${slideNum})`)}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </span>
                    </div>
                </div>

                <a
                    href={url}
                    download={isCombined ? 'full_narration.wav' : `row_${slideNum}.wav`}
                    style={{
                        color: 'var(--text-secondary)',
                        padding: '0.35rem',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                    title="Download WAV"
                >
                    <Download size={15} />
                </a>
            </div>

            {/* Seekbar */}
            <input
                type="range"
                min="0"
                max={duration || 0}
                step="0.01"
                value={currentTime}
                onMouseDown={() => setIsSeeking(true)}
                onMouseUp={() => setIsSeeking(false)}
                onChange={handleSeek}
                style={{
                    width: '100%',
                    height: '4px',
                    accentColor: 'var(--accent-primary)',
                    cursor: 'pointer',
                    marginTop: '0.2rem',
                }}
            />

            <audio
                ref={audioRef}
                src={url}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onDurationChange={handleLoadedMetadata}
                onEnded={onEnded}
                style={{ display: 'none' }}
            />
        </div>
    );
}
