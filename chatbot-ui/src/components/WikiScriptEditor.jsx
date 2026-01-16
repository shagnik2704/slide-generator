import React, { useState, useEffect, useRef } from 'react';
import { Save, X, Plus, Trash2, ChevronUp, ChevronDown, RotateCcw } from 'lucide-react';

/**
 * Converts wiki/markdown bold syntax to HTML for display
 * '''text''' or **text** → <strong>text</strong>
 */
const wikiToHtml = (text) => {
    if (!text) return '';
    let html = text;
    // Convert '''text''' to bold (wiki style)
    html = html.replace(/'''([^']+)'''/g, '<strong>$1</strong>');
    // Convert **text** to bold (markdown style)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Convert newlines to <br>
    html = html.replace(/\n/g, '<br>');
    return html;
};

/**
 * Converts HTML bold back to wiki syntax for storage
 * <strong>text</strong> → '''text'''
 */
const htmlToWiki = (html) => {
    if (!html) return '';
    let text = html;
    // Convert <strong> and <b> to wiki bold
    text = text.replace(/<strong>([^<]+)<\/strong>/gi, "'''$1'''");
    text = text.replace(/<b>([^<]+)<\/b>/gi, "'''$1'''");
    // Convert <br> to newlines
    text = text.replace(/<br\s*\/?>/gi, '\n');
    // Remove any remaining HTML tags
    text = text.replace(/<[^>]+>/g, '');
    // Decode HTML entities
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
};

/**
 * Editable cell that uses contentEditable for true WYSIWYG editing
 */
const WikiCell = ({ value, onChange, isHeader = false, width }) => {
    const cellRef = useRef(null);
    const [isFocused, setIsFocused] = useState(false);

    // Update cell content when value changes externally
    useEffect(() => {
        if (cellRef.current && !isFocused) {
            cellRef.current.innerHTML = wikiToHtml(value);
        }
    }, [value, isFocused]);

    const handleBlur = () => {
        setIsFocused(false);
        if (cellRef.current) {
            const newValue = htmlToWiki(cellRef.current.innerHTML);
            if (newValue !== value) {
                onChange(newValue);
            }
        }
    };

    const handleFocus = () => {
        setIsFocused(true);
    };

    const handleKeyDown = (e) => {
        // Ctrl+B for bold
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            document.execCommand('bold', false, null);
        }
    };

    const cellStyle = {
        padding: '0.75rem 1rem',
        border: '1px solid var(--border-color)',
        verticalAlign: 'top',
        backgroundColor: isHeader ? 'var(--bg-secondary)' : 'transparent',
        fontWeight: isHeader ? 'bold' : 'normal',
        width: width,
        minHeight: '2.5em',
        outline: isFocused ? '2px solid var(--accent-primary)' : 'none',
        outlineOffset: '-2px',
        cursor: 'text',
        lineHeight: '1.6',
        color: 'var(--text-primary)',
    };

    if (isHeader) {
        return (
            <th style={cellStyle}>
                {value}
            </th>
        );
    }

    return (
        <td
            ref={cellRef}
            contentEditable={true}
            onBlur={handleBlur}
            onFocus={handleFocus}
            onKeyDown={handleKeyDown}
            style={cellStyle}
            suppressContentEditableWarning={true}
        />
    );
};

/**
 * Row controls (move up/down, delete) with animations
 */
