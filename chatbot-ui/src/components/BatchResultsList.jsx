import React, { useState, useRef } from 'react';
import { FileText, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import ComplianceReport from './ComplianceReport';

/**
 * BatchResultsList - Displays a list of batch compliance results
 * with expandable rows to view individual reports.
 */
const BatchResultsList = ({ batchResults, batchSummary }) => {
    // Use a Set to allow multiple reports open at the same time
    const [expandedIndices, setExpandedIndices] = useState(new Set());

    // Refs for each row to enable scrollIntoView
    const rowRefs = useRef({});

    if (!batchResults || batchResults.length === 0) {
        return null;
    }

    const toggleExpand = (index) => {
        const wasExpanded = expandedIndices.has(index);

        setExpandedIndices(prev => {
            const newSet = new Set(prev);
            if (newSet.has(index)) {
                newSet.delete(index);
            } else {
                newSet.add(index);
            }
            return newSet;
        });

        // If expanding (not collapsing), scroll the row into view after a short delay
        if (!wasExpanded) {
            setTimeout(() => {
                rowRefs.current[index]?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }, 50);
        }
    };

    const isExpanded = (index) => expandedIndices.has(index);

    const getStatusIcon = (result) => {
        const failed = result?.summary?.ai_failed || 0;
        if (failed === 0) {
            return <CheckCircle2 size={18} style={{ color: 'var(--accent-success, #22c55e)' }} />;
        }
        return <AlertTriangle size={18} style={{ color: 'var(--accent-warning, #f59e0b)' }} />;
    };

    const getStatusText = (result) => {
        const passed = result?.summary?.ai_passed || 0;
        const failed = result?.summary?.ai_failed || 0;
        return `${passed} passed, ${failed} issues`;
    };

    return (
        <div style={{
            marginTop: '1rem',
            border: '1px solid var(--border-color)',
            borderRadius: '0.75rem',
            overflow: 'hidden',
            background: 'var(--bg-secondary)'
        }}>
            {/* Header */}
            <div style={{
                padding: '0.75rem 1rem',
                background: 'var(--bg-tertiary)',
                borderBottom: '1px solid var(--border-color)',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <span>Scripts ({batchResults.length})</span>
                <span style={{
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)',
                    fontWeight: 400
                }}>
                    Click to view report
                </span>
            </div>

            {/* Rows */}
            {batchResults.map((result, index) => (
                <div key={index} ref={el => rowRefs.current[index] = el}>
                    {/* Row */}
                    <div
                        onClick={() => toggleExpand(index)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            padding: '0.875rem 1rem',
                            borderBottom: index === batchResults.length - 1 && !isExpanded(index)
                                ? 'none'
                                : '1px solid var(--border-color)',
                            cursor: 'pointer',
                            background: isExpanded(index) ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                            transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={(e) => {
                            if (!isExpanded(index)) {
                                e.currentTarget.style.background = 'var(--bg-tertiary)';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (!isExpanded(index)) {
                                e.currentTarget.style.background = 'var(--bg-secondary)';
                            }
                        }}
                    >
                        {/* Status Icon */}
                        <div style={{ marginRight: '0.75rem' }}>
                            {getStatusIcon(result)}
                        </div>

                        {/* Filename */}
                        <div style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            minWidth: 0
                        }}>
                            <FileText size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                            <span style={{
                                fontSize: '0.9rem',
                                color: 'var(--text-primary)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                            }}>
                                {result.filename || `Script ${index + 1}`}
                            </span>
                        </div>

                        {/* Status Text */}
                        <div style={{
                            fontSize: '0.8rem',
                            color: 'var(--text-secondary)',
                            marginRight: '0.75rem'
                        }}>
                            {getStatusText(result)}
                        </div>

                        {/* Expand Icon */}
                        <div style={{ color: 'var(--text-tertiary)' }}>
                            {isExpanded(index)
                                ? <ChevronUp size={18} />
                                : <ChevronDown size={18} />
                            }
                        </div>
                    </div>

                    {/* Expanded Report */}
                    {isExpanded(index) && (
                        <div style={{
                            padding: '1rem',
                            background: 'var(--bg-primary)',
                            borderBottom: index === batchResults.length - 1
                                ? 'none'
                                : '1px solid var(--border-color)'
                        }}>
                            <ComplianceReport
                                report={result}
                                isOpen={true}
                                onToggle={() => { }}
                            />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default BatchResultsList;
