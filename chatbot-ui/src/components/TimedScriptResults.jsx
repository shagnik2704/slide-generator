import React, { useState } from 'react';
import { Clock, Download, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * TimedScriptResults - Display timed script generation results
 * Shows sentence-level timestamps with time ranges and download option.
 */
export default function TimedScriptResults({ timedScriptData, filename }) {
    const [isDownloading, setIsDownloading] = useState(false);
    const [showAll, setShowAll] = useState(false);

    if (!timedScriptData) return null;

    const { sentences = [], total_sentences, total_duration } = timedScriptData;

    // Show first 10 sentences by default, or all if toggled
    const visibleSentences = showAll ? sentences : sentences.slice(0, 10);
    const hasMore = sentences.length > 10;

    const handleDownloadDocx = async () => {
        setIsDownloading(true);
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || '/api'}/timed-script/download-docx`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                    },
                    body: JSON.stringify(timedScriptData),
                }
            );

            if (!response.ok) {
                throw new Error('Failed to generate DOCX');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${filename?.replace(/\.[^/.]+$/, '') || 'timed_script'}_timed_script.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download error:', err);
        } finally {
            setIsDownloading(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Summary Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.875rem 1rem',
                background: 'var(--bg-secondary)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border-color)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: 'var(--accent-primary)'
                        }}>
                            {total_sentences}
                        </span>
                        <span style={{
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)'
                        }}>
                            sentences
                        </span>
                    </div>
                    <div style={{
                        height: '24px',
                        width: '1px',
                        background: 'var(--border-color)'
                    }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Clock size={16} style={{ color: 'var(--accent-primary)' }} />
                        <span style={{
                            fontSize: '0.9rem',
                            fontWeight: 600,
                            color: 'var(--text-primary)'
                        }}>
                            {total_duration}
                        </span>
                    </div>
                </div>
                <button
                    onClick={handleDownloadDocx}
                    disabled={isDownloading}
                    style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '0.5rem',
                        border: 'none',
                        background: 'var(--accent-primary)',
                        color: 'white',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        cursor: isDownloading ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        opacity: isDownloading ? 0.7 : 1,
                        transition: 'all 0.2s ease',
                    }}
                >
                    {isDownloading ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Generating...
                        </>
                    ) : (
                        <>
                            <Download size={14} />
                            Download DOCX
                        </>
                    )}
                </button>
            </div>

            {/* Sentences Table */}
            <div style={{
                borderRadius: '0.75rem',
                border: '1px solid var(--border-color)',
                overflow: 'hidden',
            }}>
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.85rem',
                }}>
                    <thead>
                        <tr style={{ background: 'var(--bg-secondary)' }}>
                            <th style={{
                                padding: '0.75rem 1rem',
                                textAlign: 'left',
                                fontWeight: 600,
                                color: 'var(--text-primary)',
                                borderBottom: '1px solid var(--border-color)',
                                width: '120px',
                            }}>
                                Time Range
                            </th>
                            <th style={{
                                padding: '0.75rem 1rem',
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
                        {visibleSentences.map((sentence, index) => (
                            <tr
                                key={sentence.sentence_number || index}
                                style={{
                                    background: index % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                                }}
                            >
                                <td style={{
                                    padding: '0.75rem 1rem',
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
                                    padding: '0.75rem 1rem',
                                    color: 'var(--text-primary)',
                                    borderBottom: '1px solid var(--border-color)',
                                    lineHeight: 1.5,
                                }}>
                                    {sentence.text}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {/* Show More/Less Toggle */}
                {hasMore && (
                    <button
                        onClick={() => setShowAll(!showAll)}
                        style={{
                            width: '100%',
                            padding: '0.75rem',
                            background: 'var(--bg-secondary)',
                            border: 'none',
                            borderTop: '1px solid var(--border-color)',
                            color: 'var(--accent-primary)',
                            fontSize: '0.85rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            transition: 'background 0.2s ease',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'var(--bg-secondary)'}
                    >
                        {showAll ? (
                            <>
                                <ChevronUp size={16} />
                                Show Less
                            </>
                        ) : (
                            <>
                                <ChevronDown size={16} />
                                Show All {sentences.length} Sentences
                            </>
                        )}
                    </button>
                )}
            </div>

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
