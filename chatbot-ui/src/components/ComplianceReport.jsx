import React, { useState, useRef, useEffect } from 'react';
import { X, Save, Download, RotateCcw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Editable cell using contentEditable - exactly like WikiScriptEditor
 */
const WikiCell = ({ value, onChange, width, placeholder, style = {} }) => {
    const cellRef = useRef(null);
    const [isFocused, setIsFocused] = useState(false);

    useEffect(() => {
        if (cellRef.current && !isFocused) {
            cellRef.current.innerText = value || '';
            // Show placeholder when empty
            if (!value && placeholder) {
                cellRef.current.style.color = 'var(--text-secondary)';
                cellRef.current.innerText = placeholder;
            } else {
                cellRef.current.style.color = 'var(--text-primary)';
            }
        }
    }, [value, isFocused, placeholder]);

    const handleBlur = () => {
        setIsFocused(false);
        if (cellRef.current) {
            const newValue = cellRef.current.innerText;
            // Remove placeholder text if it's the placeholder
            if (newValue === placeholder) {
                cellRef.current.innerText = '';
                onChange('');
            } else if (newValue !== value) {
                onChange(newValue);
            }
        }
    };

    const handleFocus = () => {
        setIsFocused(true);
        if (cellRef.current && cellRef.current.innerText === placeholder) {
            cellRef.current.innerText = '';
            cellRef.current.style.color = 'var(--text-primary)';
        }
    };

    return (
        <td
            ref={cellRef}
            contentEditable={true}
            onBlur={handleBlur}
            onFocus={handleFocus}
            style={{
                padding: '0.75rem 1rem',
                border: '1px solid var(--border-color)',
                verticalAlign: 'top',
                backgroundColor: 'transparent',
                width: width,
                minHeight: '2.5rem',
                outline: isFocused ? '2px solid var(--accent-primary)' : 'none',
                outlineOffset: '-2px',
                cursor: 'text',
                lineHeight: '1.6',
                color: value ? 'var(--text-primary)' : 'var(--text-secondary)',
                ...style,
            }}
            suppressContentEditableWarning={true}
        />
    );
};

/**
 * WikiComplianceReport - INLINE card (NOT a modal)
 * Matches WikiScriptEditor styling exactly
 * Uses isOpen prop to control visibility
 */
const ComplianceReport = ({ report, isOpen, onClose, onSave }) => {
    const [checks, setChecks] = useState([]);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalChecks, setOriginalChecks] = useState([]);

    useEffect(() => {
        if (report?.checks) {
            const checksCopy = JSON.parse(JSON.stringify(report.checks));
            setChecks(checksCopy);
            setOriginalChecks(checksCopy);
            setHasChanges(false);
        }
    }, [report]);

    // Don't render if not open or no report
    if (!isOpen || !report) return null;

    const { summary } = report;

    const updateCheck = (index, field, value) => {
        const updated = [...checks];
        updated[index] = { ...updated[index], [field]: value };
        setChecks(updated);
        setHasChanges(true);
    };

    const handleSave = () => {
        if (onSave) {
            onSave({ ...report, checks });
        }
        setOriginalChecks(JSON.parse(JSON.stringify(checks)));
        setHasChanges(false);
    };

    const handleReset = () => {
        if (window.confirm('Discard all changes?')) {
            setChecks(JSON.parse(JSON.stringify(originalChecks)));
            setHasChanges(false);
        }
    };

    const handleDownloadDocx = async () => {
        try {
            const response = await fetch(`${API_URL}/export_compliance_report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checks: checks,
                    summary: summary,
                    format: 'docx'
                })
            });

            if (!response.ok) throw new Error('Failed to generate DOCX');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'compliance_report.docx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('DOCX download error:', error);
            alert('Failed to download. Is the backend running?');
        }
    };

    return (
        <div style={{
            marginTop: '1rem',
            background: 'var(--bg-primary)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
            border: '1px solid var(--border-color)',
        }}>
            {/* Toolbar - Exactly like WikiScriptEditor */}
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
                        Compliance Report
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: 'var(--text-secondary)',
                        background: 'var(--bg-tertiary)',
                        padding: '0.2em 0.6em',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)'
                    }}>
                        {checks.length} checks
                    </span>
                    <div style={{
                        fontSize: '0.85em',
                        background: 'var(--bg-tertiary)',
                        padding: '0.2em 0.6em',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        display: 'flex',
                        gap: '0.75rem'
                    }}>
                        <span style={{ color: '#34a853', fontWeight: 600 }}>{summary?.ai_passed || 0} ✓</span>
                        <span style={{ width: '1px', background: 'var(--border-color)' }}></span>
                        <span style={{ color: '#d93025', fontWeight: 600 }}>{summary?.ai_failed || 0} ✗</span>
                    </div>
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
                    <button
                        onClick={handleDownloadDocx}
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
                            color: 'var(--text-primary)',
                            fontWeight: 500,
                        }}
                    >
                        <Download size={14} />
                        DOCX
                    </button>
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
                background: 'var(--bg-primary, #fff)',
            }}>
                <table style={{
                    width: '100%',
                    minWidth: '900px',
                    borderCollapse: 'separate',
                    borderSpacing: '0',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    border: '1px solid var(--border-color, #a2a9b1)',
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
                                width: '40px',
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
                                Criteria
                            </th>
                            <th style={{
                                padding: '0.75rem',
                                borderRight: '1px solid var(--border-color)',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                width: '60px',
                                textAlign: 'center',
                                color: 'var(--text-primary)',
                            }}>
                                AI
                            </th>
                            <th style={{
                                padding: '0.75rem',
                                borderRight: '1px solid var(--border-color)',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                width: '30%',
                                color: 'var(--text-primary)',
                                textAlign: 'left'
                            }}>
                                AI Notes
                            </th>
                            <th style={{
                                padding: '0.75rem',
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: 'var(--bg-secondary)',
                                fontWeight: 'bold',
                                width: '25%',
                                color: 'var(--text-primary)',
                                textAlign: 'left'
                            }}>
                                Human Review
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {checks.map((check, index) => {
                            const isFailed = check.ai_review === false;
                            const isLast = index === checks.length - 1;
                            return (
                                <tr
                                    key={check.id || index}
                                    style={{
                                        backgroundColor: isFailed ? 'rgba(217, 48, 37, 0.05)' : 'transparent',
                                    }}
                                >
                                    {/* Row Number */}
                                    <td style={{
                                        padding: '0.75rem',
                                        borderRight: '1px solid var(--border-color)',
                                        borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
                                        backgroundColor: isFailed ? 'rgba(217, 48, 37, 0.08)' : 'var(--bg-secondary)',
                                        textAlign: 'center',
                                        fontWeight: 600,
                                        color: 'var(--text-primary)',
                                    }}>
                                        {index + 1}
                                    </td>
                                    {/* Criteria - Read only */}
                                    <td style={{
                                        padding: '0.75rem',
                                        borderRight: '1px solid var(--border-color)',
                                        borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
                                        verticalAlign: 'top',
                                        color: 'var(--text-primary)',
                                        fontWeight: isFailed ? 600 : 400,
                                    }}>
                                        {check.criteria}
                                    </td>
                                    {/* AI Status - Tick/Cross */}
                                    <td style={{
                                        padding: '0.75rem',
                                        borderRight: '1px solid var(--border-color)',
                                        borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
                                        textAlign: 'center',
                                        verticalAlign: 'middle',
                                        backgroundColor: check.ai_review === true ? 'rgba(52, 168, 83, 0.1)' :
                                            check.ai_review === false ? 'rgba(217, 48, 37, 0.15)' : 'transparent',
                                        fontSize: '1.3em',
                                        fontWeight: 'bold',
                                    }}>
                                        {check.ai_review === true ? (
                                            <span style={{ color: '#34a853' }}>✓</span>
                                        ) : check.ai_review === false ? (
                                            <span style={{ color: '#d93025' }}>✗</span>
                                        ) : (
                                            <span style={{ color: 'var(--text-secondary)' }}>—</span>
                                        )}
                                    </td>
                                    {/* AI Notes - Editable */}
                                    <WikiCell
                                        value={check.ai_notes || ''}
                                        onChange={(value) => updateCheck(index, 'ai_notes', value)}
                                        width="30%"
                                        placeholder={isFailed && !check.ai_notes ? 'Click to see why this failed...' : 'No notes'}
                                        style={{ borderBottom: isLast ? 'none' : '1px solid var(--border-color)' }}
                                    />
                                    {/* Human Review - Editable */}
                                    <WikiCell
                                        value={check.human_review || ''}
                                        onChange={(value) => updateCheck(index, 'human_review', value)}
                                        width="25%"
                                        placeholder="Add your review..."
                                        style={{ borderBottom: isLast ? 'none' : '1px solid var(--border-color)' }}
                                    />
                                </tr>
                            );
                        })}
                    </tbody>
                </table>

                {/* Help text */}
                <div style={{
                    marginTop: '1.25rem',
                    padding: '1rem',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Tips:</strong>
                    {' '}<span style={{ color: '#34a853', fontWeight: 600 }}>✓</span> = AI passed,
                    {' '}<span style={{ color: '#d93025', fontWeight: 600 }}>✗</span> = AI failed (highlighted in red).
                    Failed checks show detailed notes explaining why they failed. Click AI Notes or Human Review cells to edit.
                </div>
            </div>
        </div>
    );
};

export default ComplianceReport;
