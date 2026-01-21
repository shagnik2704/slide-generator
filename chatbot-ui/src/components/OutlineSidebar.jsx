import React, { useRef, useState } from 'react';
import { Settings, ChevronRight, ChevronLeft, ChevronDown, ClipboardCheck, FileText, Loader2, Download } from 'lucide-react';
import Tooltip from './Tooltip';
import UserProfile from './UserProfile';
import { API_URL } from '../services/api';

const OutlineSidebar = ({ isOpen, toggleSidebar, onStageFile }) => {
    const collapsedWidth = '60px';
    const expandedWidth = '280px';

    // Dropdown state
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [snapshotError, setSnapshotError] = useState('');
    const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

    // Refs for hidden file inputs
    const outlineComplianceInputRef = useRef(null);

    // Handle outline compliance file selection - stage for preview
    const handleOutlineComplianceFileSelect = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file type
        const filename = file.name.toLowerCase();
        if (!filename.endsWith('.json') && !filename.endsWith('.docx')) {
            alert('Please upload a .json or .docx file');
            e.target.value = '';
            return;
        }
        
        // Stage the file for preview
        if (onStageFile) {
            console.log('Staging file:', file.name, 'Type:', 'outline_compliance');
            onStageFile({ file, type: 'outline_compliance' });
        } else {
            console.error('onStageFile is not defined');
        }
        
        e.target.value = '';
    };

    // Styles for icon buttons in collapsed mode
    const iconButtonStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',
        gap: isOpen ? '0.75rem' : '0',
        padding: isOpen ? '0.75rem 1rem' : '0.75rem',
        background: 'transparent',
        border: 'none',
        borderRadius: '0.5rem',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem',
        cursor: 'pointer',
        width: '100%',
        transition: 'gap 0.35s cubic-bezier(0.4, 0, 0.2, 1), padding 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s ease, color 0.2s ease',
        whiteSpace: 'nowrap',
        overflow: 'hidden'
    };

    // Text label style - fades out AND collapses when sidebar closed
    const textLabelStyle = {
        opacity: isOpen ? 1 : 0,
        width: isOpen ? 'auto' : 0,
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        transition: 'opacity 0.25s ease, width 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
        pointerEvents: isOpen ? 'auto' : 'none'
    };

    // Dropdown item style (indented)
    const dropdownItemStyle = {
        ...iconButtonStyle,
        paddingLeft: isOpen ? '2.5rem' : '0.75rem',
        fontSize: '0.8rem'
    };

    // Wrapper component for conditional tooltip
    const TooltipWrapper = ({ children, text }) => {
        // Only show tooltip when sidebar is collapsed
        if (isOpen) return children;
        return <Tooltip text={text} position="right">{children}</Tooltip>;
    };

    const handleDownloadPdf = async () => {
        setSnapshotError('');
        setIsDownloadingPdf(true);
        try {
            const raw = localStorage.getItem('outline_chat_session');
            const session = raw ? JSON.parse(raw) : null;
            const projectId = session?.projectId;
            if (!projectId) {
                setSnapshotError('Start an outline chat first to create a session.');
                return;
            }
            const response = await fetch(`${API_URL}/outline_chat/${projectId}/export?format=pdf`);
            const data = await response.json();
            if (data?.pdf_url) {
                window.open(`${API_URL}${data.pdf_url}`, '_blank');
            } else {
                setSnapshotError('PDF is not ready yet. Complete the outline review first.');
            }
        } catch (e) {
            setSnapshotError(e?.message || 'Failed to download PDF.');
        } finally {
            setIsDownloadingPdf(false);
        }
    };

    return (
        <aside style={{
            width: isOpen ? expandedWidth : collapsedWidth,
            minWidth: isOpen ? expandedWidth : collapsedWidth,
            backgroundColor: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            padding: isOpen ? '1rem' : '0.75rem 0.5rem',
            flexShrink: 0,
            transition: 'width 0.35s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.35s cubic-bezier(0.4, 0, 0.2, 1), padding 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
            willChange: 'width, min-width, padding',
            overflow: 'visible',
            position: 'relative'
        }}>

            {/* Hidden file inputs */}
            <input
                ref={outlineComplianceInputRef}
                type="file"
                accept=".json,.docx"
                onChange={handleOutlineComplianceFileSelect}
                style={{ display: 'none' }}
            />

            {/* Navigation Items */}
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>

                {/* Download PDF button */}
                <TooltipWrapper text="Download PDF">
                    <button
                        onClick={handleDownloadPdf}
                        style={iconButtonStyle}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--accent-primary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = 'var(--text-secondary)';
                        }}
                    >
                        {isDownloadingPdf ? (
                            <Loader2 size={20} className="animate-spin" />
                        ) : (
                            <Download size={20} />
                        )}
                        <span style={{ ...textLabelStyle, flex: 1, textAlign: 'left' }}>
                            {isDownloadingPdf ? 'Downloading…' : 'Download PDF'}
                        </span>
                    </button>
                </TooltipWrapper>

                {/* Compliance Report Parent Button */}
                <TooltipWrapper text="Compliance Report">
                    <button
                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        style={{
                            ...iconButtonStyle,
                            background: isDropdownOpen ? 'var(--bg-tertiary)' : 'transparent',
                            color: isDropdownOpen ? 'var(--accent-primary)' : 'var(--text-secondary)'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--accent-primary)';
                        }}
                        onMouseLeave={(e) => {
                            if (!isDropdownOpen) {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = 'var(--text-secondary)';
                            }
                        }}
                    >
                        <ClipboardCheck size={20} />
                        <span style={{ flex: 1, textAlign: 'left', ...textLabelStyle }}>Compliance Report</span>
                        <ChevronDown
                            size={16}
                            style={{
                                ...textLabelStyle,
                                transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                                transition: 'transform 0.2s ease, opacity 0.25s ease'
                            }}
                        />
                    </button>
                </TooltipWrapper>

                {/* Dropdown Items */}
                {isDropdownOpen && (
                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.125rem',
                        marginTop: '0.125rem'
                    }}>
                        {/* Outline Compliance */}
                        <TooltipWrapper text="Outline Compliance">
                            <button
                                onClick={() => outlineComplianceInputRef.current?.click()}
                                style={dropdownItemStyle}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    e.currentTarget.style.color = 'var(--accent-primary)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'transparent';
                                    e.currentTarget.style.color = 'var(--text-secondary)';
                                }}
                            >
                                <FileText size={18} />
                                <span style={textLabelStyle}>Upload & Check</span>
                            </button>
                        </TooltipWrapper>
                    </div>
                )}
            </nav>

            {/* Errors */}
            {isOpen && snapshotError && (
                <div style={{
                    marginTop: '0.75rem',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '0.75rem',
                    padding: '0.75rem',
                    color: '#ef4444',
                    fontSize: '0.8rem'
                }}>
                    {snapshotError}
                </div>
            )}

            {/* Spacer */}
            <div style={{ flex: 1 }} />

            {/* Footer */}
            <div style={{
                borderTop: '1px solid var(--border-color)',
                paddingTop: '0.75rem',
                marginTop: '0.75rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                <TooltipWrapper text="Settings">
                    <button
                        style={iconButtonStyle}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--accent-primary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = 'var(--text-secondary)';
                        }}
                    >
                        <Settings size={20} />
                        <span style={textLabelStyle}>Settings</span>
                    </button>
                </TooltipWrapper>

                {/* Toggle button */}
                <TooltipWrapper text={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}>
                    <button
                        onClick={toggleSidebar}
                        style={{
                            ...iconButtonStyle,
                            justifyContent: 'center',
                            background: 'var(--bg-tertiary)',
                            marginTop: '0.5rem'
                        }}
                    >
                        {isOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
                        <span style={{ marginLeft: '0.25rem', ...textLabelStyle }}>Collapse</span>
                    </button>
                </TooltipWrapper>
            </div>
        </aside>
    );
};

export default OutlineSidebar;
