import React, { useState } from 'react';
import { Play, Pause, Download, Volume2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * VoicePreview - Displays audio players for generated voice files
 */
export default function VoicePreview({ voiceData, isOpen = true }) {
    const [playingSlide, setPlayingSlide] = useState(null);

    if (!voiceData || !isOpen) return null;

    const { audio_urls, zip_url, generated_slides, total_slides, errors } = voiceData;

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
                        Audio Preview
                    </span>
                    <span style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-tertiary)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.5rem'
                    }}>
                        {generated_slides}/{total_slides} slides
                    </span>
                </div>

                {zip_url && (
                    <a
                        href={`${API_URL}${zip_url}`}
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
                        Download All
                    </a>
                )}
            </div>

            {/* Audio Players Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                gap: '0.75rem',
            }}>
                {audio_urls && Object.entries(audio_urls).map(([slideNum, url]) => (
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
                    <strong>Failed slides:</strong>
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
 * Individual audio player for a slide
 */
function AudioPlayer({ slideNum, url, isPlaying, onPlay, onEnded }) {
    const audioRef = React.useRef(null);

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem',
            background: 'var(--bg-tertiary)',
            borderRadius: '0.5rem',
            border: isPlaying ? '1px solid var(--accent-primary)' : '1px solid transparent',
        }}>
            <button
                onClick={() => onPlay(slideNum, audioRef.current)}
                style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    border: 'none',
                    background: isPlaying ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                    color: isPlaying ? 'white' : 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s ease',
                }}
            >
                {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>

            <div style={{ flex: 1 }}>
                <div style={{
                    fontSize: '0.9rem',
                    fontWeight: 500,
                    color: 'var(--text-primary)'
                }}>
                    Slide {slideNum}
                </div>
                <audio
                    ref={audioRef}
                    src={url}
                    onEnded={onEnded}
                    style={{ display: 'none' }}
                />
            </div>

            <a
                href={url}
                download={`slide_${slideNum}.wav`}
                style={{
                    color: 'var(--text-secondary)',
                    padding: '0.25rem',
                }}
                title="Download"
            >
                <Download size={16} />
            </a>
        </div>
    );
}
