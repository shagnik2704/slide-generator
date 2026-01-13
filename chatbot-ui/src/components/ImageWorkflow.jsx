import React, { useState, useRef, useEffect } from 'react';
import { Image, Download, Loader2, Paperclip, XCircle, RefreshCw, AlertCircle, User, ChevronDown, ChevronUp } from 'lucide-react';
import Tooltip from './Tooltip';
import { apiJson, API_URL, apiFormData } from '../services/api';

/**
 * Strip markdown formatting from text
 */
const stripMarkdown = (text) => {
    if (!text) return text;
    return text.replace(/\*\*/g, '').replace(/\*/g, '').replace(/__/g, '').replace(/~~/g, '').trim();
};

/**
 * ImageWorkflow - Sentence-based image generation workflow.
 * Each row's narration is split into sentences, with one image per sentence.
 */
const ImageWorkflow = ({ enhancedPrompts, projectId, onClose }) => {
    const STORAGE_KEY = `image_workflow_v2_${projectId}`;

    // Flatten sentences into displayable rows
    // Each "sentence row" has: rowNumber, sentenceIndex, sentenceText, enhancedPrompt, imageUrl, etc.
    const [sentenceRows, setSentenceRows] = useState(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        let savedMap = {};
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                // Build a map: "rowNumber_sentenceIndex" -> saved data
                parsed.forEach(s => {
                    savedMap[`${s.rowNumber}_${s.sentenceIndex}`] = s;
                });
            } catch (e) {
                console.warn('Failed to parse saved workflow:', e);
            }
        }

        // Flatten the new sentence-based structure
        const rows = [];
        enhancedPrompts.forEach(prompt => {
            if (prompt.skip_reason) {
                // Skipped rows get a single entry
                rows.push({
                    rowNumber: prompt.slide_number,
                    sentenceIndex: -1, // -1 indicates skipped row
                    title: prompt.title,
                    visualCue: prompt.original,
                    sentenceText: null,
                    enhancedPrompt: null,
                    skipReason: prompt.skip_reason,
                    selected: false,
                    isEditing: false,
                    imageUrl: null,
                    imageStatus: 'skipped',
                    imageError: null
                });
            } else if (prompt.sentences && prompt.sentences.length > 0) {
                // Each sentence becomes its own row
                prompt.sentences.forEach(sent => {
                    const key = `${prompt.slide_number}_${sent.index}`;
                    const savedRow = savedMap[key];
                    rows.push({
                        rowNumber: prompt.slide_number,
                        sentenceIndex: sent.index,
                        title: prompt.title,
                        visualCue: prompt.original,
                        sentenceText: sent.text,
                        enhancedPrompt: savedRow?.enhancedPrompt || sent.enhanced || sent.text,
                        skipReason: null,
                        selected: savedRow?.selected ?? true,
                        isEditing: false,
                        imageUrl: savedRow?.imageUrl || null,
                        imageStatus: savedRow?.imageUrl ? 'success' : 'pending',
                        imageError: null
                    });
                });
            } else {
                // Fallback: no sentences, create single row from visual cue
                const key = `${prompt.slide_number}_0`;
                const savedRow = savedMap[key];
                rows.push({
                    rowNumber: prompt.slide_number,
                    sentenceIndex: 0,
                    title: prompt.title,
                    visualCue: prompt.original,
                    sentenceText: prompt.original,
                    enhancedPrompt: savedRow?.enhancedPrompt || prompt.original,
                    skipReason: null,
                    selected: savedRow?.selected ?? true,
                    isEditing: false,
                    imageUrl: savedRow?.imageUrl || null,
                    imageStatus: savedRow?.imageUrl ? 'success' : 'pending',
                    imageError: null
                });
            }
        });
        return rows;
    });

    const [isGeneratingAll, setIsGeneratingAll] = useState(false);
    const [isSelectionMode, setIsSelectionMode] = useState(false);
    const [isCharPanelOpen, setIsCharPanelOpen] = useState(false);
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

    // Save sentence rows to localStorage on change
    useEffect(() => {
        const toSave = sentenceRows.map(s => ({
            rowNumber: s.rowNumber,
            sentenceIndex: s.sentenceIndex,
            selected: s.selected,
            enhancedPrompt: s.enhancedPrompt,
            imageUrl: s.imageUrl,
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    }, [sentenceRows, STORAGE_KEY]);

    // Counts
    const selectedCount = sentenceRows.filter(s => s.selected && !s.skipReason).length;
    const generatedCount = sentenceRows.filter(s => s.imageStatus === 'success').length;
    const totalGeneratable = sentenceRows.filter(s => !s.skipReason).length;

    // Helper to create unique key for a sentence
    const getSentenceKey = (rowNumber, sentenceIndex) => `${rowNumber}_${sentenceIndex}`;

    // Toggle selection
    const toggleSelection = (rowNumber, sentenceIndex) => {
        setSentenceRows(prev => prev.map(s =>
            s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                ? { ...s, selected: !s.selected }
                : s
        ));
    };

    // Editing functions
    const startEditing = (rowNumber, sentenceIndex) => {
        setSentenceRows(prev => prev.map(s =>
            s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                ? { ...s, isEditing: true }
                : s
        ));
    };

    const saveEdit = (rowNumber, sentenceIndex, newPrompt) => {
        setSentenceRows(prev => prev.map(s =>
            s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                ? { ...s, enhancedPrompt: newPrompt, isEditing: false }
                : s
        ));
    };

    const cancelEdit = (rowNumber, sentenceIndex) => {
        setSentenceRows(prev => prev.map(s =>
            s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                ? { ...s, isEditing: false }
                : s
        ));
    };

    // Generate single image for a sentence
    const generateSingleImage = async (rowNumber, sentenceIndex) => {
        const row = sentenceRows.find(s => s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex);
        if (!row) return;

        setSentenceRows(prev => prev.map(s =>
            s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                ? { ...s, imageStatus: 'generating', imageError: null }
                : s
        ));

        try {
            const promptToUse = globalCharRef.enabled && globalCharRef.description
                ? `${globalCharRef.description}\n\n${row.enhancedPrompt}`
                : row.enhancedPrompt;

            const result = await apiJson('/generate_images', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId,
                    prompts: [{
                        slide_number: rowNumber,
                        sentence_index: sentenceIndex,
                        prompt: promptToUse,
                        reference_image_path: globalCharRef.enabled ? globalCharRef.imagePath : null
                    }],
                    aspect_ratio: '16:9'
                })
            });
            const generatedImage = result.images?.find(
                img => img.slide_number === rowNumber && (img.sentence_index === sentenceIndex || img.sentence_index === undefined)
            );

            if (generatedImage?.success) {
                setSentenceRows(prev => prev.map(s =>
                    s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                        ? { ...s, imageUrl: generatedImage.url, imageStatus: 'success', imageError: null }
                        : s
                ));
            } else {
                setSentenceRows(prev => prev.map(s =>
                    s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                        ? { ...s, imageStatus: 'error', imageError: generatedImage?.error || 'Generation failed' }
                        : s
                ));
            }
        } catch (error) {
            setSentenceRows(prev => prev.map(s =>
                s.rowNumber === rowNumber && s.sentenceIndex === sentenceIndex
                    ? { ...s, imageStatus: 'error', imageError: error.message }
                    : s
            ));
        }
    };

    // Generate all selected images
    const generateAllSelected = async () => {
        const selectedRows = sentenceRows.filter(s => s.selected && !s.skipReason);
        if (selectedRows.length === 0) return;

        setIsGeneratingAll(true);
        setSentenceRows(prev => prev.map(s =>
            s.selected && !s.skipReason
                ? { ...s, imageStatus: 'generating', imageError: null }
                : s
        ));

        try {
            const prompts = selectedRows.map(row => ({
                slide_number: row.rowNumber,
                sentence_index: row.sentenceIndex,
                prompt: globalCharRef.enabled && globalCharRef.description
                    ? `${globalCharRef.description}\n\n${row.enhancedPrompt}`
                    : row.enhancedPrompt,
                reference_image_path: globalCharRef.enabled ? globalCharRef.imagePath : null
            }));

            const result = await apiJson('/generate_images', {
                method: 'POST',
                body: JSON.stringify({
                    project_id: projectId,
                    prompts: prompts,
                    aspect_ratio: '16:9'
                })
            });
            setSentenceRows(prev => prev.map(s => {
                const generated = result.images?.find(
                    img => img.slide_number === s.rowNumber &&
                        (img.sentence_index === s.sentenceIndex || img.sentence_index === undefined)
                );
                if (!generated) return s;
                return {
                    ...s,
                    imageUrl: generated.success ? generated.url : s.imageUrl,
                    imageStatus: generated.success ? 'success' : 'error',
                    imageError: generated.success ? null : generated.error
                };
            }));
        } catch (error) {
            setSentenceRows(prev => prev.map(s =>
                s.selected && !s.skipReason
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

    // Build download URL that triggers Content-Disposition: attachment header
    const getDownloadUrl = (url) => {
        if (!url) return null;
        // Extract project_id and filename from URL like /output/images/123/file.png
        const match = url.match(/\/output\/images\/([^/]+)\/([^/]+)$/);
        if (match) {
            const [, projectId, filename] = match;
            return `${API_URL}/download/image/${projectId}/${filename}`;
        }
        return getImageUrl(url);
    };

    // Check if this is the first sentence of a new row (for visual grouping)
    const isFirstSentenceOfRow = (index) => {
        if (index === 0) return true;
        return sentenceRows[index].rowNumber !== sentenceRows[index - 1].rowNumber;
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
                        {generatedCount}/{totalGeneratable} generated (sentence-wise)
                        {isSelectionMode && ` • ${selectedCount} selected`}
                    </div>
                </div>

                {!isSelectionMode ? (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {generatedCount > 0 && (
                            <a
                                href={`${API_URL}/download/zip/${projectId}/project_${projectId}_images.zip`}
                                style={{ ...buttonStyle, textDecoration: 'none' }}
                            >
                                <Download size={16} /> Download All
                            </a>
                        )}
                        <button
                            onClick={() => setIsSelectionMode(true)}
                            style={primaryButtonStyle}
                        >
                            Select
                        </button>
                    </div>
                ) : (
                    <>
                        {generatedCount > 0 && (
                            <a
                                href={`${API_URL}/download/zip/${projectId}/project_${projectId}_images.zip`}
                                style={{ ...buttonStyle, textDecoration: 'none' }}
                            >
                                <Download size={16} /> Download All
                            </a>
                        )}
                        <button
                            onClick={() => setSentenceRows(prev => prev.map(s => ({ ...s, selected: !s.skipReason })))}
                            style={buttonStyle}
                        >
                            Select All
                        </button>
                        <button
                            onClick={() => setSentenceRows(prev => prev.map(s => ({ ...s, selected: false })))}
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

                                    const formData = new FormData();
                                    formData.append('file', file);
                                    formData.append('project_id', projectId);
                                    formData.append('slide_number', 0);

                                    try {
                                        const data = await apiFormData('/upload_reference_image', formData);
                                        setGlobalCharRef(prev => ({
                                            ...prev,
                                            imageUrl: URL.createObjectURL(file),
                                            imagePath: data.path,
                                            enabled: true
                                        }));
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

                        {/* Use generated image as reference */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Use generated image:</span>
                            <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                {sentenceRows.filter(s => s.imageUrl && s.imageStatus === 'success').slice(0, 8).map(s => (
                                    <button
                                        key={getSentenceKey(s.rowNumber, s.sentenceIndex)}
                                        onClick={() => setGlobalCharRef(prev => ({
                                            ...prev,
                                            imageUrl: getImageUrl(s.imageUrl),
                                            imagePath: s.imageUrl,
                                            enabled: true
                                        }))}
                                        style={{ ...buttonStyle, padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                    >
                                        {s.rowNumber}.{s.sentenceIndex + 1}
                                    </button>
                                ))}
                                {sentenceRows.filter(s => s.imageUrl && s.imageStatus === 'success').length === 0 && (
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                                        No images generated yet
                                    </span>
                                )}
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
                        {sentenceRows.map((row, i) => (
                            <tr
                                key={getSentenceKey(row.rowNumber, row.sentenceIndex)}
                                style={{
                                    background: i % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                                    opacity: row.skipReason ? 0.5 : 1,
                                    borderTop: isFirstSentenceOfRow(i) ? '2px solid var(--border-color)' : 'none'
                                }}
                            >
                                {/* Checkbox - only in selection mode */}
                                {isSelectionMode && (
                                    <td style={{ ...tdStyle, textAlign: 'center', verticalAlign: 'middle' }}>
                                        <input
                                            type="checkbox"
                                            checked={row.selected}
                                            onChange={() => toggleSelection(row.rowNumber, row.sentenceIndex)}
                                            disabled={!!row.skipReason}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                    </td>
                                )}

                                {/* Row.Sentence Number */}
                                <td style={{ ...tdStyle, fontWeight: 600, textAlign: 'center', verticalAlign: 'middle' }}>
                                    {row.sentenceIndex >= 0 ? `${row.rowNumber}.${row.sentenceIndex + 1}` : row.rowNumber}
                                </td>

                                {/* Visual Cue (same for all sentences in a row) */}
                                <td style={{ ...tdStyle, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                    {row.skipReason ? (
                                        <span style={{ fontStyle: 'italic' }}>{row.skipReason}</span>
                                    ) : (
                                        stripMarkdown(row.visualCue) || '—'
                                    )}
                                </td>

                                {/* Narration (the sentence text) */}
                                <td style={{ ...tdStyle, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                    {row.skipReason ? (
                                        <span style={{ fontStyle: 'italic' }}>—</span>
                                    ) : (
                                        stripMarkdown(row.sentenceText) || '—'
                                    )}
                                </td>

                                {/* Image Prompt (Editable) */}
                                <td style={tdStyle}>
                                    {row.skipReason ? (
                                        <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>—</span>
                                    ) : row.isEditing ? (
                                        <textarea
                                            autoFocus
                                            value={row.enhancedPrompt}
                                            onChange={(e) => setSentenceRows(prev => prev.map(s =>
                                                s.rowNumber === row.rowNumber && s.sentenceIndex === row.sentenceIndex
                                                    ? { ...s, enhancedPrompt: e.target.value }
                                                    : s
                                            ))}
                                            onBlur={() => saveEdit(row.rowNumber, row.sentenceIndex, row.enhancedPrompt)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Escape') cancelEdit(row.rowNumber, row.sentenceIndex);
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault();
                                                    saveEdit(row.rowNumber, row.sentenceIndex, row.enhancedPrompt);
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
                                                minHeight: '80px',
                                                fontSize: '0.85rem',
                                                lineHeight: '1.5',
                                                fontFamily: 'inherit',
                                                outline: 'none'
                                            }}
                                        />
                                    ) : (
                                        <div
                                            onClick={() => startEditing(row.rowNumber, row.sentenceIndex)}
                                            style={{
                                                padding: '0.5rem',
                                                borderRadius: '6px',
                                                border: '2px solid transparent',
                                                cursor: 'pointer',
                                                color: 'var(--accent-primary)',
                                                fontSize: '0.85rem',
                                                lineHeight: 1.5,
                                                transition: 'border-color 0.2s'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
                                            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                                        >
                                            {row.enhancedPrompt}
                                        </div>
                                    )}
                                </td>

                                {/* Generated Image */}
                                <td style={{ ...tdStyle, textAlign: 'center', verticalAlign: 'middle' }}>
                                    {row.skipReason ? (
                                        <span style={{ color: 'var(--text-secondary)' }}>—</span>
                                    ) : row.imageStatus === 'pending' ? (
                                        <button
                                            onClick={() => generateSingleImage(row.rowNumber, row.sentenceIndex)}
                                            style={primaryButtonStyle}
                                        >
                                            <Image size={14} /> Generate
                                        </button>
                                    ) : row.imageStatus === 'generating' ? (
                                        <div style={{ color: 'var(--text-secondary)' }}>
                                            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
                                            <p style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>Generating...</p>
                                        </div>
                                    ) : row.imageStatus === 'success' && row.imageUrl ? (
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                                            <img
                                                src={getImageUrl(row.imageUrl)}
                                                alt={`Row ${row.rowNumber}.${row.sentenceIndex + 1}`}
                                                style={{ maxWidth: '140px', maxHeight: '100px', borderRadius: '6px' }}
                                            />
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                <Tooltip text="Regenerate" position="bottom">
                                                    <button
                                                        onClick={() => generateSingleImage(row.rowNumber, row.sentenceIndex)}
                                                        style={{ ...buttonStyle, padding: '0.3rem 0.5rem', fontSize: '0.75rem' }}
                                                    >
                                                        <RefreshCw size={14} />
                                                    </button>
                                                </Tooltip>
                                                <Tooltip text="Download" position="bottom">
                                                    <a
                                                        href={getDownloadUrl(row.imageUrl)}
                                                        style={{ ...buttonStyle, padding: '0.3rem 0.5rem', fontSize: '0.75rem', textDecoration: 'none' }}
                                                    >
                                                        <Download size={14} />
                                                    </a>
                                                </Tooltip>
                                            </div>
                                        </div>
                                    ) : row.imageStatus === 'error' ? (
                                        <div style={{ color: '#ef4444' }}>
                                            <AlertCircle size={20} />
                                            <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{row.imageError}</p>
                                            <button
                                                onClick={() => generateSingleImage(row.rowNumber, row.sentenceIndex)}
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
