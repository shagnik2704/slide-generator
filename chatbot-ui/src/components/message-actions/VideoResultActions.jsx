import React from 'react';
import { Download } from 'lucide-react';

/**
 * Action buttons for messages with type === 'video_result'
 */
export default function VideoResultActions({ msg }) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            <video controls width="100%" style={{
                borderRadius: '0.75rem',
                boxShadow: 'var(--shadow-lg)',
                marginBottom: '1rem'
            }}>
                <source src={msg.videoUrl} type="video/mp4" />
                Your browser does not support the video tag.
            </video>
            <a
                href={msg.videoUrl}
                download="presentation.mp4"
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.5rem',
                    background: 'var(--accent-primary)',
                    color: 'white',
                    textDecoration: 'none',
                    borderRadius: '0.75rem',
                    fontSize: '1rem',
                    fontWeight: 600,
                    border: 'none',
                    boxShadow: 'var(--shadow-md)',
                    transition: 'all 0.3s ease',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                }}
            >
                <Download size={20} />
                Download Video
            </a>
        </div>
    );
}
