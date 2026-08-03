import React, { useState } from 'react';
import {
    CheckCircle2,
    Circle,
    Loader2,
    AlertCircle,
    ChevronDown,
    ChevronUp,
    Image,
    Mic,
    Languages,
    Presentation,
    FileText,
    ShieldCheck,
    ClipboardCheck,
    ListChecks,
    Globe,
    Clock
} from 'lucide-react';
import ImageWorkflow from './ImageWorkflow';
import VoicePreview from './VoicePreview';
import TranslationResults from './TranslationResults';
import SlidesPreview from './SlidesPreview';
import SlideThemePicker from './SlideThemePicker';
import BatchResultsList from './BatchResultsList';
import QualityReport from './QualityReport';
import TimedScriptResults from './TimedScriptResults';
import {
    ScriptUploadedActions,
    ScriptReviewActions,
    MediaWikiExportActions
} from './message-actions';

/**
 * WorkflowCard - A lifecycle-aware component that handles tool processing states.
 * Replaces multiple chat bubbles with a single, updating card.
 */
const WorkflowCard = ({
    workflow,
    isTyping,
    openReportId,
    setOpenReportId,
    openQualityId,
    setOpenQualityId,
    qualityReports,
    isQualityLoading,
    onQualityCheck,
    onUpdateComplianceReport,
    // Script-related props
    openEditorId,
    setOpenEditorId,
    onDownloadScriptDocx,
    onSaveScriptEdit,
    onGenerateSlides
}) => {
    const [isOpen, setIsOpen] = useState(true);

    if (!workflow) return null;

    const { tool, status, steps, currentStep, result, error } = workflow;

    // Icon Mapping
    const icons = {
        images: <Image size={18} />,
        voice: <Mic size={18} />,
        translation: <Languages size={18} />,
        slides_translation: <Languages size={18} />,
        slides: <Presentation size={18} />,
        compliance: <ShieldCheck size={18} />,
        quality: <ListChecks size={18} />,
        quality_check: <Globe size={18} />,
        batch_compliance: <ClipboardCheck size={18} />,
        batch_quality: <ListChecks size={18} />,
        script: <FileText size={18} />,
        timed_script: <Clock size={18} />,
        mediawiki_export: <Globe size={18} />,
        default: <FileText size={18} />
    };

    const titles = {
        images: 'Image Generation',
        voice: 'Voice Generation',
        translation: 'Script Translation',
        slides_translation: 'Slides Translation',
        slides: 'Slides Generation',
        compliance: 'Admin Compliance Check',
        quality: 'Quality Compliance Review',
        quality_check: 'Quality Compliance Check',
        batch_compliance: 'Batch Compliance Check',
        batch_quality: 'Batch Quality Review',
        script: 'Script Generation',
        timed_script: 'Timed Script Generation',
        mediawiki_export: 'MediaWiki Conversion'
    };

    // Calculate Progress
    const progress = status === 'complete'
        ? 100
        : Math.round(((currentStep) / steps.length) * 100);

    const containerStyle = {
        marginTop: '1rem',
        border: status === 'complete' ? 'none' : '1px solid var(--border-color)',
        borderRadius: '16px',
        overflow: status === 'complete' ? 'visible' : 'hidden',
        background: status === 'complete' ? 'transparent' : 'var(--bg-secondary)',
        boxShadow: status === 'complete' ? 'none' : 'var(--shadow-sm)',
        transition: 'all 0.3s ease',
    };

    const headerStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.875rem 1.25rem',
        cursor: 'pointer',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        transition: 'all 0.2s ease',
        marginBottom: isOpen && status === 'complete' ? '1rem' : '0',
    };

    const contentStyle = {
        padding: status === 'complete' ? '0' : '1.5rem',
        background: status === 'complete' ? 'transparent' : 'var(--bg-primary)',
        borderRadius: '12px',
        marginTop: status === 'processing' ? '0' : '0',
    };

    return (
        <div style={containerStyle}>
            {/* Header */}
            <div
                className="workflow-header"
                style={headerStyle}
                onClick={() => setIsOpen(!isOpen)}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ color: 'var(--accent-primary)', display: 'flex' }}>
                        {icons[tool] || icons.default}
                    </span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {titles[tool] || 'Process'}
                    </span>
                    {workflow.filename && (
                        <span style={{
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)',
                            marginLeft: '0.5rem',
                            paddingLeft: '0.75rem',
                            borderLeft: '1px solid var(--border-color)'
                        }}>
                            {workflow.filename}
                        </span>
                    )}
                    {status === 'complete' && (
                        <CheckCircle2 size={16} style={{ color: '#34a853', marginLeft: '0.25rem' }} />
                    )}
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>
                    {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
            </div>

            {/* Body */}
            {isOpen && (
                <div style={contentStyle}>
                    {(status === 'processing' || status === 'awaiting_color') && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {/* Steps List */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {steps.map((step, idx) => {
                                    const isDone = idx < currentStep;
                                    const isCurrent = idx === currentStep;

                                    return (
                                        <div key={idx} style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.75rem',
                                            opacity: isDone || isCurrent ? 1 : 0.4
                                        }}>
                                            {isDone ? (
                                                <CheckCircle2 size={18} style={{ color: '#34a853' }} />
                                            ) : isCurrent ? (
                                                <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
                                            ) : (
                                                <Circle size={18} style={{ color: 'var(--text-secondary)' }} />
                                            )}
                                            <span style={{
                                                fontSize: '0.9rem',
                                                color: isCurrent ? 'var(--text-primary)' : 'var(--text-secondary)',
                                                fontWeight: isCurrent ? 500 : 400
                                            }}>
                                                {step.label}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Progress Bar Container */}
                            <div style={{ marginTop: '0.5rem' }}>
                                <div style={{
                                    height: '6px',
                                    background: 'var(--border-color)',
                                    borderRadius: '3px',
                                    overflow: 'hidden',
                                    position: 'relative'
                                }}>
                                    <div style={{
                                        width: `${progress}%`,
                                        height: '100%',
                                        background: 'var(--accent-primary)',
                                        transition: 'width 0.5s ease-in-out',
                                        position: 'absolute'
                                    }} />
                                </div>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'flex-end',
                                    marginTop: '0.5rem',
                                    fontSize: '0.75rem',
                                    color: 'var(--text-secondary)'
                                }}>
                                    {progress}% Complete
                                </div>
                            </div>
                        </div>
                    )}

                    {status === 'awaiting_color' && tool === 'slides' && (
                        <div style={{
                            marginTop: '1rem',
                            paddingTop: '1rem',
                            borderTop: '1px solid var(--border-color)'
                        }}>
                            <SlideThemePicker isOpen={true} />
                            <button
                                onClick={() => onGenerateSlides?.(workflow.id, workflow.pendingParse, workflow.filename)}
                                style={{
                                    marginTop: '0.75rem',
                                    width: '100%',
                                    padding: '0.7rem 1.25rem',
                                    borderRadius: '8px',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem',
                                    fontWeight: 600,
                                    background: 'var(--accent-primary)',
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.5rem'
                                }}
                            >
                                <Presentation size={18} />
                                Generate slides
                            </button>
                        </div>
                    )}

                    {status === 'error' && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            color: '#d93025',
                            padding: '1rem',
                            background: '#fce8e6',
                            borderRadius: '8px'
                        }}>
                            <AlertCircle size={20} />
                            <span style={{ fontSize: '0.9rem' }}>{error || 'Something went wrong.'}</span>
                        </div>
                    )}

                    {status === 'complete' && result && (
                        <div style={{ animation: 'fadeIn 0.5s ease' }}>
                            {tool === 'images' && (
                                <ImageWorkflow
                                    enhancedPrompts={result.enhancedPrompts}
                                    projectId={result.projectId}
                                />
                            )}
                            {tool === 'voice' && (
                                <VoicePreview voiceData={result.voiceData} />
                            )}
                            {tool === 'translation' && (
                                <TranslationResults results={result.translationResults} />
                            )}
                            {tool === 'slides' && (
                                <SlidesPreview slidesData={result.slidesData} />
                            )}
                            {tool === 'batch_compliance' && (
                                <BatchResultsList
                                    batchResults={result.batchResults}
                                    batchSummary={result.batchSummary}
                                    type="compliance"
                                />
                            )}
                            {tool === 'batch_quality' && (
                                <BatchResultsList
                                    batchResults={result.batchResults}
                                    batchSummary={result.batchSummary}
                                    type="quality"
                                />
                            )}
                            {(tool === 'compliance' || tool === 'quality') && (
                                <ScriptUploadedActions
                                    msg={{ ...result, id: workflow.id, filename: workflow.filename }}
                                    isTyping={isTyping}
                                    openReportId={openReportId}
                                    setOpenReportId={setOpenReportId}
                                    openQualityId={openQualityId}
                                    setOpenQualityId={setOpenQualityId}
                                    qualityReports={qualityReports}
                                    isQualityLoading={isQualityLoading}
                                    onQualityCheck={onQualityCheck}
                                    onUpdateComplianceReport={onUpdateComplianceReport}
                                />
                            )}
                            {tool === 'quality_check' && result.qualityReport && (
                                <QualityReport
                                    report={result.qualityReport}
                                    isOpen={true}
                                    onClose={() => { }}
                                />
                            )}
                            {tool === 'script' && (
                                <ScriptReviewActions
                                    msg={{
                                        id: workflow.id,
                                        jsonScript: result.jsonScript,
                                        projectId: result.projectId,
                                        type: 'script_review'
                                    }}
                                    isTyping={isTyping}
                                    openEditorId={openEditorId}
                                    setOpenEditorId={setOpenEditorId}
                                    onDownloadScriptDocx={onDownloadScriptDocx}
                                    onSaveScriptEdit={onSaveScriptEdit}
                                />
                            )}
                            {tool === 'timed_script' && (
                                <TimedScriptResults
                                    timedScriptData={result.timedScriptData}
                                    filename={workflow.filename}
                                />
                            )}
                            {tool === 'mediawiki_export' && (
                                <MediaWikiExportActions
                                    msg={{
                                        ...result,
                                        id: workflow.id
                                    }}
                                />
                            )}
                            {tool === 'slides_translation' && result.slidesTranslation && (
                                <div style={{
                                    padding: '1.25rem',
                                    background: 'var(--bg-secondary)',
                                    borderRadius: '12px',
                                    border: '1px solid var(--border-color)'
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        marginBottom: '1rem'
                                    }}>
                                        <div>
                                            <div style={{
                                                fontWeight: 600,
                                                color: 'var(--text-primary)',
                                                marginBottom: '0.25rem'
                                            }}>
                                                Translated to {result.slidesTranslation.language_name}
                                            </div>
                                            <div style={{
                                                fontSize: '0.85rem',
                                                color: 'var(--text-secondary)'
                                            }}>
                                                XeLaTeX format with {result.slidesTranslation.font_name} font
                                            </div>
                                        </div>
                                        <a
                                            href={result.slidesTranslation.download_url}
                                            download={result.slidesTranslation.filename}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                padding: '0.625rem 1rem',
                                                background: 'var(--accent-primary)',
                                                color: 'white',
                                                borderRadius: '8px',
                                                textDecoration: 'none',
                                                fontWeight: 500,
                                                fontSize: '0.9rem',
                                                transition: 'all 0.2s ease'
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.background = 'var(--accent-secondary)';
                                                e.currentTarget.style.transform = 'translateY(-1px)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.background = 'var(--accent-primary)';
                                                e.currentTarget.style.transform = 'translateY(0)';
                                            }}
                                        >
                                            <Presentation size={16} />
                                            Download .tex
                                        </a>
                                    </div>
                                    <div style={{
                                        padding: '0.75rem 1rem',
                                        background: 'rgba(251, 191, 36, 0.1)',
                                        border: '1px solid rgba(251, 191, 36, 0.3)',
                                        borderRadius: '8px',
                                        fontSize: '0.85rem',
                                        color: 'var(--text-secondary)'
                                    }}>
                                        <strong style={{ color: 'var(--text-primary)' }}>Note:</strong> Compile with <code style={{
                                            background: 'var(--bg-tertiary)',
                                            padding: '0.125rem 0.375rem',
                                            borderRadius: '4px',
                                            fontFamily: 'monospace'
                                        }}>xelatex</code> instead of pdflatex
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            <style>{`
                .workflow-header:hover {
                    background: var(--bg-tertiary) !important;
                    border-color: var(--accent-primary) !important;
                    box-shadow: var(--shadow-sm);
                }
                .animate-spin {
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default WorkflowCard;
