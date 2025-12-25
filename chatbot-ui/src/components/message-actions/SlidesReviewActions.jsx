import React from 'react';
import { FileText, Video } from 'lucide-react';

/**
 * Action buttons for messages with type === 'slides_review'
 */
export default function SlidesReviewActions({
    msg,
    isTyping,
    onApprove,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            <div style={{ marginBottom: '1rem' }}>
                <a
                    href={msg.pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                        color: 'var(--accent-primary)',
                        textDecoration: 'none',
                        fontWeight: 500,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                    onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                >
                    <FileText size={18} />
                    View Slides PDF
                </a>
            </div>
            <button
                onClick={() => onApprove(msg.jsonScript, msg.pdfPath, msg.projectId)}
                disabled={isTyping}
                style={{
                    padding: '0.75rem 1.5rem',
                    background: isTyping
                        ? 'var(--bg-tertiary)'
                        : 'var(--accent-primary)',
                    color: isTyping ? 'var(--text-secondary)' : 'white',
                    border: 'none',
                    borderRadius: '0.75rem',
                    cursor: isTyping ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '1rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    transition: 'all 0.3s ease',
                    boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                    opacity: isTyping ? 0.6 : 1,
                }}
                onMouseEnter={(e) => {
                    if (!isTyping) {
                        e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                    }
                }}
                onMouseLeave={(e) => {
                    if (!isTyping) {
                        e.currentTarget.style.transform = 'translateY(0) scale(1)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    }
                }}
            >
                <Video size={20} />
                Approve & Generate Video
            </button>
        </div>
    );
}
