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
        padding: '0.4em 0.6em',
        border: '1px solid #a2a9b1',
        verticalAlign: 'top',
        backgroundColor: isHeader ? '#eaecf0' : '#ffffff',
        fontWeight: isHeader ? 'bold' : 'normal',
        width: width,
        minHeight: '2em',
        outline: isFocused ? '2px solid #36c' : 'none',
        outlineOffset: '-2px',
        cursor: 'text',
        lineHeight: '1.6',
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
        background: animating === direction ? '#e6f3ff' : 'none',
        border: '1px solid transparent',
        borderRadius: '4px',
        padding: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.3 : 1,
        color: '#36c',
        transition: 'all 0.15s ease',
        transform: animating === direction
            ? (direction === 'up' ? 'translateY(-3px)' : 'translateY(3px)')
            : 'translateY(0)',
    });

    return (
        <td style={{
            padding: '0.5em',
            border: '1px solid #a2a9b1',
            backgroundColor: '#f8f9fa',
            textAlign: 'center',
            width: '60px',
            verticalAlign: 'middle',
        }}>
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
            }}>
                <span style={{
                    fontWeight: 600,
                    fontSize: '0.9em',
                    color: '#202122',
                    marginBottom: '6px'
                }}>
                    {rowNumber}
                </span>
                <button
                    onClick={handleMoveUp}
                    disabled={isFirst}
                    style={buttonStyle(isFirst, 'up')}
                    title="Move row up"
                    onMouseEnter={(e) => {
                        if (!isFirst) {
                            e.currentTarget.style.background = '#e6f3ff';
                            e.currentTarget.style.borderColor = '#36c';
                            e.currentTarget.style.transform = 'scale(1.15)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'none';
                        e.currentTarget.style.borderColor = 'transparent';
                        e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    <ChevronUp size={20} strokeWidth={2.5} />
                </button>
                <button
                    onClick={handleMoveDown}
                    disabled={isLast}
                    style={buttonStyle(isLast, 'down')}
                    title="Move row down"
                    onMouseEnter={(e) => {
                        if (!isLast) {
                            e.currentTarget.style.background = '#e6f3ff';
                            e.currentTarget.style.borderColor = '#36c';
                            e.currentTarget.style.transform = 'scale(1.15)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'none';
                        e.currentTarget.style.borderColor = 'transparent';
                        e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    <ChevronDown size={20} strokeWidth={2.5} />
                </button>
                <button
                    onClick={onDelete}
                    style={{
                        background: 'none',
                        border: '1px solid transparent',
                        borderRadius: '4px',
                        padding: '4px',
                        cursor: 'pointer',
                        color: '#c33',
                        transition: 'all 0.15s ease',
                        marginTop: '4px',
                    }}
                    title="Delete row"
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#fee';
                        e.currentTarget.style.borderColor = '#c33';
                        e.currentTarget.style.transform = 'scale(1.1)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'none';
                        e.currentTarget.style.borderColor = 'transparent';
                        e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    <Trash2 size={14} />
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
            background: '#fff',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            overflow: 'hidden',
        }}>
            {/* Toolbar */}
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
                        Script Editor
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: '#54595d',
                        background: '#eaecf0',
                        padding: '0.2em 0.6em',
                        borderRadius: '3px',
                    }}>
                        {slides.length} rows
                    </span>
                    {hasChanges && (
                        <span style={{
                            fontSize: '0.85em',
                            color: '#d33',
                            fontWeight: 500,
                        }}>
                            • Unsaved changes
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
                                    background: '#fff',
                                    border: '1px solid #a2a9b1',
                                    borderRadius: '3px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    fontSize: '0.9rem',
                                    color: '#54595d',
                                }}
                            >
                                <RotateCcw size={14} />
                                Reset
                            </button>
                            <button
                                onClick={handleSave}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    background: '#36c',
                                    border: 'none',
                                    borderRadius: '3px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.3rem',
                                    fontSize: '0.9rem',
                                    color: '#fff',
                                    fontWeight: 500,
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
                            color: '#54595d',
                        }}
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Wiki Table */}
            <div style={{
                padding: '1rem',
                overflowX: 'auto',
                background: '#fff',
            }}>
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontFamily: '"Linux Libertine", "Georgia", "Times", serif',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    border: '1px solid #a2a9b1',
                }}>
                    <thead>
                        <tr>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '50px',
                                textAlign: 'center',
                            }}>
                                #
                            </th>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '35%',
                            }}>
                                Visual Cue
                            </th>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
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
                    marginTop: '0.75rem',
                    textAlign: 'center',
                }}>
                    <button
                        onClick={addSlide}
                        style={{
                            padding: '0.4rem 1rem',
                            background: '#fff',
                            border: '1px dashed #a2a9b1',
                            borderRadius: '3px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            fontSize: '0.9rem',
                            color: '#36c',
                            fontFamily: 'sans-serif',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = '#36c';
                            e.currentTarget.style.background = '#f8f9fa';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = '#a2a9b1';
                            e.currentTarget.style.background = '#fff';
                        }}
                    >
                        <Plus size={16} />
                        Add Row
                    </button>
                </div>

                {/* Help text */}
                <div style={{
                    marginTop: '1rem',
                    padding: '0.75rem',
                    background: '#f8f9fa',
                    border: '1px solid #eaecf0',
                    borderRadius: '3px',
                    fontSize: '0.85rem',
                    color: '#54595d',
                    fontFamily: 'sans-serif',
                }}>
                    <strong>Tips:</strong> Click any cell to edit directly. Use <code style={{
                        background: '#eaecf0',
                        padding: '0.1em 0.3em',
                        borderRadius: '2px'
                    }}>Ctrl+B</code> for bold text.
                    Text like <strong>'''bold'''</strong> will be rendered as <strong>bold</strong>.
                </div>
            </div>
        </div>
    );
};

export default WikiScriptEditor;
