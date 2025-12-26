import React from 'react';
import { FileText, Download, Upload, FileCode2, Edit3 } from 'lucide-react';
import WikiScriptEditor from '../WikiScriptEditor';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Action buttons for messages with type === 'script_review'
 */
export default function ScriptReviewActions({
    msg,
    isTyping,
    openEditorId,
    setOpenEditorId,
    editedScriptInputRef,
    onGenerateSlides,
    onDownloadScriptDocx,
    onUploadEditedScript,
    onExportMediaWiki,
    onSaveScriptEdit,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
            {/* PDF Link */}
            <div style={{ marginBottom: '1rem' }}>
                <a
                    href={`${API_URL}${msg.pdfUrl}`}
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
                    View Script PDF
                </a>
                {msg.wasEdited && (
                    <span style={{
                        marginLeft: '0.75rem',
                        color: '#059669',
                        fontSize: '0.85rem',
                        fontWeight: 500
                    }}>
                        ✓ Edited
                    </span>
                )}
            </div>

            {/* Edit Script Section */}
            <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
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
                    Download Script (.docx)
                </button>

                <input
                    type="file"
                    accept=".docx"
                    style={{ display: 'none' }}
                    ref={editedScriptInputRef}
                    onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                            onUploadEditedScript(file, msg.id);
                            e.target.value = '';
                        }
                    }}
                />

                <button
                    onClick={() => editedScriptInputRef.current?.click()}
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
                    <Upload size={18} />
                    Upload Edited Script
                </button>
            </div>

            {/* Action Buttons Row */}
            <button
                onClick={() => onExportMediaWiki(msg.jsonScript)}
                disabled={isTyping}
                style={{
                    marginLeft: '0.75rem',
                    padding: '0.75rem 1.5rem',
                    background: isTyping
                        ? 'var(--bg-tertiary)'
                        : 'linear-gradient(135deg, #059669, #10b981)',
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

            <button
                onClick={() => setOpenEditorId(openEditorId === msg.id ? null : msg.id)}
                style={{
                    marginLeft: '0.75rem',
                    padding: '0.75rem 1.5rem',
                    background: openEditorId === msg.id
                        ? 'linear-gradient(135deg, #7c3aed, #a855f7)'
                        : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
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
                {openEditorId === msg.id ? 'Close Editor' : 'Edit Script Inline'}
            </button>

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