const RowControls = ({ onMoveUp, onMoveDown, onDelete, isFirst, isLast, rowNumber }) => {
    const [animating, setAnimating] = useState(null); // 'up' | 'down' | null

    const handleMoveUp = () => {
        if (isFirst) return;
        setAnimating('up');
        setTimeout(() => {
            onMoveUp();
            setAnimating(null);
        }, 150);
    };

    const handleMoveDown = () => {
        if (isLast) return;
        setAnimating('down');
        setTimeout(() => {
            onMoveDown();
            setAnimating(null);
        }, 150);
    };

    const buttonStyle = (disabled, direction) => ({
        background: animating === direction ? 'var(--bg-tertiary)' : 'none',
        border: '1px solid transparent',
        borderRadius: '8px',
        padding: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.3 : 1,
        color: 'var(--accent-primary)',
        transition: 'all 0.15s ease',
        transform: animating === direction
            ? (direction === 'up' ? 'translateY(-3px)' : 'translateY(3px)')
            : 'translateY(0)',
    });

    return (
        <td style={{
            padding: '0.75rem',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            textAlign: 'center',
            width: '70px',
            verticalAlign: 'middle',
        }}>
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
            }}>
                <span style={{
                    fontWeight: 700,
                    fontSize: '0.9rem',
                    color: 'var(--text-primary)',
                    marginBottom: '4px'
                }}>
                    {rowNumber}
                </span>
                <button
                    onClick={handleMoveUp}
                    disabled={isFirst}
                    style={buttonStyle(isFirst, 'up')}
                    className="row-btn"
                    title="Move row up"
                >
                    <ChevronUp size={20} strokeWidth={2.5} />
                </button>
                <button
                    onClick={handleMoveDown}
                    disabled={isLast}
                    style={buttonStyle(isLast, 'down')}
                    className="row-btn"
                    title="Move row down"
                >
                    <ChevronDown size={20} strokeWidth={2.5} />
                </button>
                <button
                    onClick={onDelete}
                    className="row-btn delete-btn"
                    style={{
                        background: 'none',
                        border: '1px solid transparent',
                        borderRadius: '8px',
                        padding: '6px',
                        cursor: 'pointer',
                        color: '#d93025',
                        transition: 'all 0.15s ease',
                        marginTop: '4px',
                    }}
                    title="Delete row"
                >
                    <Trash2 size={16} />
                </button>
            </div>
        </td>
    );
};

/**
 * Main WikiTable Editor - looks exactly like MediaWiki tables
 */
