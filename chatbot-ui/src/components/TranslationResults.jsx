import React from 'react';
import { Check, X, Download, Languages, ChevronDown, ChevronUp, FileText, List, Grid3X3 } from 'lucide-react';
import { apiRequest } from '../services/api';

/**
 * TranslationResults - Displays translation results with side-by-side comparison
 */
export default function TranslationResults({ results }) {
    const [expandedLang, setExpandedLang] = React.useState(null);
    const [downloadingLang, setDownloadingLang] = React.useState(null);
    const [viewMode, setViewMode] = React.useState('list'); // 'list' | 'compare'

    if (!results || !results.results || results.results.length === 0) {
        return null;
    }

    const { results: translations, total_requested, total_success } = results;

    // Handle DOCX download
    const handleDownload = async (result) => {
        if (!result.success || !result.translated_script) return;

        setDownloadingLang(result.language_code);

        try {
            const response = await apiRequest('/translation/export_docx', {
                method: 'POST',
                body: JSON.stringify({
                    translated_script: result.translated_script,
                    language_code: result.language_code,
                    language_name: result.language
                })
            });

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `script_${result.language_code}.docx`;
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
        // Expand width in Compare mode for better multi-column view
        ...(viewMode === 'compare' ? {
            position: 'relative',
            width: 'calc(100vw - 140px)',
            maxWidth: '1400px',
            left: '50%',
            transform: 'translateX(-50%)',
        } : {}),
        transition: 'all 0.3s ease',
    };

    const headerStyle = {
        padding: '1rem 1.25rem',
        borderBottom: '1px solid var(--border-primary)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
    };

    const resultCardStyle = (success) => ({
        borderBottom: '1px solid var(--border-primary)',
        background: success ? 'transparent' : 'rgba(239, 68, 68, 0.05)',
    });

    const statusBadgeStyle = (success) => ({
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.25rem 0.75rem',
        borderRadius: '20px',
        fontSize: '0.8rem',
        fontWeight: 500,
        background: success
            ? 'rgba(34, 197, 94, 0.1)'
            : 'rgba(239, 68, 68, 0.1)',
        color: success ? '#22c55e' : '#ef4444',
    });

    const buttonStyle = {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        borderRadius: '8px',
        border: '1px solid var(--border-primary)',
        background: 'var(--bg-secondary)',
        color: 'var(--text-primary)',
        cursor: 'pointer',
        fontSize: '0.85rem',
        fontWeight: 500,
        transition: 'all 0.2s ease',
    };

    const downloadButtonStyle = {
        ...buttonStyle,
        background: 'var(--accent-primary)',
        border: 'none',
        color: 'white',
    };

    const tableStyle = {
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '0.9rem',
    };

    const thStyle = {
        padding: '0.75rem 1rem',
        textAlign: 'left',
        fontWeight: 600,
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        fontSize: '0.85rem',
        color: 'var(--text-secondary)',
    };

    const tdStyle = {
        padding: '1.25rem 1.5rem',
        borderBottom: '1px solid var(--border-primary)',
        verticalAlign: 'top',
        lineHeight: 1.8,
    };

    // Format text: parse **bold** and add line breaks after sentences
    const formatText = (text) => {
        if (!text) return null;

        // Split by sentences (period, question mark, exclamation followed by space)
        const sentences = text.split(/(?<=[।.?!])\s+/);

        return sentences.map((sentence, sentenceIndex) => {
            // Parse **bold** markers within each sentence
            const parts = [];
            const boldPattern = /\*\*(.+?)\*\*/g;
            let lastIndex = 0;
            let match;

            while ((match = boldPattern.exec(sentence)) !== null) {
                // Add text before the bold
                if (match.index > lastIndex) {
                    parts.push(sentence.substring(lastIndex, match.index));
                }
                // Add bold text
                parts.push(<strong key={`bold-${sentenceIndex}-${match.index}`}>{match[1]}</strong>);
                lastIndex = match.index + match[0].length;
            }
            // Add remaining text
            if (lastIndex < sentence.length) {
                parts.push(sentence.substring(lastIndex));
            }

            return (
                <span key={sentenceIndex} style={{ display: 'block', marginBottom: '0.75rem' }}>
                    {parts.length > 0 ? parts : sentence}
                </span>
            );
        });
    };

    const toggleExpanded = (langCode) => {
        setExpandedLang(prev => prev === langCode ? null : langCode);
    };

    return (
        <div style={containerStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <Languages size={22} style={{ color: 'var(--accent-primary)' }} />
                <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                        Translation Complete
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {total_success} of {total_requested} language{total_requested !== 1 ? 's' : ''} successful
                    </div>
                </div>
                {/* View Mode Toggle */}
                <div style={{
                    display: 'flex',
                    gap: '0.25rem',
                    background: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    padding: '0.25rem',
                    border: '1px solid var(--border-primary)',
                }}>
                    <button
                        onClick={() => setViewMode('list')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
                            borderRadius: '6px',
                            border: 'none',
                            background: viewMode === 'list' ? 'var(--accent-primary)' : 'transparent',
                            color: viewMode === 'list' ? 'white' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            transition: 'all 0.2s ease',
                        }}
                    >
                        <List size={14} />
                        List
                    </button>
                    <button
                        onClick={() => setViewMode('compare')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
                            borderRadius: '6px',
                            border: 'none',
                            background: viewMode === 'compare' ? 'var(--accent-primary)' : 'transparent',
                            color: viewMode === 'compare' ? 'white' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            transition: 'all 0.2s ease',
                        }}
                    >
                        <Grid3X3 size={14} />
                        Compare
                    </button>
                </div>
            </div>


            {/* LIST VIEW - Per-language expandable cards */}
            {viewMode === 'list' && translations.map((result, index) => (
                <div
                    key={result.language_code || index}
                    style={resultCardStyle(result.success)}
                >
                    {/* Result Header */}
                    <div style={{
                        padding: '1rem 1.25rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '1rem',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div>
                                <div style={{ fontWeight: 500, fontSize: '1rem' }}>
                                    {result.language}
                                </div>
                                <div style={{
                                    fontSize: '1.1rem',
                                    color: 'var(--text-secondary)',
                                    fontFamily: 'system-ui'
                                }}>
                                    {result.language_native}
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            {/* Status badge - only show for failed */}
                            {!result.success && (
                                <span style={statusBadgeStyle(false)}>
                                    <X size={14} /> Failed
                                </span>
                            )}

                            {/* Actions */}
                            {result.success && (
                                <>
                                    {/* View toggle */}
                                    <button
                                        onClick={() => toggleExpanded(result.language_code)}
                                        style={buttonStyle}
                                    >
                                        {expandedLang === result.language_code ? (
                                            <><ChevronUp size={16} /> Hide</>
                                        ) : (
                                            <><ChevronDown size={16} /> View</>
                                        )}
                                    </button>

                                    {/* Download button */}
                                    <button
                                        onClick={() => handleDownload(result)}
                                        style={downloadButtonStyle}
                                        disabled={downloadingLang === result.language_code}
                                    >
                                        {downloadingLang === result.language_code ? (
                                            <>Downloading...</>
                                        ) : (
                                            <><Download size={16} /> DOCX</>
                                        )}
                                    </button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Error message */}
                    {!result.success && result.error && (
                        <div style={{
                            margin: '0 1.25rem 1rem',
                            padding: '0.5rem 0.75rem',
                            background: 'rgba(239, 68, 68, 0.1)',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            color: '#ef4444',
                        }}>
                            {result.error}
                        </div>
                    )}

                    {/* Side-by-side comparison table */}
                    {expandedLang === result.language_code && result.success && (
                        <div style={{
                            margin: '0 1.25rem 1.25rem',
                            border: '1px solid var(--border-primary)',
                            borderRadius: '8px',
                            overflow: 'hidden',
                            maxHeight: '500px',
                            overflowY: 'auto',
                        }}>
                            <table style={tableStyle}>
                                <thead>
                                    <tr>
                                        <th style={{ ...thStyle, width: '60px' }}>Row</th>
                                        <th style={{ ...thStyle, width: '45%' }}>English (Original)</th>
                                        <th style={{ ...thStyle, width: '45%' }}>{result.language}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {result.translated_script?.slides?.map((slide, i) => (
                                        <tr key={i} style={{
                                            background: i % 2 === 0 ? 'transparent' : 'var(--bg-secondary)'
                                        }}>
                                            <td style={{ ...tdStyle, fontWeight: 500, textAlign: 'center' }}>
                                                {slide.slide_number}
                                            </td>
                                            <td style={tdStyle}>
                                                <div style={{ marginBottom: '0.5rem' }}>
                                                    <div style={{
                                                        fontSize: '0.75rem',
                                                        color: 'var(--text-secondary)',
                                                        marginBottom: '0.25rem',
                                                        fontWeight: 500,
                                                    }}>
                                                        Narration
                                                    </div>
                                                    {formatText(slide.narration)}
                                                </div>
                                            </td>
                                            <td style={{ ...tdStyle, fontFamily: 'system-ui' }}>
                                                <div style={{ marginBottom: '0.5rem' }}>
                                                    <div style={{
                                                        fontSize: '0.75rem',
                                                        color: 'var(--text-secondary)',
                                                        marginBottom: '0.25rem',
                                                        fontWeight: 500,
                                                    }}>
                                                        Narration
                                                    </div>
                                                    <span style={{ color: 'var(--accent-primary)' }}>
                                                        {formatText(slide[`narration_${result.language_code}`]) || '—'}
                                                    </span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            ))}

            {/* COMPARE VIEW - Multi-column table with all languages */}
            {viewMode === 'compare' && (
                <div style={{ padding: '1rem 1.25rem' }}>

                    {/* Multi-column comparison table */}
                    <div style={{
                        border: '1px solid var(--border-primary)',
                        borderRadius: '8px',
                        overflow: 'hidden',
                        overflowX: 'auto',
                    }}>
                        <table style={{ ...tableStyle, minWidth: `${200 + translations.filter(t => t.success).length * 250}px` }}>
                            <thead>
                                <tr>
                                    <th style={{ ...thStyle, width: '70px', position: 'sticky', left: 0, background: 'var(--bg-secondary)', zIndex: 1 }}>Row</th>
                                    <th style={{ ...thStyle, minWidth: '200px' }}>English</th>
                                    {translations.filter(t => t.success).map(result => (
                                        <th key={result.language_code} style={{ ...thStyle, minWidth: '200px' }}>
                                            {result.language}
                                            <div style={{ fontSize: '0.9rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
                                                {result.language_native}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {/* Use first successful translation as source for slides */}
                                {(() => {
                                    const slides = translations.find(t => t.success)?.translated_script?.slides || [];
                                    return slides.map((slide, i) => (
                                        <tr key={i} style={{
                                            background: i % 2 === 0 ? 'transparent' : 'var(--bg-secondary)'
                                        }}>
                                            <td style={{
                                                ...tdStyle,
                                                fontWeight: 600,
                                                textAlign: 'center',
                                                position: 'sticky',
                                                left: 0,
                                                background: i % 2 === 0 ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                                                zIndex: 1,
                                                fontSize: '0.9rem',
                                                color: 'var(--text-primary)',
                                            }}>
                                                {slide.slide_number || i + 1}
                                            </td>
                                            <td style={tdStyle}>
                                                {formatText(slide.narration)}
                                            </td>
                                            {translations.filter(t => t.success).map(result => (
                                                <td key={result.language_code} style={{ ...tdStyle, fontFamily: 'system-ui' }}>
                                                    <span style={{ color: 'var(--accent-primary)' }}>
                                                        {formatText(result.translated_script?.slides?.[i]?.[`narration_${result.language_code}`]) || '—'}
                                                    </span>
                                                </td>
                                            ))}
                                        </tr>
                                    ));
                                })()}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
