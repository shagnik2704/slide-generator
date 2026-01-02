import React, { useState } from 'react';
import { Play, Pause, Download, Volume2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * VoicePreview - Displays audio players for generated voice files
 * Supports both:
 * - audio_urls: Multiple files (one per slide)
 * - audio_url: Single combined file (entire script)
 */
export default function VoicePreview({ voiceData, isOpen = true }) {
    const [playingSlide, setPlayingSlide] = useState(null);

    if (!voiceData || !isOpen) return null;

    // Support both formats
    const { audio_urls, audio_url, zip_url, generated_slides, total_slides, errors, duration_estimate } = voiceData;

    // Check if this is a combined (single file) response
    const isCombined = audio_url && !audio_urls;

    const handlePlay = (slideNum, audioRef) => {
        if (playingSlide === slideNum) {
            audioRef.pause();
            setPlayingSlide(null);
        } else {
            // Pause any currently playing audio
            document.querySelectorAll('audio').forEach(a => a.pause());
            audioRef.play();
            setPlayingSlide(slideNum);
        }
    };

    const handleEnded = () => {
        setPlayingSlide(null);
    };

    return (
        <div style={{
            marginTop: '1rem',
            padding: '1rem',
            background: 'var(--bg-secondary)',
            borderRadius: '0.75rem',
            border: '1px solid var(--border-color)',
        }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid var(--border-color)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Volume2 size={20} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {isCombined ? 'Full Audio' : 'Audio Preview'}
                    </span>
                    <span style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-tertiary)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.5rem'
                    }}>
                        {isCombined ? `${total_slides} Rows` : `${generated_slides}/${total_slides} Rows`}
                    </span>
                    {duration_estimate && (
                        <span style={{
                            fontSize: '0.85rem',
                            color: 'var(--accent-primary)',
                            background: 'var(--bg-tertiary)',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '0.5rem'
                        }}>
                            {duration_estimate}
                        </span>
                    )}
                </div>

                {/* Download button - works for both zip_url and audio_url */}
                {(zip_url || audio_url) && (
                    <a
                        href={`${API_URL}${zip_url || audio_url}`}
                        download
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 1rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            borderRadius: '0.5rem',
                            textDecoration: 'none',
                            fontSize: '0.85rem',
                            fontWeight: 500,
                        }}
                    >
                        <Download size={16} />
                        {isCombined ? 'Download Audio' : 'Download All'}
                    </a>
                )}
            </div>

            {/* Combined Audio - Single Player */}
            {isCombined && (
                <AudioPlayer
                    slideNum="full"
                    url={`${API_URL}${audio_url}`}
                    isPlaying={playingSlide === 'full'}
                    onPlay={handlePlay}
                    onEnded={handleEnded}
                    isCombined={true}
                />
            )}

            {/* Multiple Audio Players Grid */}
            {!isCombined && audio_urls && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                    gap: '0.75rem',
                }}>
                    {Object.entries(audio_urls).map(([slideNum, url]) => (
                        <AudioPlayer
                            key={slideNum}
                            slideNum={slideNum}
                            url={`${API_URL}${url}`}
                            isPlaying={playingSlide === slideNum}
                            onPlay={handlePlay}
                            onEnded={handleEnded}
                        />
                    ))}
                </div>
            )}

            {/* Errors */}
            {errors && errors.length > 0 && (
                <div style={{
                    marginTop: '1rem',
                    padding: '0.75rem',
                    background: 'rgba(239, 68, 68, 0.1)',
                    borderRadius: '0.5rem',
                    fontSize: '0.85rem',
                    color: '#ef4444',
                }}>
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
 * Individual audio player for a slide with premium seekbar
 */
function AudioPlayer({ slideNum, url, isPlaying, onPlay, onEnded, isCombined = false }) {
    const audioRef = React.useRef(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isSeeking, setIsSeeking] = useState(false);

    // Update time state as audio plays (but not while user is dragging)
    const handleTimeUpdate = () => {
        if (audioRef.current && !isSeeking) {
            setCurrentTime(audioRef.current.currentTime);
        }
    };

    // Initialize duration when metadata loads
    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    // Format seconds into M:SS
    const formatTime = (time) => {
        if (isNaN(time)) return "0:00";
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Handle seeker changes
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
                gap: '0.5rem',
                padding: '1rem',
                background: 'var(--bg-tertiary)',
                borderRadius: '0.75rem',
                border: isPlaying ? '1px solid var(--accent-primary)' : '1px solid transparent',
                transition: 'all 0.3s ease',
                boxShadow: isPlaying ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
            }}
        >
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
            }}>
                <button
                    onClick={() => onPlay(slideNum, audioRef.current)}
                    style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        border: 'none',
                        background: isPlaying ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                        color: isPlaying ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s ease',
                        boxShadow: 'var(--shadow-sm)',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.1)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" style={{ marginLeft: '2px' }} />}
                </button>

                <div style={{ flex: 1 }}>
                    <div style={{
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <span>{isCombined ? 'Full Narration' : `Row ${slideNum}`}</span>
                        <span style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)'
                        }}>
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </span>
                    </div>
                </div>

                <a
                    href={url}
                    download={isCombined ? 'full_narration.wav' : `row_${slideNum}.wav`}
                    style={{
                        color: 'var(--text-secondary)',
                        padding: '0.4rem',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-secondary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                    title="Download"
                >
                    <Download size={16} />
                </a>
            </div>

            {/* Premium Seekbar */}
            <div style={{
                position: 'relative',
                height: '6px',
                display: 'flex',
                alignItems: 'center',
                marginTop: '0.25rem'
            }}>
                <input
                    type="range"
                    min="0"
                    max={duration || 0}
                    step="0.01"
                    value={currentTime}
                    onMouseDown={() => setIsSeeking(true)}
                    onMouseUp={() => setIsSeeking(false)}
                    onTouchStart={() => setIsSeeking(true)}
                    onTouchEnd={() => setIsSeeking(false)}
                    onChange={handleSeek}
                    className="custom-seekbar"
                    style={{
                        backgroundSize: `${(currentTime / (duration || 1)) * 100}% 100%`,
                        backgroundImage: `linear-gradient(var(--accent-primary), var(--accent-primary))`,
                    }}
                />
            </div>

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
