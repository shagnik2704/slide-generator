import React from 'react';
import { Download, FileText, CheckCircle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * SlidesPreview - Display generated Beamer LaTeX template with download option.
 * 
 * Props:
 * - slidesData: Result from /generate_slides endpoint
 *   { tex_content, filename, num_boilerplate_slides, num_content_slides, total_slides }
 */
const SlidesPreview = ({ slidesData }) => {
    const {
        tex_content = '',
        filename = 'slides.tex',
        zip_filename = 'slides.zip',
        zip_url = '',
        num_boilerplate_slides = 0,
        num_content_slides = 0,
        total_slides = 0
    } = slidesData || {};

    const handleDownload = () => {
        if (zip_url) {
            // Download ZIP from server
            const a = document.createElement('a');
            a.href = `${API_URL}${zip_url}`;
            a.download = zip_filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            // Fallback to tex-only download
            const blob = new Blob([tex_content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    };

    // Styles
    const containerStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '12px',
        border: '1px solid var(--border-color)',
        padding: '1.5rem',
        marginTop: '1rem'
    };

    const headerStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
    };

    const buttonStyle = {
        padding: '0.6rem 1.25rem',
        borderRadius: '8px',
        border: 'none',
        cursor: 'pointer',
        fontSize: '0.9rem',
        fontWeight: 600,
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: 'var(--accent-primary)',
        color: 'white',
        boxShadow: 'var(--shadow-sm)'
    };

    const statsStyle = {
        display: 'flex',
        gap: '1.5rem',
        marginTop: '1rem'
    };

    const statItemStyle = {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '1rem 1.5rem',
        background: 'var(--bg-tertiary)',
        borderRadius: '8px',
        flex: 1
    };

    const statNumberStyle = {
        fontSize: '1.75rem',
        fontWeight: 700,
        color: 'var(--text-primary)'
    };

    const statLabelStyle = {
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
        marginTop: '0.25rem'
    };

    return (
        <div style={containerStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <FileText size={24} style={{ color: 'var(--accent-primary)' }} />
                    <div>
                        <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>
                            Beamer Slides Template
                        </h3>
                        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            <CheckCircle size={14} style={{ color: 'green', marginRight: '0.35rem' }} />
                            Ready for download
                        </p>
                    </div>
                </div>
                <button
                    onClick={handleDownload}
                    style={buttonStyle}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                    }}
                >
                    <Download size={18} />
                    Download .zip
                </button>
            </div>

            {/* Stats */}
            <div style={statsStyle}>
                <div style={statItemStyle}>
                    <span style={statNumberStyle}>{total_slides}</span>
                    <span style={statLabelStyle}>Total Slides</span>
                </div>
                <div style={statItemStyle}>
                    <span style={statNumberStyle}>{num_boilerplate_slides}</span>
                    <span style={statLabelStyle}>Boilerplate</span>
                </div>
                <div style={statItemStyle}>
                    <span style={statNumberStyle}>{num_content_slides}</span>
                    <span style={statLabelStyle}>Blank Content</span>
                </div>
            </div>

            {/* Instructions */}
            <div style={{
                marginTop: '1.25rem',
                padding: '1rem',
                background: 'var(--bg-tertiary)',
                borderRadius: '8px',
                fontSize: '0.85rem',
                color: 'var(--text-secondary)'
            }}>
                <strong style={{ color: 'var(--text-primary)' }}>Next steps:</strong>
                <ol style={{ margin: '0.5rem 0 0 1rem', padding: 0, lineHeight: 1.6 }}>
                    <li>Download the <code>.zip</code> file (includes logo)</li>
                    <li>Upload to <a href="https://overleaf.com" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-primary)' }}>Overleaf</a> or extract locally</li>
                    <li>Edit your content slides</li>
                    <li>Compile to generate the final PDF</li>
                </ol>
            </div>

            {/* Filename */}
            <div style={{
                marginTop: '1rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
                textAlign: 'center'
            }}>
                📦 {zip_filename || filename}
            </div>
        </div>
    );
};

export default SlidesPreview;
