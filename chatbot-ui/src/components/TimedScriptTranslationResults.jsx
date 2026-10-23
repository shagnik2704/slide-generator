import React, { useState } from 'react';
import { Clock, Download, ChevronDown, ChevronUp, FileText, Check, Loader2 } from 'lucide-react';
import { apiRequest } from '../services/api';

/**
 * TimedScriptTranslationResults - Displays translated timed scripts with side-by-side comparison
 * and DOCX download options.
 */
export default function TimedScriptTranslationResults({ results }) {
    const [activeLangIndex, setActiveLangIndex] = useState(0);
    const [downloadingLang, setDownloadingLang] = useState(null);
    const [showAll, setShowAll] = useState(false);

    if (!results || !results.results || results.results.length === 0) {
        return null;
    }

    const { results: translations, total_requested, total_success } = results;
    const activeResult = translations[activeLangIndex] || translations[0];

    // Download translated DOCX handler
    const handleDownloadDocx = async (result) => {
        if (!result.success || !result.rows || result.rows.length === 0) return;

        setDownloadingLang(result.language_code);

        try {
            const response = await apiRequest('/timed-script/export-translated-docx', {
                method: 'POST',
                body: JSON.stringify({
                    rows: result.rows,
                    language_code: result.language_code,
                    language_name: result.language,
                    language_native: result.language_native || '',
                    title: result.title || 'Timed Script',
                    total_duration: result.total_duration || '00:00'
                })
            });

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const safeTitle = (result.title || 'timed_script').replace(/\s+/g, '_');
            a.download = `${safeTitle}_${result.language_code}_timed_script.docx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Download error:', error);
        } finally {
            setDownloadingLang(null);
        }
    };

    const containerStyle = {
        background: 'var(--bg-tertiary)',
        borderRadius: '12px',
        border: '1px solid var(--border-primary)',
        overflow: 'hidden',
        marginTop: '1rem',
    };

    const headerStyle = {
        padding: '1rem 1.25rem',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
    };

    const buttonStyle = {
        padding: '0.45rem 0.9rem',
        borderRadius: '8px',
        border: '1px solid var(--border-primary)',
        background: 'var(--bg-tertiary)',
        color: 'var(--text-primary)',
        fontSize: '0.85rem',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        transition: 'all 0.2s ease',
    };

    const downloadButtonStyle = {
        ...buttonStyle,
        background: 'var(--accent-primary)',
        color: 'white',
        border: 'none',
        fontWeight: 500,
    };

    const tabStyle = (isActive) => ({
        padding: '0.5rem 1rem',
        borderRadius: '8px',
        border: `1px solid ${isActive ? 'var(--accent-primary)' : 'var(--border-primary)'}`,
        background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-secondary)',
        color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
        fontWeight: isActive ? 600 : 400,
        fontSize: '0.85rem',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        transition: 'all 0.15s ease',
    });

    const thStyle = {
        padding: '0.75rem 1rem',
        textAlign: 'left',
        fontWeight: 600,
        fontSize: '0.85rem',
        color: 'var(--text-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        background: 'var(--bg-secondary)',
    };

    const tdStyle = {
        padding: '0.75rem 1rem',
        fontSize: '0.875rem',
        color: 'var(--text-primary)',
        borderBottom: '1px solid var(--border-primary)',
        verticalAlign: 'top',
        lineHeight: 1.5,
    };

    const rows = activeResult?.rows || [];
    const visibleRows = showAll ? rows : rows.slice(0, 12);
    const hasMore = rows.length > 12;

    return (
        <div style={containerStyle}>
            {/* Top Summary Bar */}
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Clock size={18} style={{ color: 'var(--accent-primary)' }} />
                        <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                            {activeResult?.title || 'Timed Script'}
                        </span>
                    </div>

                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)'
                    }}>
                        <span><strong>{activeResult?.total_rows || rows.length}</strong> rows</span>
                        <span>•</span>
                        <span><strong>{activeResult?.total_duration || '00:00'}</strong></span>
                        <span>•</span>
                        <span><strong>{total_success}</strong> / {total_requested} languages</span>
                    </div>
                </div>

                {/* Download Button */}
                {activeResult?.success && (
                    <button
                        onClick={() => handleDownloadDocx(activeResult)}
                        style={downloadButtonStyle}
                        disabled={downloadingLang === activeResult.language_code}
                    >
                        {downloadingLang === activeResult.language_code ? (
                            <>
                                <Loader2 size={15} className="animate-spin" />
                                Downloading...
                            </>
                        ) : (
                            <>
                                <Download size={15} />
                                Download DOCX ({activeResult.language})
                            </>
                        )}
                    </button>
                )}
            </div>

            {/* Language Selection Tabs if multiple */}
            {translations.length > 1 && (
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.25rem',
                    background: 'var(--bg-tertiary)',
                    borderBottom: '1px solid var(--border-primary)',
                    overflowX: 'auto',
                }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginRight: '0.25rem' }}>
                        Language:
                    </span>
                    {translations.map((res, idx) => (
                        <button
                            key={res.language_code || idx}
                            onClick={() => setActiveLangIndex(idx)}
                            style={tabStyle(idx === activeLangIndex)}
                        >
                            <span>{res.language}</span>
                            <span style={{ fontFamily: 'system-ui', fontSize: '0.8rem', opacity: 0.85 }}>
                                ({res.language_native})
                            </span>
                            {res.success ? (
                                <Check size={13} style={{ color: 'var(--accent-primary)' }} />
                            ) : (
                                <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>Failed</span>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {/* Results Table */}
            {activeResult?.success ? (
                <div>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr>
                                    <th style={{ ...thStyle, width: '100px', textAlign: 'center' }}>Time</th>
                                    <th style={{ ...thStyle, width: '45%' }}>English (Original)</th>
                                    <th style={{ ...thStyle, width: '45%' }}>
                                        {activeResult.language} ({activeResult.language_native})
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {visibleRows.map((row, idx) => (
                                    <tr
                                        key={row.row_number || idx}
                                        style={{
                                            background: idx % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                                        }}
                                    >
                                        <td style={{
                                            ...tdStyle,
                                            textAlign: 'center',
                                            fontWeight: 600,
                                            fontFamily: 'monospace',
                                            color: 'var(--accent-primary)',
                                            fontSize: '0.825rem',
                                            whiteSpace: 'nowrap',
                                        }}>
                                            {row.time}
                                        </td>
                                        <td style={tdStyle}>
                                            {row.narration}
                                        </td>
                                        <td style={{
                                            ...tdStyle,
                                            fontFamily: 'system-ui',
                                            color: 'var(--text-primary)',
                                        }}>
                                            <span style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>
                                                {row.narration_translated || row[`narration_${activeResult.language_code}`] || '—'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Show All / Show Less Toggle */}
                    {hasMore && (
                        <button
                            onClick={() => setShowAll(!showAll)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                background: 'var(--bg-secondary)',
                                border: 'none',
                                borderTop: '1px solid var(--border-primary)',
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
                                    Show All {rows.length} Rows
                                </>
                            )}
                        </button>
                    )}
                </div>
            ) : (
                <div style={{ padding: '1.5rem', color: '#ef4444' }}>
                    Translation failed: {activeResult?.error || 'Unknown error'}
                </div>
            )}
        </div>
    );
}
