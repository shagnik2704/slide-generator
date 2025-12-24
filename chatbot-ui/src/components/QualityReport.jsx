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

    const { checks = [], summary = {}, translated_script: translatedScript } = report;

    const toggleSlide = (slideNum) => {
        setExpandedSlide(expandedSlide === slideNum ? null : slideNum);
    };

    return (
        <div style={{
            marginTop: '1rem',
            background: '#fff',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            overflow: 'hidden',
        }}>
            {/* Toolbar - Match ComplianceReport style */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                background: '#f8f9fa',
                borderBottom: '1px solid #a2a9b1',
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    fontFamily: 'sans-serif',
                }}>
                    <span style={{ fontWeight: 600, color: '#202122' }}>
                        Quality Report (Hindi)
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: '#54595d',
                        background: '#eaecf0',
                        padding: '0.2em 0.6em',
                        borderRadius: '3px',
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
                            color: '#54595d',
                        }}
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Quality Checks Table */}
            <div style={{
                padding: '1rem',
                background: '#fff',
            }}>
                <h4 style={{ margin: '0 0 0.75rem 0', color: '#202122', fontFamily: 'sans-serif' }}>
                    Quality Checks
                </h4>
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontFamily: 'sans-serif',
                    fontSize: '14px',
                    border: '1px solid #a2a9b1',
                }}>
                    <thead>
                        <tr>
                            <th style={{
                                padding: '0.5em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '40%',
                            }}>
                                Criteria
                            </th>
                            <th style={{
                                padding: '0.5em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '60px',
                                textAlign: 'center',
                            }}>
                                Status
                            </th>
                            <th style={{
                                padding: '0.5em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                            }}>
                                Notes
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {checks.map((check, index) => (
                            <tr key={check.id || index}>
                                <td style={{
                                    padding: '0.5em',
                                    border: '1px solid #a2a9b1',
                                    backgroundColor: '#fff',
                                }}>
                                    {check.criteria}
                                </td>
                                <td style={{
                                    padding: '0.5em',
                                    border: '1px solid #a2a9b1',
                                    textAlign: 'center',
                                    backgroundColor: check.ai_review === true ? '#e6f9e6' :
                                        check.ai_review === false ? '#fee' : '#fff',
                                    fontSize: '1.2em',
                                }}>
                                    {check.ai_review === true ? (
                                        <span style={{ color: '#14866d' }}>✓</span>
                                    ) : check.ai_review === false ? (
                                        <span style={{ color: '#d33' }}>✗</span>
                                    ) : (
                                        <span style={{ color: '#54595d' }}>—</span>
                                    )}
                                </td>
                                <td style={{
                                    padding: '0.5em',
                                    border: '1px solid #a2a9b1',
                                    backgroundColor: '#fff',
                                    color: '#54595d',
                                }}>
                                    {check.ai_notes}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Translated Script Section */}
            {translatedScript && (
                <div style={{
                    padding: '1rem',
                    borderTop: '1px solid #eaecf0',
                    background: '#f8f9fa',
                }}>
                    <h4 style={{
                        margin: '0 0 0.75rem 0',
                        color: '#202122',
                        fontFamily: 'sans-serif',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <Globe size={18} />
                        Hindi Translation
                        {translatedScript.title_hindi && (
                            <span style={{
                                fontWeight: 'normal',
                                color: '#54595d',
                                fontSize: '0.9em',
                                marginLeft: '0.5rem'
                            }}>
                                — {translatedScript.title_hindi}
                            </span>
                        )}
                    </h4>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {translatedScript.slides?.map((slide) => (
                            <div
                                key={slide.slide_number}
                                style={{
                                    background: '#fff',
                                    borderRadius: '4px',
                                    border: '1px solid #a2a9b1',
                                    overflow: 'hidden',
                                }}
                            >
                                {/* Slide Header - Clickable */}
                                <div
                                    onClick={() => toggleSlide(slide.slide_number)}
                                    style={{
                                        padding: '0.75rem 1rem',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        cursor: 'pointer',
                                        background: expandedSlide === slide.slide_number ? '#eaecf0' : '#fff',
                                        borderBottom: expandedSlide === slide.slide_number ? '1px solid #a2a9b1' : 'none',
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <span style={{
                                            fontWeight: 600,
                                            color: '#36c',
                                            minWidth: '60px',
                                        }}>
                                            Row {slide.slide_number}
                                        </span>
                                        <span style={{
                                            fontSize: '0.85em',
                                            color: slide.timing_ok ? '#14866d' : '#d33',
                                            background: slide.timing_ok ? '#e6f9e6' : '#fee',
                                            padding: '0.15em 0.5em',
                                            borderRadius: '3px',
                                        }}>
                                            {slide.timing_ok ? '⏱️ OK' : '⏱️ Long'}
                                        </span>
                                    </div>
                                    {expandedSlide === slide.slide_number ?
                                        <ChevronUp size={18} style={{ color: '#54595d' }} /> :
                                        <ChevronDown size={18} style={{ color: '#54595d' }} />
                                    }
                                </div>

                                {/* Expanded Content */}
                                {expandedSlide === slide.slide_number && (
                                    <div style={{ padding: '1rem' }}>
                                        {/* Original English */}
                                        <div style={{ marginBottom: '1rem' }}>
                                            <label style={{
                                                display: 'block',
                                                fontSize: '0.75em',
                                                color: '#54595d',
                                                marginBottom: '0.25rem',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                            }}>
                                                Original (English)
                                            </label>
                                            <div style={{
                                                padding: '0.75rem',
                                                background: '#f8f9fa',
                                                borderRadius: '4px',
                                                border: '1px solid #eaecf0',
                                                fontFamily: 'sans-serif',
                                                fontSize: '0.9rem',
                                                lineHeight: '1.6',
                                            }}>
                                                {slide.narration_original}
                                            </div>
                                        </div>

                                        {/* Hindi Translation */}
                                        <div style={{ marginBottom: slide.issues?.length > 0 ? '1rem' : 0 }}>
                                            <label style={{
                                                display: 'block',
                                                fontSize: '0.75em',
                                                color: '#54595d',
                                                marginBottom: '0.25rem',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                            }}>
                                                Hindi Translation
                                            </label>
                                            <div style={{
                                                padding: '0.75rem',
                                                background: 'linear-gradient(135deg, #667eea10 0%, #764ba210 100%)',
                                                borderRadius: '4px',
                                                border: '1px solid #667eea30',
                                                fontFamily: 'Noto Sans Devanagari, sans-serif',
                                                fontSize: '1rem',
                                                lineHeight: '1.8',
                                            }}>
                                                {slide.narration}
                                            </div>
                                        </div>

                                        {/* Issues if any */}
                                        {slide.issues?.length > 0 && (
                                            <div>
                                                <label style={{
                                                    display: 'block',
                                                    fontSize: '0.75em',
                                                    color: '#d33',
                                                    marginBottom: '0.25rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.05em',
                                                }}>
                                                    Issues Found
                                                </label>
                                                <ul style={{
                                                    margin: 0,
                                                    padding: '0.5rem 0.5rem 0.5rem 1.5rem',
                                                    background: '#fee',
                                                    borderRadius: '4px',
                                                    fontSize: '0.85rem',
                                                }}>
                                                    {slide.issues.map((issue, i) => (
                                                        <li key={i} style={{ color: '#d33' }}>{issue}</li>
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
                padding: '0.75rem 1rem',
                background: '#f8f9fa',
                borderTop: '1px solid #eaecf0',
                fontSize: '0.85rem',
                color: '#54595d',
                fontFamily: 'sans-serif',
            }}>
                <strong>Tips:</strong> Click on any slide to see the English → Hindi translation.
                Quality scores range from 1-5 (5 = excellent translation).
            </div>
        </div>
    );
};

export default QualityReport;
