import React, { useState } from 'react';
import { X, Clock, Loader2, Download, AlertCircle, FileAudio } from 'lucide-react';
import { apiFormData } from '../services/api';

/**
 * TimedScriptModal - Modal for generating timed scripts from audio
 */
export default function TimedScriptModal({ isOpen, onClose, file }) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    if (!isOpen) return null;

    const handleSubmit = async () => {
        if (!file) return;

        setIsLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('audio', file);

            const data = await apiFormData('/timed-script/generate', formData);
            setResult(data);
        } catch (err) {
            setError(err.message || 'Failed to generate timed script');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDownloadDocx = async () => {
        if (!result) return;

        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || '/api'}/timed-script/download-docx`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                    },
                    body: JSON.stringify(result),
                }
            );

            if (!response.ok) {
                throw new Error('Failed to generate DOCX');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${file?.name?.replace(/\.[^/.]+$/, '') || 'timed_script'}_timed_script.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError(err.message || 'Failed to download DOCX');
        }
    };

    const handleClose = () => {
        setResult(null);
        setError(null);
        onClose();
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
        }}>
            <div style={{
                background: 'var(--bg-primary)',
                borderRadius: '1rem',
                width: '100%',
                maxWidth: '700px',
                maxHeight: '90vh',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: 'var(--shadow-lg)',
            }}>
                {/* Header */}
                <div style={{
                    padding: '1.25rem 1.5rem',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '0.5rem',
                            background: 'var(--accent-primary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <Clock size={18} color="white" />
                        </div>
                        <div>
                            <h2 style={{
                                margin: 0,
                                fontSize: '1.1rem',
                                fontWeight: 600,
                                color: 'var(--text-primary)',
                            }}>
                                Timed Script Generator
                            </h2>
                            <p style={{
                                margin: 0,
                                fontSize: '0.8rem',
                                color: 'var(--text-secondary)',
                            }}>
                                Generate sentence-level timestamps
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.5rem',
                            borderRadius: '0.5rem',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div style={{
                    padding: '1.5rem',
                    overflowY: 'auto',
                    flex: 1,
                }}>
                    {/* File Info */}
                    {file && !result && (
                        <div style={{
                            padding: '1rem',
                            background: 'var(--bg-secondary)',
                            borderRadius: '0.75rem',
                            marginBottom: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                        }}>
                            <FileAudio size={24} style={{ color: 'var(--accent-primary)' }} />
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                    {file.name}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Error Display */}
                    {error && (
                        <div style={{
                            marginBottom: '1rem',
                            padding: '0.75rem 1rem',
                            background: 'rgba(239, 68, 68, 0.1)',
                            borderRadius: '0.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            color: '#ef4444',
                            fontSize: '0.9rem',
                        }}>
                            <AlertCircle size={18} />
                            {error}
                        </div>
                    )}

                    {/* Results */}
                    {result && (
                        <>
                            {/* Summary */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '1rem',
                                padding: '0.75rem 1rem',
                                background: 'var(--bg-secondary)',
                                borderRadius: '0.5rem',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                        <strong style={{ color: 'var(--text-primary)' }}>{result.total_sentences}</strong> sentences
                                    </span>
                                    <span style={{
                                        fontSize: '0.85rem',
                                        color: 'var(--accent-primary)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                    }}>
                                        <Clock size={14} />
                                        {result.total_duration}
                                    </span>
                                </div>
                                <button
                                    onClick={handleDownloadDocx}
                                    style={{
                                        padding: '0.4rem 0.75rem',
                                        borderRadius: '0.375rem',
                                        border: 'none',
                                        background: 'var(--accent-primary)',
                                        color: 'white',
                                        fontSize: '0.8rem',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                    }}
                                >
                                    <Download size={14} />
                                    Download DOCX
                                </button>
                            </div>

                            {/* Sentences Table */}
                            <div style={{
                                maxHeight: '350px',
                                overflowY: 'auto',
                                borderRadius: '0.5rem',
                                border: '1px solid var(--border-color)',
                            }}>
                                <table style={{
                                    width: '100%',
                                    borderCollapse: 'collapse',
                                    fontSize: '0.85rem',
                                }}>
                                    <thead>
                                        <tr style={{
                                            background: 'var(--bg-secondary)',
                                            position: 'sticky',
                                            top: 0,
                                        }}>
                                            <th style={{
                                                padding: '0.65rem 0.75rem',
                                                textAlign: 'left',
                                                fontWeight: 600,
                                                color: 'var(--text-primary)',
                                                borderBottom: '1px solid var(--border-color)',
                                                width: '110px',
                                            }}>
                                                Time Range
                                            </th>
                                            <th style={{
                                                padding: '0.65rem 0.75rem',
                                                textAlign: 'left',
                                                fontWeight: 600,
                                                color: 'var(--text-primary)',
                                                borderBottom: '1px solid var(--border-color)',
                                            }}>
                                                Text
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.sentences.map((sentence, index) => (
                                            <tr
                                                key={sentence.sentence_number}
                                                style={{
                                                    background: index % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                                                }}
                                            >
                                                <td style={{
                                                    padding: '0.65rem 0.75rem',
                                                    color: 'var(--accent-primary)',
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.8rem',
                                                    fontWeight: 500,
                                                    borderBottom: '1px solid var(--border-color)',
                                                    whiteSpace: 'nowrap',
                                                }}>
                                                    {sentence.time_range}
                                                </td>
                                                <td style={{
                                                    padding: '0.65rem 0.75rem',
                                                    color: 'var(--text-primary)',
                                                    borderBottom: '1px solid var(--border-color)',
                                                    lineHeight: 1.4,
                                                }}>
                                                    {sentence.text}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '1rem 1.5rem',
                    borderTop: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '0.75rem',
                }}>
                    {!result ? (
                        <>
                            <button
                                onClick={handleClose}
                                style={{
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'transparent',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.9rem',
                                    cursor: 'pointer',
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={!file || isLoading}
                                style={{
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '0.5rem',
                                    border: 'none',
                                    background: isLoading ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                                    color: isLoading ? 'var(--text-secondary)' : 'white',
                                    fontSize: '0.9rem',
                                    fontWeight: 600,
                                    cursor: isLoading ? 'not-allowed' : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                }}
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={16} className="spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <Clock size={16} />
                                        Generate Timed Script
                                    </>
                                )}
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={handleClose}
                            style={{
                                padding: '0.6rem 1.25rem',
                                borderRadius: '0.5rem',
                                border: 'none',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                fontSize: '0.9rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                            }}
                        >
                            Done
                        </button>
                    )}
                </div>
            </div>

            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .spin {
                    animation: spin 1s linear infinite;
                }
            `}</style>
        </div>
    );
}
