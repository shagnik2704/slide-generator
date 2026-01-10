import React, { useState, useRef, useEffect } from 'react';
import { Image, Download, Loader2, Paperclip, XCircle, RefreshCw, AlertCircle, User, ChevronDown, ChevronUp } from 'lucide-react';
import Tooltip from './Tooltip';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Strip markdown formatting from text
 */
const stripMarkdown = (text) => {
    if (!text) return text;
    return text.replace(/\*\*/g, '').replace(/\*/g, '').replace(/__/g, '').replace(/~~/g, '').trim();
};

/**
 * Format text with line breaks after each sentence
 */
const formatSentences = (text) => {
    if (!text) return null;
    const sentences = text.split(/(?<=[.!?])\s+/);
    return sentences.map((sentence, i) => (
        <span key={i} style={{ display: 'block', marginBottom: i < sentences.length - 1 ? '0.5rem' : 0 }}>
            {sentence}
        </span>
    ));
};

/**
 * ImageWorkflow - Unified component for reviewing prompts AND displaying generated images.
 * Table-based grid layout matching TranslationResults style.
 */
const ImageWorkflow = ({ enhancedPrompts, projectId, onClose }) => {
    const STORAGE_KEY = `image_workflow_${projectId}`;

    // Initialize slides with prompt data and empty image slots
    const [slides, setSlides] = useState(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                return enhancedPrompts.map(p => {
                    const savedSlide = parsed.find(s => s.slide_number === p.slide_number);
                    return {
                        ...p,
                        selected: savedSlide?.selected ?? !p.skip_reason,
                        editedPrompt: savedSlide?.editedPrompt || p.enhanced || p.original,
                        isEditing: false,
                        referenceImage: null,
                        referenceImagePreview: null,
                        imageUrl: savedSlide?.imageUrl || null,
                        imageStatus: savedSlide?.imageUrl ? 'success' : 'pending',
                        imageError: null,
                    };
                });
            } catch (e) {
                console.warn('Failed to parse saved workflow:', e);
            }
        }
        return enhancedPrompts.map(p => ({
            ...p,
            selected: !p.skip_reason,
            editedPrompt: p.enhanced || p.original,
            isEditing: false,
            referenceImage: null,
            referenceImagePreview: null,
            imageUrl: null,
            imageStatus: 'pending',
            imageError: null,
        }));
    });

    const [isGeneratingAll, setIsGeneratingAll] = useState(false);
    const [isSelectionMode, setIsSelectionMode] = useState(false);
    const [isCharPanelOpen, setIsCharPanelOpen] = useState(false);
    const fileInputRefs = useRef({});
    const charRefInputRef = useRef(null);

    // Global character reference state
    const CHAR_REF_KEY = `char_ref_${projectId}`;
    const [globalCharRef, setGlobalCharRef] = useState(() => {
        const saved = localStorage.getItem(CHAR_REF_KEY);
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                console.warn('Failed to parse saved char ref:', e);
            }
        }
        return {
            imageUrl: null,
            imagePath: null,
            description: '',
            enabled: false
        };
    });

    // Save character reference to localStorage
    useEffect(() => {
        localStorage.setItem(CHAR_REF_KEY, JSON.stringify(globalCharRef));
    }, [globalCharRef, CHAR_REF_KEY]);

    // Save to localStorage on change
    useEffect(() => {
        const toSave = slides.map(s => ({
            slide_number: s.slide_number,
            selected: s.selected,
            editedPrompt: s.editedPrompt,
            imageUrl: s.imageUrl,
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    }, [slides, STORAGE_KEY]);

    const selectedCount = slides.filter(s => s.selected && !s.skip_reason).length;
    const generatedCount = slides.filter(s => s.imageStatus === 'success').length;
    const totalGeneratable = slides.filter(s => !s.skip_reason).length;

    // Toggle selection
    const toggleSelection = (slideNumber) => {
        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber ? { ...s, selected: !s.selected } : s
        ));
    };

    // Editing functions
    const startEditing = (slideNumber) => {
        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber ? { ...s, isEditing: true } : s
        ));
    };

    const saveEdit = (slideNumber, newPrompt) => {
        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber ? { ...s, editedPrompt: newPrompt, isEditing: false } : s
        ));
    };

    const cancelEdit = (slideNumber) => {
        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber ? { ...s, isEditing: false } : s
        ));
    };

    // Reference image handling
    const handleReferenceImageSelect = (slideNumber, file) => {
        if (!file) return;
        const reader = new FileReader();
        reader.onloadend = () => {
            setSlides(prev => prev.map(s =>
                s.slide_number === slideNumber
                    ? { ...s, referenceImage: file, referenceImagePreview: reader.result }
                    : s
            ));
        };
        reader.readAsDataURL(file);
    };

    const removeReferenceImage = (slideNumber) => {
        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber
                ? { ...s, referenceImage: null, referenceImagePreview: null }
                : s
        ));
    };

    // Generate single image
    const generateSingleImage = async (slideNumber) => {
        const slide = slides.find(s => s.slide_number === slideNumber);
        if (!slide) return;

        setSlides(prev => prev.map(s =>
            s.slide_number === slideNumber ? { ...s, imageStatus: 'generating', imageError: null } : s
        ));

        try {
            let referenceImagePath = null;
            if (slide.referenceImage) {
                const formData = new FormData();
                formData.append('file', slide.referenceImage);
                formData.append('project_id', projectId);
                formData.append('slide_number', slideNumber);
                const refRes = await fetch(`${API_URL}/upload_reference_image`, {
                    method: 'POST',
                    body: formData
                });
                if (refRes.ok) {
                    const refData = await refRes.json();
                    referenceImagePath = refData.path;
                }
            }

            const response = await fetch(`${API_URL}/generate_images`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    prompts: [{
                        slide_number: slideNumber,
                        prompt: globalCharRef.enabled && globalCharRef.description
                            ? `${globalCharRef.description}\n\n${slide.editedPrompt}`
                            : slide.editedPrompt,
                        reference_image_path: globalCharRef.enabled && globalCharRef.imagePath
                            ? globalCharRef.imagePath
                            : referenceImagePath
                    }],
                    aspect_ratio: '16:9'
                })
            });

            const result = await response.json();
            const generatedImage = result.images?.find(img => img.slide_number === slideNumber);

            if (generatedImage?.success) {
                setSlides(prev => prev.map(s =>
                    s.slide_number === slideNumber
                        ? { ...s, imageUrl: generatedImage.url, imageStatus: 'success', imageError: null }
                        : s
                ));
            } else {
                setSlides(prev => prev.map(s =>
                    s.slide_number === slideNumber
                        ? { ...s, imageStatus: 'error', imageError: generatedImage?.error || 'Generation failed' }
                        : s
                ));
            }
        } catch (error) {
            setSlides(prev => prev.map(s =>
                s.slide_number === slideNumber
                    ? { ...s, imageStatus: 'error', imageError: error.message }
                    : s
            ));
        }
    };

    // Generate all selected images
    const generateAllSelected = async () => {
        const selectedSlides = slides.filter(s => s.selected && !s.skip_reason);
        if (selectedSlides.length === 0) return;

        setIsGeneratingAll(true);
        setSlides(prev => prev.map(s =>
            s.selected && !s.skip_reason
                ? { ...s, imageStatus: 'generating', imageError: null }
                : s
        ));

        try {
            const promptsWithRefs = await Promise.all(selectedSlides.map(async (slide) => {
                let referenceImagePath = null;
                if (slide.referenceImage) {
                    const formData = new FormData();
                    formData.append('file', slide.referenceImage);
                    formData.append('project_id', projectId);
                    formData.append('slide_number', slide.slide_number);
                    const refRes = await fetch(`${API_URL}/upload_reference_image`, {
                        method: 'POST',
                        body: formData
                    });
                    if (refRes.ok) {
                        const refData = await refRes.json();
                        referenceImagePath = refData.path;
                    }
                }
                return {
                    slide_number: slide.slide_number,
                    prompt: slide.editedPrompt,
                    reference_image_path: referenceImagePath
                };
            }));

            const response = await fetch(`${API_URL}/generate_images`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    prompts: promptsWithRefs,
                    aspect_ratio: '16:9'
                })
            });

            const result = await response.json();
            setSlides(prev => prev.map(s => {
                const generated = result.images?.find(img => img.slide_number === s.slide_number);
                if (!generated) return s;
                return {
                    ...s,
                    imageUrl: generated.success ? generated.url : s.imageUrl,
                    imageStatus: generated.success ? 'success' : 'error',
                    imageError: generated.success ? null : generated.error
                };
            }));
        } catch (error) {
            setSlides(prev => prev.map(s =>
                s.selected && !s.skip_reason
                    ? { ...s, imageStatus: 'error', imageError: error.message }
                    : s
            ));
        } finally {
            setIsGeneratingAll(false);
        }
    };

    const getImageUrl = (url) => {
        if (!url) return null;
        if (url.startsWith('http')) return url;
        return `${API_URL}${url}`;
    };

    // Styles matching TranslationResults
    const containerStyle = {
        background: 'var(--bg-tertiary)',
        borderRadius: '12px',
        border: '1px solid var(--border-primary)',
        overflow: 'hidden',
        marginTop: '1rem',
        position: 'relative',
        width: 'calc(100vw - 180px)',
        maxWidth: '1200px',
        left: '50%',
        transform: 'translateX(-50%)',
    };

    const headerStyle = {
        padding: '1rem 1.25rem',
        borderBottom: '1px solid var(--border-primary)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
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
        padding: '1.5rem 1rem',
        borderBottom: '1px solid var(--border-primary)',
        verticalAlign: 'top',
        lineHeight: 1.8,
        minHeight: '120px',
    };

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

    const primaryButtonStyle = {
        ...buttonStyle,
        background: 'var(--accent-primary)',
        border: 'none',
        color: 'white',
    };

    return (
        <div style={containerStyle}>
            {/* Header */}
            <div style={headerStyle}>
                <Image size={22} style={{ color: 'var(--accent-primary)' }} />
                <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '1rem' }}>Image Workflow</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {generatedCount}/{totalGeneratable} generated
                        {isSelectionMode && ` • ${selectedCount} selected`}
                    </div>
                </div>

                {!isSelectionMode ? (
                    /* Normal Mode - just Select button */
                    <button
                        onClick={() => setIsSelectionMode(true)}
                        style={primaryButtonStyle}
                    >
                        Select
                    </button>
                ) : (
                    /* Selection Mode - bulk actions */
                    <>
                        <button
                            onClick={() => setSlides(prev => prev.map(s => ({ ...s, selected: !s.skip_reason })))}
                            style={buttonStyle}
                        >
                            Select All
                        </button>
                        <button
                            onClick={() => setSlides(prev => prev.map(s => ({ ...s, selected: false })))}
                            style={buttonStyle}
                        >
                            Deselect All
                        </button>
                        <button
                            onClick={generateAllSelected}
                            disabled={selectedCount === 0 || isGeneratingAll}
                            style={{
                                ...primaryButtonStyle,
                                opacity: selectedCount === 0 || isGeneratingAll ? 0.5 : 1
                            }}
                        >
                            {isGeneratingAll ? <Loader2 size={16} className="spin" /> : <Image size={16} />}
                            Generate {selectedCount}
                        </button>
                        <button
                            onClick={() => setIsSelectionMode(false)}
                            style={{ ...buttonStyle, padding: '0.5rem' }}
                            title="Exit selection mode"
                        >
                            ✕
                        </button>
                    </>
                )}
            </div>

            {/* Character Reference Panel */}
            <div style={{
                padding: '0.75rem 1.25rem',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-primary)',
            }}>
                <div
                    style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
                    onClick={() => setIsCharPanelOpen(!isCharPanelOpen)}
                >
                    <User size={18} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 500, flex: 1 }}>
                        Character Reference
                        {globalCharRef.enabled && <span style={{ color: 'var(--accent-primary)', marginLeft: '0.5rem' }}>• Active</span>}
                    </span>
                    {isCharPanelOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>

                {isCharPanelOpen && (
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '1.5rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                        {/* Reference Image */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {globalCharRef.imageUrl ? (
                                <div style={{ position: 'relative' }}>
                                    <img
                                        src={globalCharRef.imageUrl}
                                        alt="Character reference"
                                        style={{ width: 80, height: 80, borderRadius: '8px', objectFit: 'cover' }}
                                    />
                                    <button
                                        onClick={() => setGlobalCharRef(prev => ({ ...prev, imageUrl: null, imagePath: null }))}
                                        style={{ position: 'absolute', top: -8, right: -8, background: 'var(--bg-primary)', borderRadius: '50%', border: 'none', cursor: 'pointer', padding: '2px' }}
                                    >
                                        <XCircle size={16} />
                                    </button>
                                </div>
                            ) : (
                                <button
                                    onClick={() => charRefInputRef.current?.click()}
                                    style={{ ...buttonStyle, width: 80, height: 80, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}
                                >
                                    <Paperclip size={20} />
                                    <span style={{ fontSize: '0.7rem' }}>Upload</span>
                                </button>
                            )}
                            <input
                                ref={charRefInputRef}
                                type="file"
                                accept="image/*"
                                style={{ display: 'none' }}
                                onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;

                                    // Upload to server
                                    const formData = new FormData();
                                    formData.append('file', file);
                                    formData.append('project_id', projectId);
                                    formData.append('slide_number', 0);

                                    try {
                                        const res = await fetch(`${API_URL}/upload_reference_image`, {
                                            method: 'POST',
                                            body: formData
                                        });
                                        if (res.ok) {
                                            const data = await res.json();
                                            setGlobalCharRef(prev => ({
                                                ...prev,
                                                imageUrl: URL.createObjectURL(file),
                                                imagePath: data.path,
                                                enabled: true
                                            }));
                                        }
                                    } catch (err) {
                                        console.error('Failed to upload character ref:', err);
                                    }
                                }}
                            />
                        </div>

                        {/* Description */}
                        <div style={{ flex: 1, minWidth: '200px' }}>
                            <textarea
                                placeholder="Describe the character (e.g., 'Indian woman in her 30s, wearing a blue saree, warm smile')..."
                                value={globalCharRef.description}
                                onChange={(e) => setGlobalCharRef(prev => ({ ...prev, description: e.target.value }))}
                                style={{
                                    width: '100%',
                                    minHeight: '60px',
                                    padding: '0.5rem',
                                    borderRadius: '6px',
                                    border: '1px solid var(--border-primary)',
                                    background: 'var(--bg-primary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.85rem',
                                    fontFamily: 'inherit',
                                    resize: 'vertical'
                                }}
                            />
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={globalCharRef.enabled}
                                    onChange={(e) => setGlobalCharRef(prev => ({ ...prev, enabled: e.target.checked }))}
                                    style={{ width: 16, height: 16 }}
                                />
                                <span style={{ fontSize: '0.85rem' }}>Apply to all images</span>
                            </label>
                        </div>

                        {/* Use generated image */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Use generated image:</span>
                            <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                {slides.filter(s => s.imageUrl && s.imageStatus === 'success').slice(0, 5).map(s => (
                                    <button
                                        key={s.slide_number}
                                        onClick={() => setGlobalCharRef(prev => ({
                                            ...prev,
                                            imageUrl: getImageUrl(s.imageUrl),
                                            imagePath: s.imageUrl,
                                            enabled: true
                                        }))}
                                        style={{ ...buttonStyle, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                    >
                                        Row {s.slide_number}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Table Grid */}
            <div style={{ overflowX: 'auto' }}>
                <table style={tableStyle}>
                    <thead>
                        <tr>
                            {isSelectionMode && (
                                <th style={{ ...thStyle, width: '40px', textAlign: 'center' }}></th>
                            )}
                            <th style={{ ...thStyle, width: '40px', textAlign: 'center' }}>#</th>
                            <th style={{ ...thStyle, width: '15%' }}>Visual Cue</th>
                            <th style={{ ...thStyle, width: '22%' }}>Narration</th>
                            <th style={{ ...thStyle, width: '25%' }}>Image Prompt</th>
                            <th style={{ ...thStyle, width: '160px', textAlign: 'center' }}>Generated Image</th>
                        </tr>
                    </thead>
                    <tbody>
                        {slides.map((slide, i) => (
                            <tr
                                key={slide.slide_number}
                                style={{
                                    background: i % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                                    opacity: slide.skip_reason ? 0.5 : 1,
                                }}
                            >
                                {/* Checkbox - only in selection mode */}
                                {isSelectionMode && (
                                    <td style={{ ...tdStyle, textAlign: 'center', verticalAlign: 'middle' }}>
                                        <input
                                            type="checkbox"
                                            checked={slide.selected}
                                            onChange={() => toggleSelection(slide.slide_number)}
                                            disabled={!!slide.skip_reason}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                    </td>
                                )}

                                {/* Slide Number */}
                                <td style={{ ...tdStyle, fontWeight: 600, textAlign: 'center', verticalAlign: 'middle' }}>
                                    {slide.slide_number}
                                </td>

                                {/* Visual Cue (Original) */}
                                <td style={{ ...tdStyle, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                    {slide.skip_reason ? (
                                        <span style={{ fontStyle: 'italic' }}>{slide.skip_reason}</span>
                                    ) : (
                                        stripMarkdown(slide.original) || '—'
                                    )}
                                </td>

                                {/* Narration */}
                                <td style={{ ...tdStyle, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                    {slide.skip_reason ? (
                                        <span style={{ fontStyle: 'italic' }}>—</span>
                                    ) : (
                                        formatSentences(stripMarkdown(slide.narration)) || '—'
                                    )}
                                </td>

                                {/* Image Prompt (Editable) */}
                                <td style={tdStyle}>
                                    {slide.skip_reason ? (
                                        <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>—</span>
                                    ) : slide.isEditing ? (
                                        <textarea
                                            autoFocus
                                            value={slide.editedPrompt}
                                            onChange={(e) => setSlides(prev => prev.map(s =>
                                                s.slide_number === slide.slide_number ? { ...s, editedPrompt: e.target.value } : s
                                            ))}
                                            onBlur={() => saveEdit(slide.slide_number, slide.editedPrompt)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Escape') cancelEdit(slide.slide_number);
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault();
                                                    saveEdit(slide.slide_number, slide.editedPrompt);
                                                }
                                            }}
                                            style={{
                                                width: '100%',
                                                padding: '0.5rem',
                                                borderRadius: '6px',
                                                border: '2px solid var(--accent-primary)',
                                                background: 'transparent',
                                                color: 'var(--text-primary)',
                                                resize: 'vertical',
                                                minHeight: '100px',
                                                fontSize: '0.9rem',
                                                lineHeight: '1.6',
                                                fontFamily: 'inherit',
                                                outline: 'none'
                                            }}
                                        />
                                    ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            <div
                                                onClick={() => startEditing(slide.slide_number)}
                                                style={{
                                                    padding: '0.5rem',
                                                    borderRadius: '6px',
                                                    border: '2px solid transparent',
                                                    cursor: 'pointer',
                                                    color: 'var(--accent-primary)',
                                                    transition: 'border-color 0.2s'
                                                }}
                                                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
                                                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                                            >
                                                {formatSentences(slide.editedPrompt)}
                                            </div>
                                            {/* Reference Image */}
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <input
                                                    type="file"
                                                    accept="image/*"
                                                    ref={el => fileInputRefs.current[slide.slide_number] = el}
                                                    style={{ display: 'none' }}
                                                    onChange={(e) => handleReferenceImageSelect(slide.slide_number, e.target.files[0])}
                                                />
                                                {slide.referenceImagePreview ? (
                                                    <>
                                                        <img
                                                            src={slide.referenceImagePreview}
                                                            alt="Reference"
                                                            style={{ width: '32px', height: '32px', objectFit: 'cover', borderRadius: '4px' }}
                                                        />
                                                        <button
                                                            onClick={() => removeReferenceImage(slide.slide_number)}
                                                            style={{ ...buttonStyle, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                                        >
                                                            <XCircle size={12} />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button
                                                        onClick={() => fileInputRefs.current[slide.slide_number]?.click()}
                                                        style={{ ...buttonStyle, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                                    >
                                                        <Paperclip size={12} /> Add Reference Image
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </td>

                                {/* Generated Image */}
                                <td style={{ ...tdStyle, textAlign: 'center', verticalAlign: 'middle' }}>
                                    {slide.skip_reason ? (
                                        <span style={{ color: 'var(--text-secondary)' }}>—</span>
                                    ) : slide.imageStatus === 'pending' ? (
                                        <button onClick={() => generateSingleImage(slide.slide_number)} style={primaryButtonStyle}>
                                            <Image size={14} /> Generate
                                        </button>
                                    ) : slide.imageStatus === 'generating' ? (
                                        <div style={{ color: 'var(--text-secondary)' }}>
                                            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
                                            <p style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>Generating...</p>
                                        </div>
                                    ) : slide.imageStatus === 'success' && slide.imageUrl ? (
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                                            <img
                                                src={getImageUrl(slide.imageUrl)}
                                                alt={`Row ${slide.slide_number}`}
                                                style={{ maxWidth: '160px', maxHeight: '120px', borderRadius: '6px' }}
                                            />
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                <Tooltip text="Regenerate" position="bottom">
                                                    <button
                                                        onClick={() => generateSingleImage(slide.slide_number)}
                                                        style={{ ...buttonStyle, padding: '0.4rem 0.5rem', fontSize: '0.8rem' }}
                                                    >
                                                        <RefreshCw size={16} />
                                                    </button>
                                                </Tooltip>
                                                <Tooltip text="Download" position="bottom">
                                                    <a
                                                        href={`${API_URL}/download/image/${projectId}/slide_${slide.slide_number}.png`}
                                                        style={{ ...buttonStyle, padding: '0.4rem 0.5rem', fontSize: '0.8rem', textDecoration: 'none' }}
                                                    >
                                                        <Download size={16} />
                                                    </a>
                                                </Tooltip>
                                            </div>
                                        </div>
                                    ) : slide.imageStatus === 'error' ? (
                                        <div style={{ color: '#ef4444' }}>
                                            <AlertCircle size={20} />
                                            <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{slide.imageError}</p>
                                            <button
                                                onClick={() => generateSingleImage(slide.slide_number)}
                                                style={{ ...buttonStyle, padding: '0.25rem 0.5rem', fontSize: '0.75rem', marginTop: '0.25rem' }}
                                            >
                                                <RefreshCw size={12} /> Retry
                                            </button>
                                        </div>
                                    ) : null}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* CSS for spin animation */}
            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .spin { animation: spin 1s linear infinite; }
            `}</style>
        </div>
    );
};

export default ImageWorkflow;
