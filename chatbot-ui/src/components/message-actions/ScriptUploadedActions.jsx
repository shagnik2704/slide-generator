import React from 'react';
import { ClipboardCheck, Languages } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import QualityReport from '../QualityReport';

const ADMIN_COMPLIANCE_REVIEW_STORAGE_KEY = 'adminComplianceReviewPayload';

/**
 * Action buttons for messages with type === 'script_uploaded'
 */
export default function ScriptUploadedActions({
    msg,
    openQualityId,
    setOpenQualityId,
    qualityReports,
    isQualityLoading,
    onQualityCheck,
    onOpenQualityModal,  // New: Opens the language selection modal
}) {
    const navigate = useNavigate();

    const openComplianceReview = () => {
        const payload = {
            report: msg.complianceReport,
            jsonScript: msg.jsonScript,
            filename: msg.filename,
            projectId: msg.projectId,
        };

        window.sessionStorage.setItem(
            ADMIN_COMPLIANCE_REVIEW_STORAGE_KEY,
            JSON.stringify(payload)
        );
        navigate('/admin-compliance-review', { state: payload });
    };

    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {/* View Report Button */}
            {msg.complianceReport && (
                <button
                    onClick={openComplianceReview}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: 'var(--accent-primary)',
                        color: 'white',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.75rem',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                >
                    <ClipboardCheck size={18} />
                    Open Review Workspace
                </button>
            )}

            {/* View Quality Report Toggle - for sidebar quality flow */}
            {(qualityReports[msg.id] || msg.qualityReport) && msg.hideQualityCheck && (
                <button
                    onClick={() => setOpenQualityId(openQualityId === msg.id ? null : msg.id)}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: 'var(--accent-primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.75rem',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                        boxShadow: 'var(--shadow-md)',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(26, 68, 128, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                >
                    {openQualityId === msg.id ? 'Close Quality Report' : 'View Quality Report'}
                </button>
            )}

            {/* Quality Check Button - opens language selection modal */}
            {!msg.hideQualityCheck && (
                <button
                    onClick={() => {
                        if (openQualityId === msg.id) {
                            setOpenQualityId(null);
                        } else if (qualityReports[msg.id] || msg.qualityReport) {
                            setOpenQualityId(msg.id);
                        } else if (onOpenQualityModal) {
                            // Open language selection modal
                            onOpenQualityModal(msg);
                        } else {
                            // Fallback: Direct Hindi quality check (backward compatibility)
                            onQualityCheck(msg.jsonScript, msg.id);
                        }
                    }}
                    disabled={isQualityLoading && openQualityId === msg.id}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: openQualityId === msg.id
                            ? 'var(--accent-primary)'
                            : 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
                        color: openQualityId === msg.id ? 'white' : 'var(--text-primary)',
                        border: '1px solid var(--accent-primary)',
                        borderRadius: '0.75rem',
                        cursor: isQualityLoading ? 'wait' : 'pointer',
                        fontWeight: 600,
                        fontSize: '1rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all 0.3s ease',
                        marginTop: '0.5rem',
                    }}
                    onMouseEnter={(e) => {
                        if (!isQualityLoading) {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                >
                    <Languages size={18} />
                    {isQualityLoading && openQualityId === msg.id
                        ? 'Checking...'
                        : openQualityId === msg.id
                            ? 'Close Quality'
                            : 'Quality Check'}
                </button>
            )}

            {/* Inline Quality Report */}
            <QualityReport
                report={qualityReports[msg.id] || msg.qualityReport}
                isOpen={openQualityId === msg.id && !isQualityLoading}
                onClose={() => setOpenQualityId(null)}
            />
        </div>
    );
}
