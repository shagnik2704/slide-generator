import React from 'react';
import { X, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

/**
 * ComplianceReport - Modal component showing checklist-style compliance results
 */
const ComplianceReport = ({ report, onClose }) => {
    if (!report) return null;

    const { formatting, narration, structure, total_violations } = report;

    const renderCheck = (check) => {
        const { rule, passed, violations } = check;
        return (
            <div key={rule} style={{ marginBottom: '0.75rem' }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    color: passed ? 'var(--success-color, #22c55e)' : 'var(--error-color, #ef4444)'
                }}>
                    {passed ? (
                        <CheckCircle size={18} />
                    ) : (
                        <XCircle size={18} />
                    )}
                    <span style={{ fontWeight: 500 }}>{rule}</span>
                </div>

                {!passed && violations && violations.length > 0 && (
                    <div style={{
                        marginLeft: '1.75rem',
                        marginTop: '0.25rem',
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)'
                    }}>
                        {violations.slice(0, 3).map((v, i) => (
                            <div key={i} style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '0.5rem',
                                marginBottom: '0.25rem'
                            }}>
                                <span style={{ color: 'var(--text-tertiary)' }}>└─</span>
                                <span>
                                    {v.slide > 0 && <strong>Slide {v.slide}:</strong>} {v.issue}
                                    {v.text && (
                                        <span style={{
                                            display: 'block',
                                            fontStyle: 'italic',
                                            color: 'var(--text-tertiary)',
                                            marginTop: '0.1rem'
                                        }}>
                                            "{v.text}"
                                        </span>
                                    )}
                                </span>
                            </div>
                        ))}
                        {violations.length > 3 && (
                            <div style={{
                                marginLeft: '1.25rem',
                                color: 'var(--text-tertiary)',
                                fontStyle: 'italic'
                            }}>
                                ... and {violations.length - 3} more
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    const renderCategory = (title, checks) => {
        if (!checks) return null;
        return (
            <div style={{ marginBottom: '1.25rem' }}>
                <h3 style={{
                    fontSize: '0.9rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--text-secondary)',
                    marginBottom: '0.75rem',
                    paddingBottom: '0.5rem',
                    borderBottom: '1px solid var(--border-color)'
                }}>
                    {title}
                </h3>
                {Object.values(checks).map(renderCheck)}
            </div>
        );
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem'
        }}>
            <div style={{
                backgroundColor: 'var(--bg-primary)',
                borderRadius: '1rem',
                width: '100%',
                maxWidth: '600px',
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: 'var(--shadow-lg)'
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1rem 1.25rem',
                    borderBottom: '1px solid var(--border-color)'
                }}>
                    <h2 style={{
                        margin: 0,
                        fontSize: '1.1rem',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        📋 Script Compliance Report
                    </h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '0.25rem',
                            color: 'var(--text-secondary)',
                            borderRadius: '0.25rem'
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div style={{
                    padding: '1.25rem',
                    overflowY: 'auto',
                    flex: 1
                }}>
                    {renderCategory('Formatting', formatting)}
                    {renderCategory('Narration', narration)}
                    {renderCategory('Structure', structure)}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '1rem 1.25rem',
                    borderTop: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        color: total_violations === 0 ? 'var(--success-color, #22c55e)' : 'var(--warning-color, #f59e0b)',
                        fontWeight: 500
                    }}>
                        {total_violations === 0 ? (
                            <>
                                <CheckCircle size={18} />
                                All checks passed!
                            </>
                        ) : (
                            <>
                                <AlertCircle size={18} />
                                {total_violations} violation{total_violations !== 1 ? 's' : ''} found
                            </>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '0.5rem 1rem',
                            backgroundColor: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            cursor: 'pointer',
                            fontWeight: 500
                        }}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ComplianceReport;
