import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Save, X, Plus, Trash2, ChevronUp, ChevronDown, RotateCcw } from 'lucide-react';

const wikiToHtml = (text) => {
    if (!text) return '';
    let html = text;
    html = html.replace(/'''([^']+)'''/g, '<strong>$1</strong>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
};

const htmlToWiki = (html) => {
    if (!html) return '';
    let text = html;
    text = text.replace(/<strong>([^<]+)<\/strong>/gi, "'''$1'''");
    text = text.replace(/<b>([^<]+)<\/b>/gi, "'''$1'''");
    text = text.replace(/<br\s*\/?>/gi, '\n');
    text = text.replace(/<[^>]+>/g, '');
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
};

const cellBaseStyle = {
    padding: '0.75rem 1rem',
    border: '1px solid var(--border-color)',
    verticalAlign: 'top',
    minHeight: '2.5em',
    lineHeight: '1.6',
    color: 'var(--text-primary)',
};

const WikiCell = ({
    value,
    onChange,
    width,
    readOnly = false,
    issueIds = [],
    isActive = false,
    onIssueClick,
}) => {
    const cellRef = useRef(null);
    const [isFocused, setIsFocused] = useState(false);

    useEffect(() => {
        if (cellRef.current && !isFocused && !readOnly) {
            cellRef.current.innerHTML = wikiToHtml(value);
        }
    }, [value, isFocused, readOnly]);

    const style = {
        ...cellBaseStyle,
        width,
        backgroundColor: isActive
            ? 'rgba(217, 48, 37, 0.16)'
            : issueIds.length
                ? 'rgba(217, 48, 37, 0.07)'
                : 'transparent',
        outline: isFocused ? '2px solid var(--accent-primary)' : 'none',
        outlineOffset: '-2px',
        cursor: readOnly ? (issueIds.length ? 'pointer' : 'default') : 'text',
        boxShadow: isActive ? 'inset 0 0 0 2px #d93025' : 'none',
    };

    if (readOnly) {
        return (
            <td onClick={issueIds.length ? onIssueClick : undefined} style={style}>
                <span dangerouslySetInnerHTML={{ __html: wikiToHtml(value) }} />
            </td>
        );
    }

    const handleBlur = () => {
        setIsFocused(false);
        if (cellRef.current) {
            const newValue = htmlToWiki(cellRef.current.innerHTML);
            if (newValue !== value) onChange(newValue);
        }
    };

    const handleKeyDown = (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
            event.preventDefault();
            document.execCommand('bold', false, null);
        }
    };

    return (
        <td
            ref={cellRef}
            contentEditable
            onBlur={handleBlur}
            onFocus={() => setIsFocused(true)}
            onKeyDown={handleKeyDown}
            style={style}
            suppressContentEditableWarning
        />
    );
};

