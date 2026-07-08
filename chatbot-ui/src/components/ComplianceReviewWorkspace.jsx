import React, { useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import {
    AlertTriangle,
    CheckCircle2,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    ChevronUp,
    CircleDashed,
    Download,
    ListChecks,
    X,
} from 'lucide-react';
import WikiScriptEditor from './WikiScriptEditor';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const SEVERITY_COLORS = {
    blocker: '#a50e0e',
    major: '#d93025',
    minor: '#f29900',
};

const STATUS_LABELS = {
    issues: 'Issues',
    failed: 'Failed Checks',
    skipped: 'Skipped',
    passed: 'Passed',
    all: 'All',
};

const ComplianceReviewWorkspace = ({
    report,
    jsonScript,
    isOpen,
    onClose,
    activeIssueId,
    onIssueSelect,
    variant = 'overlay',
}) => {
    const [filter, setFilter] = useState('issues');
    const [isQueueOpen, setIsQueueOpen] = useState(true);
    const queueRailRef = useRef(null);

    const checks = useMemo(() => report?.checks || [], [report?.checks]);
    const issues = useMemo(() => report?.issues || [], [report?.issues]);
    const summary = report?.summary || {};
    const artifactSummary = report?.artifact_summary || {};
    const policy = report?.policy || {};

    const checkById = useMemo(
        () => Object.fromEntries(checks.map((check) => [check.id, check])),
        [checks]
    );

    const activeIssue = useMemo(
        () => issues.find((issue) => issue.id === activeIssueId) || null,
        [issues, activeIssueId]
    );

    const visibleChecks = useMemo(() => {
        if (filter === 'failed') return checks.filter((check) => check.ai_review === false);
        if (filter === 'skipped') return checks.filter((check) => check.ai_review === null);
        if (filter === 'passed') return checks.filter((check) => check.ai_review === true);
        return checks;
    }, [checks, filter]);

    const issueCounts = useMemo(() => ({
        issues: issues.length,
        failed: checks.filter((check) => check.ai_review === false).length,
        skipped: checks.filter((check) => check.ai_review === null).length,
        passed: checks.filter((check) => check.ai_review === true).length,
        all: checks.length,
    }), [checks, issues]);

    if (!isOpen || !report) return null;
    const isPage = variant === 'page';

    const scrollQueue = (direction) => {
        const rail = queueRailRef.current;
        if (!rail) return;
        const distance = Math.min(rail.clientWidth * 0.85, 520);
        rail.scrollBy({ left: direction * distance, behavior: 'smooth' });
    };

    const handleDownloadDocx = async () => {
        try {
            const response = await fetch(`${API_URL}/export_compliance_report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    checks,
                    summary,
                    format: 'docx',
                }),
            });

            if (!response.ok) throw new Error('Failed to generate DOCX');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'admin_compliance_report.docx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('DOCX download error:', error);
            alert('Failed to download. Is the backend running?');
        }
    };

    const workspace = (
        <section className="compliance-review-workspace" style={getWorkspaceStyle(variant)}>
            {variant !== 'page' && (
                <header style={headerStyle}>
                    <div>
                        <div style={eyebrowStyle}>Admin Compliance V1</div>
                        <h3 style={titleStyle}>Compliance Review Workspace</h3>
                        <div style={metaStyle}>
                            <span>{policy.criteria_count || checks.length} criteria</span>
                            <span>{artifactSummary.rows || jsonScript?.slides?.length || 0} script rows</span>
                            {(artifactSummary.detected_sections || []).length > 0 && (
                                <span>{artifactSummary.detected_sections.length} detected sections</span>
                            )}
                        </div>
                    </div>

                    <div style={headerActionsStyle}>
                        <button onClick={handleDownloadDocx} style={secondaryButtonStyle}>
                            <Download size={15} />
                            DOCX
                        </button>
                        {onClose && (
                            <button onClick={onClose} style={iconButtonStyle} aria-label="Close compliance workspace">
                                <X size={18} />
                            </button>
                        )}
                    </div>
                </header>
            )}

            <div style={summaryGridStyle}>
                <SummaryTile label="Passed" value={summary.ai_passed || 0} icon={<CheckCircle2 size={18} />} tone="pass" />
                <SummaryTile label="Failed" value={summary.ai_failed || 0} icon={<AlertTriangle size={18} />} tone="fail" />
                <SummaryTile label="Skipped" value={summary.ai_skipped || 0} icon={<CircleDashed size={18} />} tone="skip" />
                <SummaryTile label="Major" value={summary.major || 0} icon={<ListChecks size={18} />} tone="major" />
            </div>

            <div className="compliance-review-main" style={isPage ? pageMainGridStyle : mainGridStyle}>
                <section style={queuePanelStyle}>
                    <div style={queueHeaderStyle}>
                        <div>
                            <div style={sectionLabelStyle}>Review Queue</div>
                            <div style={smallMutedStyle}>Click an item to jump to the highlighted evidence.</div>
                        </div>
                        <button
                            onClick={() => setIsQueueOpen((open) => !open)}
                            style={toggleButtonStyle}
                        >
                            {isQueueOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            {isQueueOpen ? 'Collapse' : 'Expand'}
                        </button>
                    </div>

                    {isQueueOpen && (
                        <>
                            <div style={filterBarStyle}>
                                {['issues', 'failed', 'skipped', 'passed', 'all'].map((item) => (
                                    <button
                                        key={item}
                                        onClick={() => setFilter(item)}
                                        style={filter === item ? activeFilterStyle : filterButtonStyle}
                                    >
                                        {STATUS_LABELS[item]} {issueCounts[item]}
                                    </button>
                                ))}
                            </div>

                            <div style={queueRailShellStyle}>
                                <button
                                    aria-label="Scroll review queue left"
                                    onClick={() => scrollQueue(-1)}
                                    style={queueArrowButtonStyle}
                                    type="button"
                                >
                                    <ChevronLeft size={18} />
                                </button>
                                <div ref={queueRailRef} style={isPage ? pageQueueStyle : queueStyle}>
                                    {filter === 'issues' ? (
                                        <IssueList
                                            issues={issues}
                                            activeIssueId={activeIssueId}
                                            checkById={checkById}
                                            onIssueSelect={onIssueSelect}
                                        />
                                    ) : (
                                        <CheckList
                                            checks={visibleChecks}
                                            issues={issues}
                                            activeIssueId={activeIssueId}
                                            onIssueSelect={onIssueSelect}
                                        />
                                    )}
                                </div>
                                <button
                                    aria-label="Scroll review queue right"
                                    onClick={() => scrollQueue(1)}
                                    style={queueArrowButtonStyle}
                                    type="button"
                                >
                                    <ChevronRight size={18} />
                                </button>
                            </div>
                        </>
                    )}
                </section>

                <div style={isPage ? pageRightPaneStyle : rightPaneStyle}>
                    {jsonScript ? (
                        <WikiScriptEditor
                            jsonScript={jsonScript}
                            isOpen={true}
                            readOnly={true}
                            fillHeight={!isPage}
                            flushTop={true}
                            showCloseButton={false}
                            showTips={false}
                            annotations={report.annotations || {}}
                            issues={issues}
                            activeIssueId={activeIssueId}
                            activeIssue={activeIssue}
                            activeIssueCheck={activeIssue ? checkById[activeIssue.criteria_id] : null}
                            onIssueSelect={onIssueSelect}
                        />
                    ) : (
                        <div style={emptyStateStyle}>No parsed script is available for row-level viewing.</div>
                    )}
                </div>
            </div>
        </section>
    );

    if (variant === 'page') return workspace;

    if (typeof document === 'undefined') return null;

    return createPortal(
        <div className="compliance-review-backdrop" style={backdropStyle}>
            {workspace}
        </div>,
        document.body
    );
};

const SummaryTile = ({ label, value, icon, tone }) => {
    const colors = {
        pass: '#188038',
        fail: '#d93025',
        skip: 'var(--text-secondary)',
        major: '#d93025',
    };

    return (
        <div style={summaryTileStyle}>
            <span style={{ ...summaryIconStyle, color: colors[tone] }}>{icon}</span>
            <div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{value}</div>
                <div style={smallMutedStyle}>{label}</div>
            </div>
        </div>
    );
};

const IssueList = ({ issues, activeIssueId, checkById, onIssueSelect }) => {
    if (!issues.length) {
        return <div style={emptyStateStyle}>No row-level issues were returned for this report.</div>;
    }

    return issues.map((issue) => {
        const firstEvidence = issue.evidence?.[0];
        const isActive = issue.id === activeIssueId;
        const check = checkById[issue.criteria_id];

        return (
            <button
                key={issue.id}
                onClick={() => onIssueSelect && onIssueSelect(issue.id)}
                style={isActive ? activeCardStyle : queueCardStyle}
            >
                <div style={cardTopLineStyle}>
                    <SeverityPill severity={issue.severity} />
                    {firstEvidence?.row_number && (
                        <span style={rowBadgeStyle}>
                            Row {firstEvidence.row_number}
                            {firstEvidence.field ? `, ${formatField(firstEvidence.field)}` : ''}
                        </span>
                    )}
                </div>
                <MarkdownText value={issue.message} style={cardTitleStyle} />
                {check?.criteria && <MarkdownText value={check.criteria} style={criterionStyle} />}
                {firstEvidence?.text && <MarkdownText value={firstEvidence.text} style={evidenceTextStyle} />}
            </button>
        );
    });
};

const CheckList = ({ checks, issues, activeIssueId, onIssueSelect }) => {
    const issueById = Object.fromEntries(issues.map((issue) => [issue.id, issue]));

    if (!checks.length) {
        return <div style={emptyStateStyle}>No checks match this filter.</div>;
    }

    return checks.map((check) => {
        const linkedIssue = check.issues?.map((id) => issueById[id]).find(Boolean);
        const isActive = check.issues?.includes(activeIssueId);

        return (
            <button
                key={check.id}
                onClick={() => linkedIssue && onIssueSelect && onIssueSelect(linkedIssue.id)}
                style={isActive ? activeCardStyle : queueCardStyle}
            >
                <div style={cardTopLineStyle}>
                    <StatusPill value={check.ai_review} />
                    <SeverityPill severity={check.severity} />
                </div>
                <MarkdownText value={check.criteria} style={cardTitleStyle} />
                {check.ai_notes && <MarkdownText value={check.ai_notes} style={criterionStyle} />}
                {linkedIssue?.evidence?.[0]?.row_number && (
                    <div style={rowBadgeStyle}>Row {linkedIssue.evidence[0].row_number}</div>
                )}
            </button>
        );
    });
};

const MarkdownText = ({ value, style }) => (
    <div style={style}>
        <ReactMarkdown
            components={markdownComponents}
        >
            {normalizeMarkdown(value)}
        </ReactMarkdown>
    </div>
);

const normalizeMarkdown = (value) => String(value || '').replace(/\\n/g, '\n');

const markdownComponents = {
    p: ({ children }) => <p style={markdownParagraphStyle}>{children}</p>,
    strong: ({ children }) => <strong style={markdownStrongStyle}>{children}</strong>,
    em: ({ children }) => <em>{children}</em>,
    ul: ({ children }) => <ul style={markdownListStyle}>{children}</ul>,
    ol: ({ children }) => <ol style={markdownListStyle}>{children}</ol>,
    li: ({ children }) => <li style={markdownListItemStyle}>{children}</li>,
    code: ({ children }) => <code style={markdownCodeStyle}>{children}</code>,
};

const SeverityPill = ({ severity }) => (
    <span style={{
        ...pillStyle,
        color: SEVERITY_COLORS[severity] || 'var(--text-secondary)',
        borderColor: `${SEVERITY_COLORS[severity] || '#999'}55`,
        background: `${SEVERITY_COLORS[severity] || '#999'}12`,
    }}>
        {severity || 'info'}
    </span>
);

const StatusPill = ({ value }) => {
    const label = value === true ? 'passed' : value === false ? 'failed' : 'skipped';
    const color = value === true ? '#188038' : value === false ? '#d93025' : 'var(--text-secondary)';
    return (
        <span style={{ ...pillStyle, color, borderColor: `${color}55`, background: `${color}12` }}>
            {label}
        </span>
    );
};

const formatField = (field) => field.replace('_', ' ');

const getWorkspaceStyle = (variant) => ({
    width: 'min(1600px, calc(100vw - 48px))',
    height: 'min(920px, calc(100vh - 48px))',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '12px',
    boxShadow: 'var(--shadow-lg)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    ...(variant === 'page' ? pageWorkspaceOverrides : {}),
});

const pageWorkspaceOverrides = {
    width: '100%',
    height: 'auto',
    minHeight: '100%',
    borderRadius: '0',
    border: 'none',
    boxShadow: 'none',
    overflow: 'visible',
};

const backdropStyle = {
    position: 'fixed',
    inset: 0,
    zIndex: 1000,
    padding: '1.5rem',
    background: 'rgba(15, 23, 42, 0.28)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
};

const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '1rem',
    padding: '1rem 1.25rem',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-color)',
    flexShrink: 0,
};

const eyebrowStyle = {
    color: 'var(--accent-primary)',
    fontSize: '0.78rem',
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
};

const titleStyle = {
    margin: '0.2rem 0',
    fontSize: '1.15rem',
    color: 'var(--text-primary)',
};

const metaStyle = {
    display: 'flex',
    gap: '0.75rem',
    flexWrap: 'wrap',
    color: 'var(--text-secondary)',
    fontSize: '0.86rem',
};

const headerActionsStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
};

const secondaryButtonStyle = {
    padding: '0.45rem 0.75rem',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    fontWeight: 600,
};

const iconButtonStyle = {
    padding: '0.45rem',
    background: 'transparent',
    border: '1px solid transparent',
    borderRadius: '8px',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
};

const summaryGridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
    gap: '0.75rem',
    padding: '1rem 1.25rem',
    borderBottom: '1px solid var(--border-color)',
    flexShrink: 0,
};

const summaryTileStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.8rem',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
};

const summaryIconStyle = {
    display: 'flex',
};

const mainGridStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    padding: '1rem',
    flex: 1,
    minHeight: 0,
    overflow: 'hidden',
};

const pageMainGridStyle = {
    ...mainGridStyle,
    flex: '0 0 auto',
    minHeight: 'auto',
    overflow: 'visible',
};

const queuePanelStyle = {
    border: '1px solid var(--border-color)',
    borderRadius: '10px',
    overflow: 'hidden',
    background: 'var(--bg-primary)',
    flexShrink: 0,
};

const rightPaneStyle = {
    minWidth: 0,
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    alignSelf: 'stretch',
};

const pageRightPaneStyle = {
    ...rightPaneStyle,
    minHeight: 'auto',
    overflow: 'visible',
};

const queueHeaderStyle = {
    padding: '0.9rem 1rem',
    borderBottom: '1px solid var(--border-color)',
    background: 'var(--bg-secondary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '1rem',
};

const sectionLabelStyle = {
    fontWeight: 800,
    color: 'var(--text-primary)',
};

const smallMutedStyle = {
    color: 'var(--text-secondary)',
    fontSize: '0.84rem',
};

const filterBarStyle = {
    display: 'flex',
    gap: '0.4rem',
    padding: '0.75rem',
    borderBottom: '1px solid var(--border-color)',
    flexWrap: 'wrap',
};

const toggleButtonStyle = {
    alignItems: 'center',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '999px',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    display: 'inline-flex',
    flexShrink: 0,
    fontSize: '0.8rem',
    fontWeight: 800,
    gap: '0.35rem',
    padding: '0.4rem 0.75rem',
};

const queueRailShellStyle = {
    alignItems: 'stretch',
    display: 'grid',
    gap: '0.5rem',
    gridTemplateColumns: 'auto minmax(0, 1fr) auto',
    padding: '0.75rem',
};

const queueArrowButtonStyle = {
    alignItems: 'center',
    alignSelf: 'center',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '999px',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    display: 'inline-flex',
    height: '38px',
    justifyContent: 'center',
    width: '38px',
};

const filterButtonStyle = {
    border: '1px solid var(--border-color)',
    background: 'var(--bg-primary)',
    color: 'var(--text-secondary)',
    borderRadius: '999px',
    padding: '0.35rem 0.65rem',
    cursor: 'pointer',
    fontSize: '0.78rem',
    fontWeight: 700,
};

const activeFilterStyle = {
    ...filterButtonStyle,
    background: 'var(--accent-primary)',
    color: 'white',
    borderColor: 'var(--accent-primary)',
};

const queueStyle = {
    display: 'flex',
    gap: '0.6rem',
    overflowX: 'auto',
    overflowY: 'hidden',
    padding: '0.1rem 0.1rem 0.65rem',
    scrollBehavior: 'smooth',
    scrollSnapType: 'x proximity',
    WebkitOverflowScrolling: 'touch',
};

const pageQueueStyle = {
    ...queueStyle,
};

const queueCardStyle = {
    textAlign: 'left',
    border: '1px solid var(--border-color)',
    background: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    borderRadius: '8px',
    padding: '0.75rem',
    cursor: 'pointer',
    flex: '0 0 min(360px, calc(100vw - 7rem))',
    minHeight: '175px',
    scrollSnapAlign: 'start',
};

const activeCardStyle = {
    ...queueCardStyle,
    border: '2px solid #d93025',
    background: 'rgba(217, 48, 37, 0.07)',
};

const cardTopLineStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
    flexWrap: 'wrap',
};

const cardTitleStyle = {
    marginTop: '0.45rem',
    fontWeight: 750,
    lineHeight: 1.35,
};

const markdownParagraphStyle = {
    margin: 0,
};

const markdownStrongStyle = {
    fontWeight: 800,
};

const markdownListStyle = {
    margin: 0,
    paddingLeft: '1.1rem',
};

const markdownListItemStyle = {
    margin: 0,
};

const markdownCodeStyle = {
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '0.92em',
    padding: '0.05rem 0.25rem',
};

const criterionStyle = {
    marginTop: '0.35rem',
    color: 'var(--text-secondary)',
    fontSize: '0.84rem',
    lineHeight: 1.45,
    display: '-webkit-box',
    WebkitBoxOrient: 'vertical',
    WebkitLineClamp: 2,
    overflow: 'hidden',
};

const evidenceTextStyle = {
    marginTop: '0.45rem',
    color: 'var(--text-secondary)',
    fontSize: '0.82rem',
    display: '-webkit-box',
    WebkitBoxOrient: 'vertical',
    WebkitLineClamp: 2,
    overflow: 'hidden',
    borderLeft: '3px solid rgba(217, 48, 37, 0.3)',
    paddingLeft: '0.5rem',
};

const rowBadgeStyle = {
    color: 'var(--text-secondary)',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '999px',
    padding: '0.13rem 0.45rem',
    fontSize: '0.75rem',
    fontWeight: 700,
};

const pillStyle = {
    border: '1px solid',
    borderRadius: '999px',
    padding: '0.12rem 0.45rem',
    fontSize: '0.72rem',
    fontWeight: 800,
    textTransform: 'uppercase',
};

const emptyStateStyle = {
    padding: '1rem',
    color: 'var(--text-secondary)',
    background: 'var(--bg-secondary)',
    border: '1px dashed var(--border-color)',
    borderRadius: '8px',
    fontSize: '0.9rem',
};

export default ComplianceReviewWorkspace;
