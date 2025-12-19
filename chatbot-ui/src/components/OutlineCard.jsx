import React, { useState } from 'react';
import { Download, FileText, Users, Target, BookOpen, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const OutlineCard = ({ outlineData, projectId }) => {
    const [isDownloadingPDF, setIsDownloadingPDF] = useState(false);
    const [isDownloadingDOCX, setIsDownloadingDOCX] = useState(false);

    if (!outlineData) return null;

    const handleDownloadPDF = async () => {
        setIsDownloadingPDF(true);
        try {
            const response = await fetch(`${API_URL}/outline_chat/${projectId}/export?format=pdf`);
            const data = await response.json();

            if (data.pdf_url) {
                window.open(`${API_URL}${data.pdf_url}`, '_blank');
            }
        } catch (error) {
            console.error('Failed to download PDF:', error);
        } finally {
            setIsDownloadingPDF(false);
        }
    };

    const handleDownloadDOCX = async () => {
        setIsDownloadingDOCX(true);
        try {
            const response = await fetch(`${API_URL}/outline_chat/${projectId}/export?format=docx`);
            const data = await response.json();

            if (data.docx_url) {
                window.open(`${API_URL}${data.docx_url}`, '_blank');
            }
        } catch (error) {
            console.error('Failed to download DOCX:', error);
        } finally {
            setIsDownloadingDOCX(false);
        }
    };

    const cardStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '1rem',
        padding: '1.5rem',
        marginTop: '1rem',
        border: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-md)',
    };

    const headerStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)',
    };

    const titleStyle = {
        fontSize: '1.25rem',
        fontWeight: 700,
        color: 'var(--text-primary)',
        margin: 0,
    };

    const sectionStyle = {
        marginBottom: '1.25rem',
    };

    const sectionTitleStyle = {
        fontSize: '0.85rem',
        fontWeight: 600,
        color: 'var(--text-secondary)',
        marginBottom: '0.5rem',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
    };

    const tableStyle = {
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '0.9rem',
    };

    const tdStyle = {
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid var(--border-color)',
        verticalAlign: 'top',
    };

    const labelStyle = {
        ...tdStyle,
        fontWeight: 600,
        color: 'var(--text-secondary)',
        width: '35%',
        background: 'var(--bg-tertiary)',
    };

    const valueStyle = {
        ...tdStyle,
        color: 'var(--text-primary)',
    };

    const tagStyle = {
        display: 'inline-block',
        background: 'var(--bg-tertiary)',
        padding: '0.25rem 0.5rem',
        borderRadius: '0.25rem',
        fontSize: '0.8rem',
        marginRight: '0.5rem',
        marginBottom: '0.25rem',
    };

    const buttonStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        background: 'var(--accent-primary)',
        color: 'var(--bg-primary)',
        border: 'none',
        borderRadius: '0.5rem',
        cursor: 'pointer',
        fontWeight: 600,
        fontSize: '0.875rem',
        transition: 'transform 0.2s',
    };

    return (
        <div style={cardStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <div>
                    <h3 style={titleStyle}>
                        📋 {outlineData.tutorial_name || 'Course Outline'}
                    </h3>
                    <p style={{ margin: '0.5rem 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        {outlineData.recommended_no_of_tutorials || 1} tutorial(s) •
                        Prepared by {outlineData.prepared_by || 'Unknown'}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        style={buttonStyle}
                        onClick={handleDownloadPDF}
                        disabled={isDownloadingPDF}
                        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                    >
                        {isDownloadingPDF ? (
                            <><Loader2 size={16} className="animate-spin" /> PDF...</>
                        ) : (
                            <><Download size={16} /> PDF</>
                        )}
                    </button>
                    <button
                        style={{ ...buttonStyle, background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
                        onClick={handleDownloadDOCX}
                        disabled={isDownloadingDOCX}
                        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                    >
                        {isDownloadingDOCX ? (
                            <><Loader2 size={16} className="animate-spin" /> DOCX...</>
                        ) : (
                            <><FileText size={16} /> DOCX</>
                        )}
                    </button>
                </div>
            </div>

            {/* Metadata Table */}
            <div style={sectionStyle}>
                <table style={tableStyle}>
                    <tbody>
                        <tr>
                            <td style={labelStyle}><Users size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} /> Target Audience</td>
                            <td style={valueStyle}>{outlineData.target_audience || '-'}</td>
                        </tr>
                        <tr>
                            <td style={labelStyle}><BookOpen size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} /> Entry Behaviour</td>
                            <td style={valueStyle}>{outlineData.entry_behaviour || '-'}</td>
                        </tr>
                        <tr>
                            <td style={labelStyle}><Target size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} /> Purpose</td>
                            <td style={valueStyle}>{outlineData.purpose || '-'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            {/* Course Objectives */}
            {outlineData.course_objectives?.length > 0 && (
                <div style={sectionStyle}>
                    <div style={sectionTitleStyle}>Course Objectives</div>
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-primary)' }}>
                        {outlineData.course_objectives.map((obj, i) => (
                            <li key={i} style={{ marginBottom: '0.35rem', fontSize: '0.9rem' }}>{obj}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Topics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                {outlineData.topics_included?.length > 0 && (
                    <div>
                        <div style={sectionTitleStyle}>
                            <CheckCircle size={14} style={{ marginRight: 6, color: '#22c55e', verticalAlign: 'middle' }} />
                            Topics Included
                        </div>
                        <div>
                            {outlineData.topics_included.map((topic, i) => (
                                <span key={i} style={{ ...tagStyle, borderLeft: '3px solid #22c55e' }}>{topic}</span>
                            ))}
                        </div>
                    </div>
                )}
                {outlineData.topics_not_included?.length > 0 && (
                    <div>
                        <div style={sectionTitleStyle}>
                            <XCircle size={14} style={{ marginRight: 6, color: '#ef4444', verticalAlign: 'middle' }} />
                            Topics Not Included
                        </div>
                        <div>
                            {outlineData.topics_not_included.map((topic, i) => (
                                <span key={i} style={{ ...tagStyle, borderLeft: '3px solid #ef4444' }}>{topic}</span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Core Example */}
            {outlineData.core_example && (
                <div style={sectionStyle}>
                    <div style={sectionTitleStyle}>🎯 Core Example</div>
                    <div style={{
                        background: 'var(--bg-tertiary)',
                        padding: '0.75rem 1rem',
                        borderRadius: '0.5rem',
                        fontSize: '0.9rem',
                        color: 'var(--text-primary)',
                        borderLeft: '3px solid var(--accent-primary)'
                    }}>
                        {outlineData.core_example}
                    </div>
                </div>
            )}

            {/* Tutorial Rows Table */}
            {outlineData.tutorial_rows?.length > 0 && (
                <div style={sectionStyle}>
                    <div style={sectionTitleStyle}>📚 Tutorial Structure</div>
                    <table style={{ ...tableStyle, fontSize: '0.85rem' }}>
                        <thead>
                            <tr style={{ background: 'var(--bg-tertiary)' }}>
                                <th style={{ ...tdStyle, fontWeight: 600, textAlign: 'left' }}>#</th>
                                <th style={{ ...tdStyle, fontWeight: 600, textAlign: 'left' }}>Title</th>
                                <th style={{ ...tdStyle, fontWeight: 600, textAlign: 'left' }}>Topics</th>
                                <th style={{ ...tdStyle, fontWeight: 600, textAlign: 'center', width: '80px' }}>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {outlineData.tutorial_rows.map((row, i) => (
                                <tr key={i}>
                                    <td style={valueStyle}>{row.tutorial_number || i + 1}</td>
                                    <td style={{ ...valueStyle, fontWeight: 500 }}>{row.title}</td>
                                    <td style={valueStyle}>
                                        {row.topics_details?.map((topic, j) => (
                                            <div key={j} style={{ marginBottom: '0.25rem' }}>• {topic}</div>
                                        ))}
                                    </td>
                                    <td style={{ ...valueStyle, textAlign: 'center' }}>
                                        {Math.floor((row.time_seconds || 0) / 60)}m
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Keywords */}
            {outlineData.keywords?.length > 0 && (
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginRight: '0.5rem' }}>Keywords:</span>
                    {outlineData.keywords.map((kw, i) => (
                        <span key={i} style={tagStyle}>{kw}</span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default OutlineCard;