const RowControls = ({ onMoveUp, onMoveDown, onDelete, isFirst, isLast, rowNumber }) => {
    const buttonStyle = (disabled) => ({
        background: 'none',
        border: '1px solid transparent',
        borderRadius: '8px',
        padding: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.3 : 1,
        color: 'var(--accent-primary)',
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
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{rowNumber}</span>
                <button onClick={onMoveUp} disabled={isFirst} style={buttonStyle(isFirst)} title="Move row up">
                    <ChevronUp size={20} strokeWidth={2.5} />
                </button>
                <button onClick={onMoveDown} disabled={isLast} style={buttonStyle(isLast)} title="Move row down">
                    <ChevronDown size={20} strokeWidth={2.5} />
                </button>
                <button onClick={onDelete} style={{ ...buttonStyle(false), color: '#d93025' }} title="Delete row">
                    <Trash2 size={16} />
                </button>
            </div>
        </td>
    );
};

const rowIdForIndex = (index) => `row_${String(index + 1).padStart(3, '0')}`;

const WikiScriptEditor = ({
    jsonScript,
    onSave,
    onClose,
    isOpen,
    readOnly = false,
    fillHeight = false,
    flushTop = false,
    showCloseButton = true,
    showTips = true,
    annotations = {},
    issues = [],
    activeIssueId = null,
    scrollTrigger = 0,
    activeIssue = null,
    activeIssueCheck = null,
    onIssueSelect,
    showCommentColumn = false,
    reviewComments = {},
    onReviewCommentChange,
    onDownloadReview,
    isDownloadingReview = false,
}) => {
    const [slides, setSlides] = useState([]);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalSlides, setOriginalSlides] = useState([]);
    const rowRefs = useRef({});

    const issueById = useMemo(
        () => Object.fromEntries((issues || []).map((issue) => [issue.id, issue])),
        [issues]
    );

    useEffect(() => {
        if (jsonScript?.slides) {
            const slidesCopy = JSON.parse(JSON.stringify(jsonScript.slides));
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setSlides(slidesCopy);
            setOriginalSlides(slidesCopy);
            setHasChanges(false);
        }
    }, [jsonScript]);

    useEffect(() => {
        if (!activeIssueId || !isOpen) return;
        const activeIssue = issues.find((issue) => issue.id === activeIssueId);
        const rowId = activeIssue?.evidence?.find((ev) => ev.row_id)?.row_id;
        if (rowId && rowRefs.current[rowId]) {
            rowRefs.current[rowId].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [activeIssueId, scrollTrigger, issues, isOpen]);

    const updateSlide = (index, field, value) => {
        const updated = [...slides];
        updated[index] = { ...updated[index], [field]: value };
        setSlides(updated);
        setHasChanges(true);
    };

    const deleteSlide = (index) => {
        if (slides.length <= 1) return;
        if (window.confirm(`Delete row ${index + 1}?`)) {
            setSlides(slides.filter((_, i) => i !== index));
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
        setSlides([...slides, { title: '', narration: '', image_prompt: '', slide_type: 'demo' }]);
        setHasChanges(true);
    };

    const handleSave = () => {
        const updatedScript = { ...jsonScript, slides };
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

    const getCellIssues = (rowId, field) => annotations?.[`${rowId}:${field}`] || [];
    const getRowIssues = (rowId) => Array.from(new Set([
        ...getCellIssues(rowId, 'visual_cue'),
        ...getCellIssues(rowId, 'narration'),
        ...getCellIssues(rowId, 'script'),
    ]));
    const selectFirstIssue = (issueIds) => {
        if (issueIds.length && onIssueSelect) onIssueSelect(issueIds[0]);
    };

    if (!isOpen) return null;

    return (
        <div style={{
            marginTop: fillHeight || flushTop ? 0 : '1rem',
            background: 'var(--bg-primary)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            flex: fillHeight ? 1 : undefined,
            minHeight: fillHeight ? 0 : undefined,
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.875rem 1.25rem',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-color)',
                gap: '0.75rem',
                flexWrap: 'wrap',
                flexShrink: 0,
            }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {readOnly ? 'Script Viewer' : 'Script Editor'}
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
                        {!readOnly && hasChanges && (
                            <span style={{ fontSize: '0.85em', color: '#d93025', fontWeight: 600 }}>
                                Unsaved changes
                            </span>
                        )}
                    </div>
                    {readOnly && (
                        activeIssue ? (
                            <SelectedIssueHeader issue={activeIssue} check={activeIssueCheck} />
                        ) : (
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                Select an issue to inspect the exact row and cell.
                            </div>
                        )
                    )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {!readOnly && hasChanges && (
                        <>
                            <button onClick={handleReset} style={toolbarButtonStyle()}>
                                <RotateCcw size={14} />
                                Reset
                            </button>
                            <button onClick={handleSave} style={toolbarButtonStyle(true)}>
                                <Save size={14} />
                                Save
                            </button>
                        </>
                    )}
                    {showCloseButton && onClose && (
                        <button onClick={onClose} style={{ padding: '0.4rem', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                            <X size={18} />
                        </button>
                    )}
                    {readOnly && onDownloadReview && (
                        <button
                            onClick={onDownloadReview}
                            disabled={isDownloadingReview}
                            style={toolbarButtonStyle()}
                            type="button"
                        >
                            <Download size={14} />
                            {isDownloadingReview ? 'Preparing...' : 'Download'}
                        </button>
                    )}
                </div>
            </div>

            <div style={{
                padding: '1.25rem',
                overflowX: 'auto',
                overflowY: fillHeight ? 'auto' : undefined,
                background: 'var(--bg-primary)',
                flex: fillHeight ? 1 : undefined,
                minHeight: fillHeight ? 0 : undefined,
            }}>
                <table style={{
                    width: '100%',
                    minWidth: readOnly ? (showCommentColumn ? '1080px' : '760px') : '900px',
                    borderCollapse: 'separate',
                    borderSpacing: '0',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    overflow: 'hidden',
                }}>
                    <thead>
                        <tr>
                            <HeaderCell width="70px" align="center">#</HeaderCell>
                            <HeaderCell width="35%">Visual Cue</HeaderCell>
                            <HeaderCell>Narration</HeaderCell>
                            {showCommentColumn && <HeaderCell width="280px">Reviewer Comments</HeaderCell>}
                        </tr>
                    </thead>
                    <tbody>
                        {slides.map((slide, index) => {
                            const rowId = rowIdForIndex(index);
                            const rowIssues = getRowIssues(rowId);
                            const visualIssues = getCellIssues(rowId, 'visual_cue');
                            const narrationIssues = getCellIssues(rowId, 'narration');
                            const rowActive = rowIssues.includes(activeIssueId);
                            return (
                                <tr
                                    key={rowId}
                                    ref={(node) => {
                                        if (node) rowRefs.current[rowId] = node;
                                    }}
                                    style={{ background: rowActive ? 'rgba(217, 48, 37, 0.06)' : 'transparent' }}
                                >
                                    {readOnly ? (
                                        <td
                                            onClick={() => selectFirstIssue(rowIssues)}
                                            title={rowIssues.map((id) => issueById[id]?.message).filter(Boolean).join('\n')}
                                            style={{
                                                padding: '0.75rem',
                                                border: '1px solid var(--border-color)',
                                                backgroundColor: rowIssues.length ? 'rgba(217, 48, 37, 0.1)' : 'var(--bg-secondary)',
                                                textAlign: 'center',
                                                fontWeight: 700,
                                                width: '70px',
                                                verticalAlign: 'middle',
                                                color: rowIssues.length ? '#d93025' : 'var(--text-primary)',
                                                cursor: rowIssues.length ? 'pointer' : 'default',
                                            }}
                                        >
                                            <div>{index + 1}</div>
                                        </td>
                                    ) : (
                                        <RowControls
                                            rowNumber={index + 1}
                                            onMoveUp={() => moveSlide(index, index - 1)}
                                            onMoveDown={() => moveSlide(index, index + 1)}
                                            onDelete={() => deleteSlide(index)}
                                            isFirst={index === 0}
                                            isLast={index === slides.length - 1}
                                        />
                                    )}
                                    <WikiCell
                                        value={slide.image_prompt || ''}
                                        onChange={(value) => updateSlide(index, 'image_prompt', value)}
                                        width="35%"
                                        readOnly={readOnly}
                                        issueIds={visualIssues}
                                        isActive={visualIssues.includes(activeIssueId)}
                                        onIssueClick={() => selectFirstIssue(visualIssues)}
                                    />
                                    <WikiCell
                                        value={slide.narration || ''}
                                        onChange={(value) => updateSlide(index, 'narration', value)}
                                        readOnly={readOnly}
                                        issueIds={narrationIssues}
                                        isActive={narrationIssues.includes(activeIssueId)}
                                        onIssueClick={() => selectFirstIssue(narrationIssues)}
                                    />
                                    {showCommentColumn && (
                                        <CommentCell
                                            value={reviewComments[rowId] || ''}
                                            onChange={(value) => onReviewCommentChange?.(rowId, value)}
                                            rowNumber={index + 1}
                                        />
                                    )}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>

                {!readOnly && (
                    <div style={{ marginTop: '1.25rem', textAlign: 'center' }}>
                        <button onClick={addSlide} style={addButtonStyle}>
                            <Plus size={18} />
                            Add New Row
                        </button>
                    </div>
                )}

                {showTips && (
                    <div style={{
                        marginTop: '1.5rem',
                        padding: '1rem',
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                    }}>
                        <strong style={{ color: 'var(--text-primary)' }}>Tips:</strong>{' '}
                        {readOnly
                            ? 'Click a highlighted row or cell to inspect its compliance issue.'
                            : "Click any cell to edit directly. Use Ctrl+B for bold text. Text like '''bold''' will be rendered as bold."}
                    </div>
                )}
            </div>
        </div>
    );
};

const HeaderCell = ({ children, width, align = 'left' }) => (
    <th style={{
        padding: '0.75rem',
        borderRight: '1px solid var(--border-color)',
        borderBottom: '1px solid var(--border-color)',
        backgroundColor: 'var(--bg-secondary)',
        fontWeight: 'bold',
        width,
        textAlign: align,
        color: 'var(--text-primary)',
    }}>
        {children}
    </th>
);

const CommentCell = ({ value, onChange, rowNumber }) => (
    <td style={{
        ...cellBaseStyle,
        width: '280px',
        backgroundColor: 'var(--bg-secondary)',
    }}>
        <textarea
            aria-label={`Reviewer comments for row ${rowNumber}`}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Add reviewer comment..."
            style={commentTextareaStyle}
        />
    </td>
);

const SelectedIssueHeader = ({ issue, check }) => {
    const firstEvidence = issue.evidence?.[0];

    return (
        <div style={{
            display: 'grid',
            gap: '0.3rem',
            color: 'var(--text-primary)',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                <span style={{
                    border: '1px solid rgba(217, 48, 37, 0.35)',
                    borderRadius: '999px',
                    color: issue.severity === 'minor' ? '#f29900' : '#d93025',
                    background: issue.severity === 'minor' ? 'rgba(242, 153, 0, 0.1)' : 'rgba(217, 48, 37, 0.1)',
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    padding: '0.12rem 0.45rem',
                    textTransform: 'uppercase',
                }}>
                    {issue.severity || 'issue'}
                </span>
                {firstEvidence?.row_number && (
                    <span style={{
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '999px',
                        padding: '0.12rem 0.45rem',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                    }}>
                        Row {firstEvidence.row_number}
                        {firstEvidence.field ? `, ${firstEvidence.field.replace('_', ' ')}` : ''}
                    </span>
                )}
            </div>
            <div style={{ fontWeight: 700 }}>{issue.message}</div>
            {check?.criteria && (
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
                    {check.criteria}
                </div>
            )}
        </div>
    );
};

const toolbarButtonStyle = (primary = false) => ({
    padding: '0.4rem 0.8rem',
    background: primary ? 'var(--accent-primary)' : 'var(--bg-primary)',
    border: primary ? 'none' : '1px solid var(--border-color)',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.3rem',
    fontSize: '0.85rem',
    color: primary ? 'white' : 'var(--text-secondary)',
    fontWeight: primary ? 600 : 400,
});

const addButtonStyle = {
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
};

const commentTextareaStyle = {
    width: '100%',
    minHeight: '96px',
    resize: 'vertical',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    fontFamily: 'inherit',
    fontSize: '0.88rem',
    lineHeight: 1.45,
    padding: '0.65rem',
    outlineColor: 'var(--accent-primary)',
};

export default WikiScriptEditor;
