import React, { useState } from 'react';
import { Download, FileCode2, Edit3, Copy, Check, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import WikiScriptEditor from '../WikiScriptEditor';
import { apiJson, API_URL } from '../../services/api';

/**
 * Action buttons for messages with type === 'script_review'
 */
export default function ScriptReviewActions({
    msg,
    isTyping,
    openEditorId,
    setOpenEditorId,
    onDownloadScriptDocx,
    onSaveScriptEdit,
}) {
    // Local state for MediaWiki export
    const [mediaWikiResult, setMediaWikiResult] = useState(null);
    const [isExporting, setIsExporting] = useState(false);
    const [isMediaWikiOpen, setIsMediaWikiOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    // Handle MediaWiki export inline
    const handleExportMediaWiki = async () => {
        setIsExporting(true);
        try {
            const data = await apiJson('/export_mediawiki', {
                method: 'POST',
                body: JSON.stringify({ json_script: msg.jsonScript }),
            });
            setMediaWikiResult(data);
            setIsMediaWikiOpen(true);
        } catch (error) {
            console.error('MediaWiki export error:', error);
            setMediaWikiResult({ error: error.message });
        } finally {
            setIsExporting(false);
        }
    };

    // Copy to clipboard
    const handleCopy = async () => {
        if (mediaWikiResult?.mediawiki_content) {
            await navigator.clipboard.writeText(mediaWikiResult.mediawiki_content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // Download .wiki file
    const handleDownloadWiki = () => {
        if (mediaWikiResult?.mediawiki_file_url) {
            const a = document.createElement('a');
            a.href = `${API_URL}${mediaWikiResult.mediawiki_file_url}`;
            a.download = 'script.wiki';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    return (
        <div style={{ marginTop: '1rem', marginBottom: '1.5rem' }}>
            {/* Action Buttons Row */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Primary: Review & Edit Script */}
                <button
                    onClick={() => setOpenEditorId && setOpenEditorId(openEditorId === msg.id ? null : msg.id)}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: openEditorId === msg.id ? 'var(--accent-primary)' : 'var(--accent-primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.75rem',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                        boxShadow: 'var(--shadow-md)',
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
                    <Edit3 size={20} />
                    {openEditorId === msg.id ? 'Close Editor' : 'Review & Edit Script'}
                </button>

                {/* Secondary: Export to MediaWiki */}
                <button
                    onClick={handleExportMediaWiki}
                    disabled={isTyping || isExporting}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: (isTyping || isExporting) ? 'var(--bg-tertiary)' : '#059669',
                        color: (isTyping || isExporting) ? 'var(--text-secondary)' : 'white',
                        border: 'none',
                        borderRadius: '0.75rem',
                        cursor: (isTyping || isExporting) ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                        boxShadow: (isTyping || isExporting) ? 'none' : 'var(--shadow-md)',
                        opacity: (isTyping || isExporting) ? 0.6 : 1,
                    }}
                    onMouseEnter={(e) => {
                        if (!isTyping && !isExporting) {
                            e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        if (!isTyping && !isExporting) {
                            e.currentTarget.style.transform = 'translateY(0) scale(1)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }
                    }}
                >
                    {isExporting ? (
                        <><Loader2 size={20} className="animate-spin" /> Exporting...</>
                    ) : (
                        <><FileCode2 size={20} /> Export to MediaWiki</>
                    )}
                </button>

                {/* Tertiary: Download as .docx */}
                <button
                    onClick={() => onDownloadScriptDocx && onDownloadScriptDocx(msg.jsonScript)}
                    disabled={isTyping}
                    style={{
                        padding: '0.6rem 1rem',
                        background: isTyping ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.75rem',
                        cursor: isTyping ? 'not-allowed' : 'pointer',
                        fontWeight: 500,
                        fontSize: '0.9rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                        opacity: isTyping ? 0.6 : 1,
                    }}
                    onMouseEnter={(e) => {
                        if (!isTyping) {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.borderColor = 'var(--accent-primary)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        if (!isTyping) {
                            e.currentTarget.style.background = 'var(--bg-secondary)';
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                        }
                    }}
                >
                    <Download size={18} />
                    Download (.docx)
                </button>
            </div>

            {/* MediaWiki Export Result - Inline Collapsible */}
            {mediaWikiResult && !mediaWikiResult.error && (
                <div style={{
                    marginTop: '1rem',
                    border: '1px solid var(--border-color)',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    background: 'var(--bg-secondary)',
                }}>
                    {/* Collapsible Header */}
                    <div
                        onClick={() => setIsMediaWikiOpen(!isMediaWikiOpen)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '0.75rem 1rem',
                            background: 'var(--bg-tertiary)',
                            cursor: 'pointer',
                            borderBottom: isMediaWikiOpen ? '1px solid var(--border-color)' : 'none',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Check size={16} style={{ color: '#059669' }} />
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                                MediaWiki Export Ready
                            </span>
                        </div>
                        {isMediaWikiOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </div>

                    {/* Collapsible Content */}
                    {isMediaWikiOpen && (
                        <div style={{ padding: '1rem' }}>
                            {/* Action buttons */}
                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
                                <button
                                    onClick={handleCopy}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                        fontSize: '0.85rem',
                                        color: 'var(--text-primary)',
                                        fontWeight: 500,
                                    }}
                                >
                                    {copied ? <Check size={16} style={{ color: '#059669' }} /> : <Copy size={16} />}
                                    {copied ? 'Copied!' : 'Copy to Clipboard'}
                                </button>
                                <button
                                    onClick={handleDownloadWiki}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: '#059669',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                        fontSize: '0.85rem',
                                        color: 'white',
                                        fontWeight: 600,
                                    }}
                                >
                                    <Download size={16} />
                                    Download .wiki File
                                </button>
                            </div>

                            {/* Preview */}
                            <div style={{
                                background: 'var(--bg-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                padding: '1rem',
                                maxHeight: '300px',
                                overflow: 'auto',
                                fontFamily: 'monospace',
                                fontSize: '0.8rem',
                                whiteSpace: 'pre-wrap',
                                color: 'var(--text-primary)',
                            }}>
                                {mediaWikiResult.mediawiki_content}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* MediaWiki Export Error */}
            {mediaWikiResult?.error && (
                <div style={{
                    marginTop: '1rem',
                    padding: '0.75rem 1rem',
                    background: '#fce8e6',
                    border: '1px solid #d93025',
                    borderRadius: '8px',
                    color: '#d93025',
                    fontSize: '0.9rem',
                }}>
                    ❌ Export failed: {mediaWikiResult.error}
                </div>
            )}

            {/* Wiki-style Script Editor */}
            <WikiScriptEditor
                jsonScript={msg.jsonScript}
                isOpen={openEditorId === msg.id}
                onSave={(updatedScript) => onSaveScriptEdit && onSaveScriptEdit(msg.id, updatedScript)}
                onClose={() => setOpenEditorId && setOpenEditorId(null)}
            />

            <style>{`
                .animate-spin {
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}
