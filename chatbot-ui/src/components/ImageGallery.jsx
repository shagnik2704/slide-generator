import React, { useState } from 'react';
import { Image, Download, X, CheckCircle, XCircle, ExternalLink } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * ImageGallery - Display generated images in a grid.
 * 
 * Props:
 * - imageData: Result from /generate_images endpoint
 *   { images: [{slide_number, url, success, error}], zip_url, generated, failed }
 * - projectId: Project ID for reference
 * - onClose: Close the gallery
 */
const ImageGallery = ({ imageData, projectId, onClose }) => {
    const [selectedImage, setSelectedImage] = useState(null);

    const { images = [], zip_url, generated = 0, failed = 0 } = imageData || {};

    // Build full URL for images
    const getImageUrl = (url) => {
        if (!url) return null;
        if (url.startsWith('http')) return url;
        return `${API_URL}${url}`;
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
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
    };

    const gridStyle = {
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem'
    };

    const cardStyle = {
        display: 'flex',
        background: 'var(--bg-tertiary)',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid var(--border-color)',
        minHeight: '200px'
    };

    const imageSectionStyle = {
        width: '300px',
        minWidth: '300px',
        borderRight: '1px solid var(--border-color)',
        background: 'var(--bg-primary)',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
    };

    const infoSectionStyle = {
        padding: '1.25rem',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem'
    };

    const imageStyle = {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        cursor: 'pointer'
    };

    const buttonStyle = {
        padding: '0.5rem 1rem',
        borderRadius: '8px',
        border: 'none',
        cursor: 'pointer',
        fontSize: '0.85rem',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
    };

    const primaryButtonStyle = {
        ...buttonStyle,
        background: 'var(--accent-primary)',
        color: 'white'
    };

    const secondaryButtonStyle = {
        ...buttonStyle,
        background: 'var(--bg-tertiary)',
        color: 'var(--text-primary)'
    };

    // Modal for enlarged image
    const Modal = ({ image, onClose }) => (
        <div
            onClick={onClose}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.85)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                padding: '2rem'
            }}
        >
            <div
                onClick={e => e.stopPropagation()}
                style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    maxWidth: '90vw',
                    maxHeight: '90vh'
                }}
            >
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem',
                    borderBottom: '1px solid var(--border-color)'
                }}>
                    <span style={{ fontWeight: 600 }}>
                        Row {image.slide_number}
                    </span>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <a
                            href={getImageUrl(image.url)}
                            download={`slide_${image.slide_number}.png`}
                            style={{ ...secondaryButtonStyle, textDecoration: 'none' }}
                        >
                            <Download size={16} /> Download
                        </a>
                        <button onClick={onClose} style={secondaryButtonStyle}>
                            <X size={16} />
                        </button>
                    </div>
                </div>
                <img
                    src={getImageUrl(image.url)}
                    alt={`Slide ${image.slide_number}`}
                    style={{
                        display: 'block',
                        maxWidth: '100%',
                        maxHeight: 'calc(90vh - 80px)',
                        objectFit: 'contain'
                    }}
                />
            </div>
        </div>
    );

    return (
        <div style={containerStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Image size={24} style={{ color: 'var(--accent-primary)' }} />
                    <div>
                        <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>
                            Generated Images
                        </h3>
                        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            <span style={{ color: 'green' }}>{generated} successful</span>
                            {failed > 0 && (
                                <span style={{ color: 'red', marginLeft: '0.75rem' }}>
                                    {failed} failed
                                </span>
                            )}
                        </p>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {zip_url && (
                        <a
                            href={getImageUrl(zip_url)}
                            download
                            style={{ ...primaryButtonStyle, textDecoration: 'none' }}
                        >
                            <Download size={16} /> Download All (ZIP)
                        </a>
                    )}
                    {onClose && (
                        <button onClick={onClose} style={secondaryButtonStyle}>
                            Close
                        </button>
                    )}
                </div>
            </div>

            {/* List */}
            <div style={gridStyle}>
                {images.map((image) => (
                    <div key={image.slide_number} style={cardStyle}>
                        {/* Column 1: Image */}
                        <div style={imageSectionStyle}>
                            {image.success ? (
                                <img
                                    src={getImageUrl(image.url)}
                                    alt={`Slide ${image.slide_number}`}
                                    style={imageStyle}
                                    onClick={() => setSelectedImage(image)}
                                    loading="lazy"
                                />
                            ) : (
                                <div style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    color: 'var(--text-secondary)'
                                }}>
                                    <XCircle size={32} style={{ color: 'red' }} />
                                    <span style={{ fontSize: '0.75rem' }}>{image.error || 'Failed'}</span>
                                </div>
                            )}

                            {/* Overlay button for preview */}
                            {image.success && (
                                <div
                                    style={{
                                        position: 'absolute',
                                        bottom: '10px',
                                        right: '10px',
                                        background: 'rgba(0,0,0,0.6)',
                                        color: 'white',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '0.75rem',
                                        pointerEvents: 'none'
                                    }}
                                >
                                    Click to expand
                                </div>
                            )}
                        </div>

                        {/* Column 2: Prompt Info */}
                        <div style={infoSectionStyle}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h4 style={{ margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    Row {image.slide_number}
                                    {image.success ? (
                                        <CheckCircle size={16} style={{ color: 'green' }} />
                                    ) : (
                                        <XCircle size={16} style={{ color: 'red' }} />
                                    )}
                                </h4>
                                {image.success && (
                                    <a
                                        href={getImageUrl(image.url)}
                                        download={`slide_${image.slide_number}.png`}
                                        style={{ color: 'var(--text-secondary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem' }}
                                        title="Download Image"
                                    >
                                        <Download size={14} /> Download
                                    </a>
                                )}
                            </div>

                            <div style={{ flex: 1 }}>
                                <div style={{
                                    fontSize: '0.75rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    color: 'var(--text-secondary)',
                                    marginBottom: '0.35rem',
                                    fontWeight: 600
                                }}>
                                    Prompt Used
                                </div>
                                <div style={{
                                    color: 'var(--text-primary)',
                                    lineHeight: '1.6',
                                    fontSize: '0.95rem',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {image.prompt ? image.prompt : <span style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>No prompt information available</span>}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Empty state */}
            {images.length === 0 && (
                <div style={{
                    textAlign: 'center',
                    padding: '3rem',
                    color: 'var(--text-secondary)'
                }}>
                    No images generated yet.
                </div>
            )}

            {/* Modal */}
            {selectedImage && (
                <Modal image={selectedImage} onClose={() => setSelectedImage(null)} />
            )}
        </div>
    );
};

export default ImageGallery;