const WikiScriptEditor = ({ jsonScript, onSave, onClose, isOpen }) => {
    const [slides, setSlides] = useState([]);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalSlides, setOriginalSlides] = useState([]);

    useEffect(() => {
        if (jsonScript?.slides) {
            const slidesCopy = JSON.parse(JSON.stringify(jsonScript.slides));
            setSlides(slidesCopy);
            setOriginalSlides(slidesCopy);
            setHasChanges(false);
        }
    }, [jsonScript]);

    const updateSlide = (index, field, value) => {
        const updated = [...slides];
        updated[index] = { ...updated[index], [field]: value };
        setSlides(updated);
        setHasChanges(true);
    };

    const deleteSlide = (index) => {
        if (slides.length <= 1) return;
        if (window.confirm(`Delete row ${index + 1}?`)) {
            const updated = slides.filter((_, i) => i !== index);
            setSlides(updated);
            setHasChanges(true);
        }
    };

    const moveSlide = (fromIndex, toIndex) => {
        if (toIndex < 0 || toIndex >= slides.length) return;
        const updated = [...slides];
        const [removed] = updated.splice(fromIndex, 1);
        updated.splice(toIndex, 0, removed);
        setSlides(updated);
        setHasChanges(true);
    };

    const addSlide = () => {
        const newSlide = {
            title: '',
            narration: '',
            image_prompt: '',
            slide_type: 'demo'
        };
        setSlides([...slides, newSlide]);
        setHasChanges(true);
    };

    const handleSave = () => {
        const updatedScript = {
            ...jsonScript,
            slides: slides
        };
        onSave(updatedScript);
        setOriginalSlides(JSON.parse(JSON.stringify(slides)));
        setHasChanges(false);
    };

    const handleReset = () => {
        if (window.confirm('Discard all changes?')) {
            setSlides(JSON.parse(JSON.stringify(originalSlides)));
            setHasChanges(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            marginTop: '1rem',
            background: 'var(--bg-primary)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
        }}>
            {/* Toolbar */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.875rem 1.25rem',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-color)',
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        Script Editor
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-tertiary)',
                        padding: '0.2em 0.6em',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                    }}>
                        {slides.length} rows
                    </span>
                    {hasChanges && (
                        <span style={{
                            fontSize: '0.85em',
                            color: '#d93025',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                        }}>
                            <span style={{ width: '6px', height: '6px', background: '#d93025', borderRadius: '50%' }}></span>
                            Unsaved changes
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {hasChanges && (
                        <>
                            <button
                                onClick={handleReset}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    background: 'var(--bg-primary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    fontSize: '0.85rem',
                                    color: 'var(--text-secondary)',
                                }}
                            >
                                <RotateCcw size={14} />
                                Reset
                            </button>
                            <button
                                onClick={handleSave}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    background: 'var(--accent-primary)',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    fontSize: '0.85rem',
                                    color: 'white',
                                    fontWeight: 600,
                                }}
                            >
                                <Save size={14} />
                                Save
                            </button>
                        </>
                    )}
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

            {/* Wiki Table */}
            <div style={{
                padding: '1.25rem',
                overflowX: 'auto',
                background: 'var(--bg-primary)',
            }}>
                <table style={{
                    width: '100%',
                    borderCollapse: 'separate',
                    borderSpacing: '0',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    overflow: 'hidden'
                }}>
                    <thead>
                        <tr>
                            <th style={{
                                padding: '0.75rem',
                                borderRight: '1px solid var(--border-color)',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                width: '70px',
                                textAlign: 'center',
                                color: 'var(--text-primary)',
                            }}>
                                #
                            </th>
                            <th style={{
                                padding: '0.75rem',
                                borderRight: '1px solid var(--border-color)',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                width: '35%',
                                color: 'var(--text-primary)',
                                textAlign: 'left'
                            }}>
                                Visual Cue
                            </th>
                            <th style={{
                                padding: '0.75rem',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                color: 'var(--text-primary)',
                                textAlign: 'left'
                            }}>
                                Narration
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {slides.map((slide, index) => (
                            <tr key={index}>
                                <RowControls
                                    rowNumber={index + 1}
                                    onMoveUp={() => moveSlide(index, index - 1)}
                                    onMoveDown={() => moveSlide(index, index + 1)}
                                    onDelete={() => deleteSlide(index)}
                                    isFirst={index === 0}
                                    isLast={index === slides.length - 1}
                                />
                                <WikiCell
                                    value={slide.image_prompt || ''}
                                    onChange={(value) => updateSlide(index, 'image_prompt', value)}
                                    width="35%"
                                />
                                <WikiCell
                                    value={slide.narration || ''}
                                    onChange={(value) => updateSlide(index, 'narration', value)}
                                />
                            </tr>
                        ))}
                    </tbody>
                </table>

                {/* Add Row Button */}
                <div style={{
                    marginTop: '1.25rem',
                    textAlign: 'center',
                }}>
                    <button
                        onClick={addSlide}
                        style={{
                            padding: '0.6rem 1.5rem',
                            background: 'var(--bg-primary)',
                            border: '2px dashed var(--border-color)',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            fontSize: '0.9rem',
                            color: 'var(--accent-primary)',
                            fontWeight: 600,
                            transition: 'all 0.2s ease',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'var(--accent-primary)';
                            e.currentTarget.style.background = 'var(--bg-secondary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                            e.currentTarget.style.background = 'var(--bg-primary)';
                        }}
                    >
                        <Plus size={18} />
                        Add New Row
                    </button>
                </div>

                {/* Help text */}
                <div style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Tips:</strong> Click any cell to edit directly. Use <code style={{
                        background: 'var(--bg-primary)',
                        padding: '0.1em 0.4em',
                        borderRadius: '4px',
                        border: '1px solid var(--border-color)'
                    }}>Ctrl+B</code> for bold text.
                    Text like <strong>'''bold'''</strong> will be rendered as <strong>bold</strong>.
                </div>
            </div>

            <style>{`
                .row-btn:hover {
                    background: var(--bg-tertiary) !important;
                    border-color: var(--accent-primary) !important;
                    transform: scale(1.1) !important;
                }
                .delete-btn:hover {
                    background: rgba(217, 48, 37, 0.1) !important;
                    border-color: #d93025 !important;
                    color: #d93025 !important;
                }
            `}</style>
        </div>
    );
};

export default WikiScriptEditor;
