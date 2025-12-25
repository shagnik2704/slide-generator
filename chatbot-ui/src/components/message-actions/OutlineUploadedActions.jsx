import React from 'react';
import { FileText } from 'lucide-react';

/**
 * Action button for messages with type === 'outline_uploaded'
 */
export default function OutlineUploadedActions({
    msg,
    isTyping,
    onGenerateScript,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            <button
                onClick={() => onGenerateScript(msg.outline, msg.projectId)}
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
                <FileText size={20} />
                Generate Script from Edited Content
            </button>
        </div>
    );
}
