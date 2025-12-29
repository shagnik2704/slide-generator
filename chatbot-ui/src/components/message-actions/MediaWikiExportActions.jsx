import React from 'react';
import { Download, Copy, Check } from 'lucide-react';

/**
 * Action buttons for messages with type === 'mediawiki_export'
 */
export default function MediaWikiExportActions({
    msg,
    copiedId,
    setCopiedId,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            {/* MediaWiki content preview */}
            <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: '0.75rem',
                padding: '1rem',
                marginBottom: '1rem',
                maxHeight: '300px',
                overflowY: 'auto',
                border: '1px solid var(--border-color)'
            }}>
                <pre style={{
                    margin: 0,
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: 'var(--text-primary)'
                }}>
                    {msg.mediawikiContent}
                </pre>
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                    onClick={() => {
                        navigator.clipboard.writeText(msg.mediawikiContent);
                        setCopiedId(msg.id);
                        setTimeout(() => setCopiedId(null), 2000);
                    }}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.75rem',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                    }}
                    onMouseEnter={(e) => {
                        if (copiedId !== msg.id) {
                            e.currentTarget.style.background = 'var(--bg-secondary)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        if (copiedId !== msg.id) {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                        }
                    }}
                >
                    {copiedId === msg.id ? <Check size={20} /> : <Copy size={20} />}
                    {copiedId === msg.id ? 'Copied!' : 'Copy to Clipboard'}
                </button>

                <button
                    onClick={() => {
                        const blob = new Blob([msg.mediawikiContent], { type: 'text/plain' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'script.wiki';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    }}
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.75rem 1.5rem',
                        background: '#065f46',
                        color: 'white',
                        textDecoration: 'none',
                        borderRadius: '0.75rem',
                        fontSize: '1rem',
                        fontWeight: 600,
                        border: 'none',
                        boxShadow: 'var(--shadow-md)',
                        transition: 'all 0.3s ease',
                        cursor: 'pointer',
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
                    Download .wiki File
                </button>
            </div>
        </div>
    );
}
