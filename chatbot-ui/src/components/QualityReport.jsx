import React, { useState, useEffect } from 'react';
import { X, Download, Globe, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * QualityReport - Displays quality check results and Hindi translation
 * Shows translation quality, timing, and transliteration checks
 * Plus the complete translated Hindi script
 */
const QualityReport = ({ report, isOpen, onClose }) => {
    const [expandedSlide, setExpandedSlide] = useState(null);

    // Don't render if not open or no report
    if (!isOpen || !report) return null;

    const {
        checks = [],
        summary = {},
        translated_script: translatedScript,
        language_code: languageCode = 'hi',
        language_name: languageName = 'Hindi',
        language_native: languageNative = 'हिंदी'
    } = report;

    const toggleSlide = (slideNum) => {
        setExpandedSlide(expandedSlide === slideNum ? null : slideNum);
    };

    return (
        <div className="quality-report" style={{
            marginTop: '1rem',
            background: 'var(--bg-primary)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
        }}>
            {/* Toolbar - Match ComplianceReport style */}
            <div className="report-toolbar" style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.875rem 1.25rem',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-color)',
                flexWrap: 'wrap',
                gap: '0.75rem',
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    flexWrap: 'wrap',
                }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        Quality Report ({languageName})
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-tertiary)',
                        padding: '0.2em 0.6em',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)'
                    }}>
                        {translatedScript?.slides?.length || 0} slides
                    </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '0.4rem',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-secondary)',
                        }}
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Quality Checks Table */}
            <div style={{
                padding: '1.25rem',
                background: 'var(--bg-primary)',
            }}>
                <h4 style={{ margin: '0 0 1rem 0', color: 'var(--text-primary)' }}>
                    Quality Checks
                </h4>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{
                        width: '100%',
                        borderCollapse: 'separate',
                        borderSpacing: '0',
                        fontSize: '14px',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        overflow: 'hidden'
                    }}>
                        <thead>
                            <tr>
                                <th style={{
                                    padding: '0.75rem',
                                    borderBottom: '1px solid var(--border-color)',
                                    borderRight: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-secondary)',
                                    fontWeight: 'bold',
                                    color: 'var(--text-primary)',
                                    width: '40%',
                                    textAlign: 'left'
                                }}>
                                    Criteria
                                </th>
                                <th style={{
                                    padding: '0.75rem',
                                    borderBottom: '1px solid var(--border-color)',
                                    borderRight: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-secondary)',
                                    fontWeight: 'bold',
                                    color: 'var(--text-primary)',
                                    width: '80px',
                                    textAlign: 'center',
                                }}>
                                    Status
                                </th>
                                <th style={{
                                    padding: '0.75rem',
                                    borderBottom: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                    fontWeight: 'bold',
                                    textAlign: 'left'
                                }}>
                                    Notes
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {checks.map((check, index) => (
                                <tr key={check.id || index}>
                                    <td style={{
                                        padding: '0.75rem',
                                        borderBottom: index === checks.length - 1 ? 'none' : '1px solid var(--border-color)',
                                        borderRight: '1px solid var(--border-color)',
                                        color: 'var(--text-primary)',
                                    }}>
                                        {check.criteria}
                                    </td>
                                    <td style={{
                                        padding: '0.75rem',
                                        borderBottom: index === checks.length - 1 ? 'none' : '1px solid var(--border-color)',
                                        borderRight: '1px solid var(--border-color)',
                                        textAlign: 'center',
                                        backgroundColor: check.ai_review === true ? 'rgba(52, 168, 83, 0.1)' :
                                            check.ai_review === false ? 'rgba(217, 48, 37, 0.1)' : 'transparent',
                                        fontSize: '1.2em',
                                    }}>
                                        {check.ai_review === true ? (
                                            <span style={{ color: '#34a853' }}>✓</span>
                                        ) : check.ai_review === false ? (
                                            <span style={{ color: '#d93025' }}>✗</span>
                                        ) : (
                                            <span style={{ color: 'var(--text-secondary)' }}>—</span>
                                        )}
                                    </td>
                                    <td style={{
                                        padding: '0.75rem',
                                        borderBottom: index === checks.length - 1 ? 'none' : '1px solid var(--border-color)',
                                        color: 'var(--text-secondary)',
                                    }}>
                                        {check.ai_notes}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Translated Script Section */}
            {translatedScript && (
                <div style={{
                    padding: '1.25rem',
                    borderTop: '1px solid var(--border-color)',
                    background: 'var(--bg-primary)',
                }}>
                    <h4 style={{
                        margin: '0 0 1rem 0',
                        color: 'var(--text-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem'
                    }}>
                        <Globe size={18} style={{ color: 'var(--accent-primary)' }} />
                        {languageName} Translation
                        <span style={{
                            fontSize: '0.9em',
                            color: 'var(--text-secondary)',
                            fontWeight: 'normal'
                        }}>
                            ({languageNative})
                        </span>
                    </h4>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {translatedScript.slides?.map((slide) => (
                            <div
                                key={slide.slide_number}
                                style={{
                                    background: 'var(--bg-secondary)',
                                    borderRadius: '12px',
                                    border: '1px solid var(--border-color)',
                                    overflow: 'hidden',
                                    transition: 'all 0.2s ease'
                                }}
                            >
                                {/* Slide Header - Clickable */}
                                <div
                                    onClick={() => toggleSlide(slide.slide_number)}
                                    className="slide-header"
                                    style={{
                                        padding: '1rem 1.25rem',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        cursor: 'pointer',
                                        background: expandedSlide === slide.slide_number ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                                        borderBottom: expandedSlide === slide.slide_number ? '1px solid var(--border-color)' : 'none',
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                        <span style={{
                                            fontWeight: 600,
                                            color: 'var(--accent-primary)',
                                            minWidth: '60px',
                                        }}>
                                            Row {slide.slide_number}
                                        </span>
                                        <span style={{
                                            fontSize: '0.85em',
                                            color: slide.meaning_preserved ? '#34a853' : '#d93025',
                                            background: slide.meaning_preserved ? 'rgba(52, 168, 83, 0.1)' : 'rgba(217, 48, 37, 0.1)',
                                            padding: '0.25em 0.75rem',
                                            borderRadius: '20px',
                                            border: `1px solid ${slide.meaning_preserved ? 'rgba(52, 168, 83, 0.2)' : 'rgba(217, 48, 37, 0.2)'}`
                                        }}>
                                            {slide.meaning_preserved ? '✓ Match' : '⚠️ Mismatch'} ({slide.similarity_score || 0}/5)
                                        </span>
                                    </div>
                                    {expandedSlide === slide.slide_number ?
                                        <ChevronUp size={20} style={{ color: 'var(--text-secondary)' }} /> :
                                        <ChevronDown size={20} style={{ color: 'var(--text-secondary)' }} />
                                    }
                                </div>

                                {/* Expanded Content - Swipeable Carousel on Mobile */}
                                {expandedSlide === slide.slide_number && (
                                    <div style={{ padding: '1.25rem', background: 'var(--bg-primary)' }}>
                                        {/* Carousel Container */}
                                        <div
                                            className="translation-carousel"
                                            style={{
                                                display: 'flex',
                                                overflowX: 'auto',
                                                scrollSnapType: 'x mandatory',
                                                scrollBehavior: 'smooth',
                                                gap: '1rem',
                                                paddingBottom: '0.75rem',
                                                marginBottom: slide.issues?.length > 0 ? '1.25rem' : 0,
                                                WebkitOverflowScrolling: 'touch',
                                            }}
                                        >
                                            {/* Card 1: Original English */}
                                            <div
                                                className="translation-card"
                                                style={{
                                                    flex: '0 0 calc(33.333% - 0.75rem)',
                                                    minWidth: '280px',
                                                    scrollSnapAlign: 'start',
                                                }}
                                            >
                                                <label style={{
                                                    display: 'block',
                                                    fontSize: '0.7rem',
                                                    color: 'var(--text-secondary)',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.1em',
                                                    fontWeight: 700,
                                                }}>
                                                    Original (English)
                                                </label>
                                                <div style={{
                                                    padding: '1rem',
                                                    background: 'var(--bg-secondary)',
                                                    borderRadius: '8px',
                                                    border: '1px solid var(--border-color)',
                                                    color: 'var(--text-primary)',
                                                    fontSize: '0.9rem',
                                                    lineHeight: '1.6',
                                                    minHeight: '100px',
                                                }}>
                                                    {slide.narration_original}
                                                </div>
                                            </div>

                                            {/* Card 2: Language Translation */}
                                            <div
                                                className="translation-card"
                                                style={{
                                                    flex: '0 0 calc(33.333% - 0.75rem)',
                                                    minWidth: '280px',
                                                    scrollSnapAlign: 'start',
                                                }}
                                            >
                                                <label style={{
                                                    display: 'block',
                                                    fontSize: '0.7rem',
                                                    color: 'var(--accent-primary)',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.1em',
                                                    fontWeight: 700,
                                                }}>
                                                    {languageName} Translation
                                                </label>
                                                <div style={{
                                                    padding: '1rem',
                                                    background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
                                                    borderRadius: '8px',
                                                    border: '1px solid var(--accent-primary)',
                                                    color: 'var(--text-primary)',
                                                    fontFamily: 'Noto Sans Devanagari, sans-serif',
                                                    fontSize: '1rem',
                                                    lineHeight: '1.8',
                                                    minHeight: '100px',
                                                }}>
                                                    {slide.narration}
                                                </div>
                                            </div>

                                            {/* Card 3: Back Translation */}
                                            <div
                                                className="translation-card"
                                                style={{
                                                    flex: '0 0 calc(33.333% - 0.75rem)',
                                                    minWidth: '280px',
                                                    scrollSnapAlign: 'start',
                                                }}
                                            >
                                                <label style={{
                                                    display: 'block',
                                                    fontSize: '0.7rem',
                                                    color: slide.meaning_preserved ? '#34a853' : '#d93025',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.1em',
                                                    fontWeight: 700,
                                                }}>
                                                    Back-Translation {slide.meaning_preserved ? '✓' : '⚠️'}
                                                </label>
                                                <div style={{
                                                    padding: '1rem',
                                                    background: slide.meaning_preserved ? 'rgba(52, 168, 83, 0.05)' : 'rgba(217, 48, 37, 0.05)',
                                                    borderRadius: '8px',
                                                    border: `1px solid ${slide.meaning_preserved ? '#34a853' : '#d93025'}`,
                                                    color: 'var(--text-primary)',
                                                    fontSize: '0.9rem',
                                                    lineHeight: '1.6',
                                                    minHeight: '100px',
                                                }}>
                                                    {slide.back_translation || 'N/A'}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Swipe Indicator - Only visible on mobile */}
                                        <div
                                            className="swipe-indicator"
                                            style={{
                                                display: 'none',
                                                justifyContent: 'center',
                                                gap: '0.5rem',
                                                marginTop: '0.5rem',
                                            }}
                                        >
                                            <span style={{
                                                fontSize: '0.75rem',
                                                color: 'var(--text-secondary)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.25rem',
                                            }}>
                                                ← Swipe to view all →
                                            </span>
                                        </div>

                                        {/* Issues if any */}
                                        {slide.issues?.length > 0 && (
                                            <div>
                                                <label style={{
                                                    display: 'block',
                                                    fontSize: '0.7rem',
                                                    color: '#d93025',
                                                    marginBottom: '0.5rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.1em',
                                                    fontWeight: 700,
                                                }}>
                                                    Issues Found
                                                </label>
                                                <ul style={{
                                                    margin: 0,
                                                    padding: '0.75rem 1rem 0.75rem 2rem',
                                                    background: 'rgba(217, 48, 37, 0.05)',
                                                    borderRadius: '8px',
                                                    border: '1px solid rgba(217, 48, 37, 0.2)',
                                                    fontSize: '0.9rem',
                                                }}>
                                                    {slide.issues.map((issue, i) => (
                                                        <li key={i} style={{ color: '#d93025', marginBottom: '0.25rem' }}>{issue}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Help text */}
            <div style={{
                padding: '1rem 1.25rem',
                background: 'var(--bg-secondary)',
                borderTop: '1px solid var(--border-color)',
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
            }}>
                <strong style={{ color: 'var(--text-primary)' }}>How it works:</strong> English → {languageName} → Back to English. If back-translation matches original, the translation is accurate.
            </div>

            <style>{`
                .slide-header:hover {
                    background: var(--bg-tertiary) !important;
                }
            `}</style>
        </div>
    );
};

export default QualityReport;
