import React from 'react';
import { Download, FileCode2, Edit3 } from 'lucide-react';
import WikiScriptEditor from '../WikiScriptEditor';

/**
 * Action buttons for messages with type === 'script_review'
 */
export default function ScriptReviewActions({
    msg,
    isTyping,
    openEditorId,
    setOpenEditorId,
    onDownloadScriptDocx,
    onExportMediaWiki,
    onSaveScriptEdit,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            {/* Action Buttons Row */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Primary: Review & Edit Script */}
                <button
                    onClick={() => setOpenEditorId(openEditorId === msg.id ? null : msg.id)}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: openEditorId === msg.id ? '#1a4480' : '#1a4480',
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
                    onClick={() => onExportMediaWiki(msg.jsonScript)}
                    disabled={isTyping}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: isTyping ? 'var(--bg-tertiary)' : '#059669',
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
                    <FileCode2 size={20} />
                    Export to MediaWiki
                </button>

                {/* Tertiary: Download as .docx */}
                <button
                    onClick={() => onDownloadScriptDocx(msg.jsonScript)}
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

            {/* Wiki-style Script Editor */}
            <WikiScriptEditor
                jsonScript={msg.jsonScript}
                isOpen={openEditorId === msg.id}
                onSave={(updatedScript) => onSaveScriptEdit(msg.id, updatedScript)}
                onClose={() => setOpenEditorId(null)}
            />
        </div>
    );
}
