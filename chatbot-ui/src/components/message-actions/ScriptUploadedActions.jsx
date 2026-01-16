import React, { useState } from 'react';
import { FileText, Languages } from 'lucide-react';
import ComplianceReport from '../ComplianceReport';
import QualityReport from '../QualityReport';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

/**
 * Action buttons for messages with type === 'script_uploaded'
 */
export default function ScriptUploadedActions({
    msg,
    isTyping,
    openReportId,
    setOpenReportId,
    openQualityId,
    setOpenQualityId,
    qualityReports,
    isQualityLoading,
    onGenerateSlides,
    onQualityCheck,
    onOpenQualityModal,  // New: Opens the language selection modal
    onUpdateComplianceReport,
}) {
    return (
        <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {/* View Report Button */}
            {msg.complianceReport && (
                <button
                    onClick={() => setOpenReportId(openReportId === msg.id ? null : msg.id)}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: openReportId === msg.id ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                        color: openReportId === msg.id ? 'white' : 'var(--text-primary)',
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
                    📋 {openReportId === msg.id ? 'Close Report' : 'View Report'}
                </button>
            )}

            {/* Inline Compliance Report */}
            <ComplianceReport
                report={msg.complianceReport}
                isOpen={openReportId === msg.id}
                onSave={(updated) => onUpdateComplianceReport(msg.id, updated)}
                onClose={() => setOpenReportId(null)}
            />

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
