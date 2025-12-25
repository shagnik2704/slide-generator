import React, { useState, useRef, useEffect } from 'react';
import { X, Save, Download, RotateCcw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Editable cell using contentEditable - exactly like WikiScriptEditor
 */
const WikiCell = ({ value, onChange, width }) => {
    const cellRef = useRef(null);
    const [isFocused, setIsFocused] = useState(false);

    useEffect(() => {
        if (cellRef.current && !isFocused) {
            cellRef.current.innerText = value || '';
        }
    }, [value, isFocused]);

    const handleBlur = () => {
        setIsFocused(false);
        if (cellRef.current) {
            const newValue = cellRef.current.innerText;
            if (newValue !== value) {
                onChange(newValue);
            }
        }
    };

    return (
        <td
            ref={cellRef}
            contentEditable={true}
            onBlur={handleBlur}
            onFocus={() => setIsFocused(true)}
            style={{
                padding: '0.4em 0.6em',
                border: '1px solid #a2a9b1',
                verticalAlign: 'top',
                backgroundColor: '#ffffff',
                width: width,
                minHeight: '2em',
                outline: isFocused ? '2px solid #36c' : 'none',
                outlineOffset: '-2px',
                cursor: 'text',
                lineHeight: '1.6',
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
            background: '#fff',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            overflow: 'hidden',
        }}>
            {/* Toolbar - Exactly like WikiScriptEditor */}
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
                        Compliance Report
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        color: '#54595d',
                        background: '#eaecf0',
                        padding: '0.2em 0.6em',
                        borderRadius: '3px',
                    }}>
                        {checks.length} checks
                    </span>
                    <span style={{
                        fontSize: '0.85em',
                        background: '#eaecf0',
                        padding: '0.2em 0.6em',
                        borderRadius: '3px',
                    }}>
                        <span style={{ color: '#14866d' }}>{summary?.ai_passed || 0} ✓</span>
                        {' · '}
                        <span style={{ color: '#d33' }}>{summary?.ai_failed || 0} ✗</span>
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
                    <button
                        onClick={handleDownloadDocx}
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
                        <Download size={14} />
                        DOCX
                    </button>
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
                    minWidth: '900px',
                    borderCollapse: 'collapse',
                    fontFamily: 'Arial, sans-serif',
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
                                width: '40px',
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
                                Criteria
                            </th>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '60px',
                                textAlign: 'center',
                            }}>
                                AI
                            </th>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '30%',
                            }}>
                                AI Notes
                            </th>
                            <th style={{
                                padding: '0.4em 0.6em',
                                border: '1px solid #a2a9b1',
                                backgroundColor: '#eaecf0',
                                fontWeight: 'bold',
                                width: '25%',
                            }}>
                                Human Review
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {checks.map((check, index) => (
                            <tr key={check.id || index}>
                                {/* Row Number */}
                                <td style={{
                                    padding: '0.4em 0.6em',
                                    border: '1px solid #a2a9b1',
                                    backgroundColor: '#f8f9fa',
                                    textAlign: 'center',
                                    fontWeight: 600,
                                    color: '#202122',
                                }}>
                                    {index + 1}
                                </td>
                                {/* Criteria - Read only */}
                                <td style={{
                                    padding: '0.4em 0.6em',
                                    border: '1px solid #a2a9b1',
                                    verticalAlign: 'top',
                                    backgroundColor: '#fff',
                                }}>
                                    {check.criteria}
                                </td>
                                {/* AI Status - Tick/Cross */}
                                <td style={{
                                    padding: '0.4em 0.6em',
                                    border: '1px solid #a2a9b1',
                                    textAlign: 'center',
                                    verticalAlign: 'middle',
                                    backgroundColor: check.ai_review === true ? '#e6f9e6' :
                                        check.ai_review === false ? '#fee' : '#fff',
                                    fontSize: '1.2em',
                                }}>
                                    {check.ai_review === true ? (
                                        <span style={{ color: '#14866d' }}>✓</span>
                                    ) : check.ai_review === false ? (
                                        <span style={{ color: '#d33' }}>✗</span>
                                    ) : (
                                        <span style={{ color: '#54595d' }}>—</span>
                                    )}
                                </td>
                                {/* AI Notes - Editable */}
                                <WikiCell
                                    value={check.ai_notes || ''}
                                    onChange={(value) => updateCheck(index, 'ai_notes', value)}
                                    width="30%"
                                />
                                {/* Human Review - Editable */}
                                <WikiCell
                                    value={check.human_review || ''}
                                    onChange={(value) => updateCheck(index, 'human_review', value)}
                                    width="25%"
                                />
                            </tr>
                        ))}
                    </tbody>
                </table>

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
                    <strong>Tips:</strong> ✓ = AI passed, ✗ = AI failed. Click AI Notes or Human Review cells to edit.
                </div>
            </div>
        </div>
    );
};

export default ComplianceReport;
