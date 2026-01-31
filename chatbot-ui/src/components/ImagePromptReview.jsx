import React, { useState, useRef, useEffect } from 'react';
import { Check, X, Edit2, Image, Loader2, Paperclip, XCircle } from 'lucide-react';
import { apiJson, apiFormData } from '../services/api';

/**
 * Strip markdown formatting from text (bold, italic, etc.)
 */
const stripMarkdown = (text) => {
    if (!text) return text;
    let result = text.replace(/\*\*/g, '');
    result = result.replace(/\*/g, '');
    result = result.replace(/__/g, '');
    result = result.replace(/~~/g, '');
    return result.trim();
};

/**
 * Format text with line breaks after each sentence for better readability
 */
const formatSentences = (text) => {
    if (!text) return null;
    // Split on sentence-ending punctuation followed by space
    const sentences = text.split(/(?<=[.!?])\s+/);
    return sentences.map((sentence, i) => (
        <span key={i} style={{ display: 'block', marginBottom: i < sentences.length - 1 ? '0.35rem' : 0 }}>
            {sentence}
        </span>
    ));
};

/**
 * ImagePromptReview - Review and edit AI-enhanced image prompts before generation.
 */
const ImagePromptReview = ({ enhancedPrompts, projectId, onGenerateComplete, onClose }) => {
    const STORAGE_KEY = `image_prompts_${projectId}`;

    // Load from localStorage if available, otherwise use props
    const [prompts, setPrompts] = useState(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                // Merge saved edits with fresh data (in case structure changed)
                return enhancedPrompts.map(p => {
                    const savedPrompt = parsed.find(s => s.slide_number === p.slide_number);
                    return {
                        ...p,
                        selected: savedPrompt?.selected ?? !p.skip_reason,
                        editedPrompt: savedPrompt?.editedPrompt || p.enhanced || p.original,
                        isEditing: false,
                        referenceImage: null,
                        referenceImagePreview: null
                    };
                });
            } catch (e) {
                console.warn('Failed to parse saved prompts:', e);
            }
        }
        // Default: fresh from props
        return enhancedPrompts.map(p => ({
            ...p,
            selected: !p.skip_reason,
            editedPrompt: p.enhanced || p.original,
            isEditing: false,
            referenceImage: null,
            referenceImagePreview: null
        }));
    });

    const [isGenerating, setIsGenerating] = useState(false);
    const [generationProgress, setGenerationProgress] = useState(null);

    // Save to localStorage whenever prompts change
    useEffect(() => {
        const toSave = prompts.map(p => ({
            slide_number: p.slide_number,
            selected: p.selected,
            editedPrompt: p.editedPrompt
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    }, [prompts, STORAGE_KEY]);

    // Refs for hidden file inputs (one per slide)
    const fileInputRefs = useRef({});

    const selectedCount = prompts.filter(p => p.selected && !p.skip_reason).length;
    const totalGeneratable = prompts.filter(p => !p.skip_reason).length;

    const toggleSelection = (slideNumber) => {
        setPrompts(prev => prev.map(p =>
            p.slide_number === slideNumber ? { ...p, selected: !p.selected } : p
        ));
    };

    const startEditing = (slideNumber) => {
        setPrompts(prev => prev.map(p =>
            p.slide_number === slideNumber ? { ...p, isEditing: true } : p
        ));
    };

    const saveEdit = (slideNumber, newPrompt) => {
        setPrompts(prev => prev.map(p =>
            p.slide_number === slideNumber ? { ...p, editedPrompt: newPrompt, isEditing: false } : p
        ));
    };

    const cancelEdit = (slideNumber) => {
        setPrompts(prev => prev.map(p =>
            p.slide_number === slideNumber ? { ...p, isEditing: false, editedPrompt: p.enhanced || p.original } : p
        ));
    };

    const selectAll = () => setPrompts(prev => prev.map(p => ({ ...p, selected: !p.skip_reason })));
    const deselectAll = () => setPrompts(prev => prev.map(p => ({ ...p, selected: false })));

    // Handle reference image selection
    const handleReferenceImageSelect = (slideNumber, file) => {
        if (file) {
            const previewUrl = URL.createObjectURL(file);
            setPrompts(prev => prev.map(p =>
                p.slide_number === slideNumber
                    ? { ...p, referenceImage: file, referenceImagePreview: previewUrl }
                    : p
            ));
        }
    };

    const removeReferenceImage = (slideNumber) => {
        setPrompts(prev => prev.map(p => {
            if (p.slide_number === slideNumber && p.referenceImagePreview) {
                URL.revokeObjectURL(p.referenceImagePreview);
            }
            return p.slide_number === slideNumber
                ? { ...p, referenceImage: null, referenceImagePreview: null }
                : p;
        }));
    };

    const handleGenerate = async () => {
        const selectedPromptsData = prompts
            .filter(p => p.selected && !p.skip_reason);

        if (selectedPromptsData.length === 0) {
            alert('Please select at least one prompt to generate.');
            return;
        }

        setIsGenerating(true);
        setGenerationProgress(`Preparing images...`);

        try {
            // First, upload any reference images
            const promptsWithRefs = [];
            for (const p of selectedPromptsData) {
                let referencePath = null;

                if (p.referenceImage) {
                    const formData = new FormData();
                    formData.append('file', p.referenceImage);
                    formData.append('project_id', projectId);
                    formData.append('slide_number', p.slide_number);

                    const uploadData = await apiFormData('/upload_reference_image', formData);
                    referencePath = uploadData.path;
                }

                promptsWithRefs.push({
                    slide_number: p.slide_number,
                    prompt: p.editedPrompt,
                    reference_image_path: referencePath
                });
            }

            setGenerationProgress(`Generating ${promptsWithRefs.length} images...`);

            const result = await apiJson('/generate_images', {
                method: 'POST',
                body: JSON.stringify({ project_id: projectId, prompts: promptsWithRefs, aspect_ratio: '1:1' })
            });

            // Enrich result with the prompts used
            const enrichedImages = result.images ? result.images.map(img => {
                const originalPrompt = promptsWithRefs.find(p => p.slide_number === img.slide_number);
                return {
                    ...img,
                    prompt: originalPrompt ? originalPrompt.prompt : ''
                };
            }) : [];

            const enrichedResult = {
                ...result,
                images: enrichedImages
            };

            setGenerationProgress(`Generated ${result.generated}/${promptsWithRefs.length} images!`);
            if (onGenerateComplete) onGenerateComplete(enrichedResult);
        } catch (error) {
            console.error('Image generation error:', error);
            setGenerationProgress(`Error: ${error.message}`);
        } finally {
            setIsGenerating(false);
        }
    };

    // Styles
    const containerStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '12px',
        border: '1px solid var(--border-color)',
        padding: '1.5rem',
        marginTop: '1rem',
        minWidth: '900px'
    };

    const headerStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
    };

    const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' };
    const thStyle = { textAlign: 'left', padding: '0.75rem', borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontWeight: 600 };
    const tdStyle = { padding: '0.75rem', borderBottom: '1px solid var(--border-color)', verticalAlign: 'top' };
    const buttonStyle = { padding: '0.5rem 1rem', borderRadius: '8px', border: 'none', cursor: 'pointer', fontSize: '0.85rem', transition: 'all 0.2s ease' };
    const primaryButtonStyle = { ...buttonStyle, background: 'var(--accent-primary)', color: 'white' };
    const secondaryButtonStyle = { ...buttonStyle, background: 'var(--bg-tertiary)', color: 'var(--text-primary)' };
    const checkboxStyle = { width: '18px', height: '18px', cursor: 'pointer' };
    const skippedRowStyle = { opacity: 0.5, background: 'var(--bg-tertiary)' };
    const iconButtonStyle = { background: 'none', border: 'none', cursor: 'pointer', padding: '4px', borderRadius: '4px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' };

    return (
        <div style={containerStyle}>
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Image size={24} style={{ color: 'var(--accent-primary)' }} />
                    <div>
                        <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Review Image Prompts</h3>
                        <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            {selectedCount} of {totalGeneratable} prompts selected
                        </p>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={selectAll} style={secondaryButtonStyle}>Select All</button>
                    <button onClick={deselectAll} style={secondaryButtonStyle}>Deselect All</button>
                </div>
            </div>

            <table style={tableStyle}>
                <thead>
                    <tr>
                        <th style={{ ...thStyle, minWidth: '40px' }}></th>
                        <th style={{ ...thStyle, minWidth: '40px' }}>#</th>
                        <th style={thStyle}>Visual Cue</th>
                        <th style={thStyle}>Narration</th>
                        <th style={thStyle}>AI Enhanced Prompt</th>
                        <th style={{ ...thStyle, minWidth: '80px' }}>Add Image</th>
                    </tr>
                </thead>
                <tbody>
                    {prompts.map((prompt) => (
                        <tr key={prompt.slide_number} style={prompt.skip_reason ? skippedRowStyle : {}}>
                            <td style={tdStyle}>
                                <input
                                    type="checkbox"
                                    checked={prompt.selected}
                                    onChange={() => toggleSelection(prompt.slide_number)}
                                    disabled={!!prompt.skip_reason}
                                    style={checkboxStyle}
                                />
                            </td>
                            <td style={tdStyle}>{prompt.slide_number}</td>
                            <td style={{ ...tdStyle, color: 'var(--text-secondary)' }}>{formatSentences(stripMarkdown(prompt.original)) || '—'}</td>
                            <td style={{ ...tdStyle, fontSize: '0.85rem', lineHeight: 1.6 }}>{formatSentences(stripMarkdown(prompt.narration)) || '—'}</td>
                            <td style={tdStyle}>
                                {prompt.skip_reason ? (
                                    <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>{prompt.skip_reason}</span>
                                ) : prompt.isEditing ? (
                                    <textarea
                                        autoFocus
                                        value={prompt.editedPrompt}
                                        onChange={(e) => setPrompts(prev => prev.map(p =>
                                            p.slide_number === prompt.slide_number ? { ...p, editedPrompt: e.target.value } : p
                                        ))}
                                        onBlur={() => saveEdit(prompt.slide_number, prompt.editedPrompt)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Escape') cancelEdit(prompt.slide_number);
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                saveEdit(prompt.slide_number, prompt.editedPrompt);
                                            }
                                        }}
                                        style={{
                                            width: '100%',
                                            padding: '0.5rem',
                                            borderRadius: '6px',
                                            border: '2px solid var(--accent-primary)',
                                            background: 'transparent',
                                            color: 'var(--text-primary)',
                                            resize: 'none',
                                            minHeight: '150px',
                                            fontSize: '0.9rem',
                                            lineHeight: '1.8',
                                            fontFamily: 'inherit',
                                            outline: 'none'
                                        }}
                                    />
                                ) : (
                                    <div
                                        onClick={() => startEditing(prompt.slide_number)}
                                        style={{
                                            color: 'var(--text-primary)',
                                            cursor: 'pointer',
                                            padding: '0.5rem',
                                            borderRadius: '6px',
                                            border: '2px solid transparent',
                                            transition: 'border-color 0.2s',
                                            minHeight: '150px'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
                                        onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                                        title="Click to edit"
                                    >
                                        {formatSentences(prompt.editedPrompt)}
                                    </div>
                                )}
                            </td>
                            <td style={{ ...tdStyle, textAlign: 'center' }}>
                                {!prompt.skip_reason && (
                                    <>
                                        <input
                                            type="file"
                                            accept="image/*"
                                            ref={el => fileInputRefs.current[prompt.slide_number] = el}
                                            style={{ display: 'none' }}
                                            onChange={(e) => handleReferenceImageSelect(prompt.slide_number, e.target.files[0])}
                                        />
                                        {prompt.referenceImagePreview ? (
                                            <div style={{ position: 'relative', display: 'inline-block' }}>
                                                <img
                                                    src={prompt.referenceImagePreview}
                                                    alt="Reference"
                                                    style={{
                                                        width: '48px',
                                                        height: '48px',
                                                        objectFit: 'cover',
                                                        borderRadius: '6px',
                                                        border: '2px solid var(--accent-primary)'
                                                    }}
                                                />
                                                <button
                                                    onClick={() => removeReferenceImage(prompt.slide_number)}
                                                    style={{
                                                        position: 'absolute',
                                                        top: '-6px',
                                                        right: '-6px',
                                                        background: 'var(--bg-primary)',
                                                        border: 'none',
                                                        borderRadius: '50%',
                                                        cursor: 'pointer',
                                                        padding: 0,
                                                        display: 'flex'
                                                    }}
                                                    title="Remove reference image"
                                                >
                                                    <XCircle size={16} style={{ color: 'var(--accent-danger, #ef4444)' }} />
                                                </button>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={() => fileInputRefs.current[prompt.slide_number]?.click()}
                                                style={{
                                                    ...iconButtonStyle,
                                                    padding: '8px',
                                                    border: '1px dashed var(--border-color)',
                                                    borderRadius: '6px'
                                                }}
                                                title="Add reference image for image-to-image generation"
                                            >
                                                <Paperclip size={16} />
                                            </button>
                                        )}
                                    </>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {generationProgress && (
                    <span style={{ color: isGenerating ? 'var(--accent-primary)' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {isGenerating && <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />}
                        {generationProgress}
                    </span>
                )}
                <div style={{ display: 'flex', gap: '0.75rem', marginLeft: 'auto' }}>
                    {onClose && <button onClick={onClose} style={secondaryButtonStyle}>Cancel</button>}
                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating || selectedCount === 0}
                        style={{ ...primaryButtonStyle, opacity: (isGenerating || selectedCount === 0) ? 0.5 : 1, cursor: (isGenerating || selectedCount === 0) ? 'not-allowed' : 'pointer' }}
                    >
                        {isGenerating ? 'Generating...' : `Generate ${selectedCount} Images`}
                    </button>
                </div>
            </div>

            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};

export default ImagePromptReview;
