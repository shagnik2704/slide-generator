import React, { useRef, useState } from 'react';
import { Settings, ChevronRight, ChevronLeft, ChevronDown, ClipboardCheck, ShieldCheck, Mic, FileText, Image, Presentation, ListChecks, Languages } from 'lucide-react';
import Tooltip from './Tooltip';
import UserProfile from './UserProfile';

const Sidebar = ({ isOpen, toggleSidebar, onStageFile, onCreateSlides, onOpenBatchModal, onOpenBatchQualityModal }) => {
    const collapsedWidth = '60px';
    const expandedWidth = '280px';

    // Dropdown state
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    // Refs for hidden file inputs
    const complianceInputRef = useRef(null);
    const qualityInputRef = useRef(null);
    const voiceInputRef = useRef(null);
    const scriptInputRef = useRef(null);
    const imageInputRef = useRef(null);
    const slidesInputRef = useRef(null);
    const translationInputRef = useRef(null);

    // Handle compliance file selection - stage for preview
    const handleComplianceFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'compliance' });
            e.target.value = '';
        }
    };

    // Handle quality file selection - stage for preview
    const handleQualityFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'quality' });
            e.target.value = '';
        }
    };

    // Handle voice file selection - stage for preview
    const handleVoiceFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'voice' });
            e.target.value = '';
        }
    };

    // Handle script file selection (outline upload) - stage for preview
    const handleScriptFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'outline' });
            e.target.value = '';
        }
    };

    // Handle image generation file selection - stage for preview
    const handleImageFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'images' });
            e.target.value = '';
        }
    };

    // Handle translation file selection - stage for preview
    const handleTranslationFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'translation' });
            e.target.value = '';
        }
    };

    // Handle slides generation file selection - stage for preview
    const handleSlidesFileSelect = (e) => {
        const file = e.target.files[0];
        if (file && onStageFile) {
            onStageFile({ file, type: 'slides' });
            e.target.value = '';
        }
    };

    // Styles for icon buttons in collapsed mode
    const iconButtonStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',  // Always flex-start - icons stay in place
        gap: isOpen ? '0.75rem' : '0',  // Collapse gap when closed
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
            // Smoother animation with cubic-bezier and GPU acceleration
            transition: 'width 0.35s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.35s cubic-bezier(0.4, 0, 0.2, 1), padding 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
            willChange: 'width, min-width, padding',
            overflow: 'visible',
            position: 'relative'
        }}>

            {/* Hidden file inputs */}
            <input
                ref={complianceInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleComplianceFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={qualityInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleQualityFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={voiceInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleVoiceFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={scriptInputRef}
                type="file"
                accept=".md,.docx,.odt,.txt"
                onChange={handleScriptFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={imageInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleImageFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={slidesInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleSlidesFileSelect}
                style={{ display: 'none' }}
            />
            <input
                ref={translationInputRef}
                type="file"
                accept=".json,.docx,.odt"
                onChange={handleTranslationFileSelect}
                style={{ display: 'none' }}
            />

            {/* Navigation Items */}
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>

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
                        {/* Admin Compliance */}
                        <TooltipWrapper text="Admin Compliance">
                            <button
                                onClick={() => complianceInputRef.current?.click()}
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
                                <ShieldCheck size={18} />
                                <span style={textLabelStyle}>Admin Compliance</span>
                            </button>
                        </TooltipWrapper>

                        {/* Quality Compliance */}
                        <TooltipWrapper text="Quality Compliance">
                            <button
                                onClick={() => qualityInputRef.current?.click()}
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
                                <span style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '-0.5px' }}>अத</span>
                                <span style={textLabelStyle}>Quality Compliance</span>
                            </button>
                        </TooltipWrapper>

                        {/* Batch Admin */}
                        <TooltipWrapper text="Batch Admin">
                            <button
                                onClick={() => onOpenBatchModal && onOpenBatchModal()}
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
                                <ListChecks size={18} />
                                <span style={textLabelStyle}>Batch Admin</span>
                            </button>
                        </TooltipWrapper>

                        {/* Batch Quality */}
                        <TooltipWrapper text="Batch Quality">
                            <button
                                onClick={() => onOpenBatchQualityModal && onOpenBatchQualityModal()}
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
                                <Languages size={18} />
                                <span style={textLabelStyle}>Batch Quality</span>
                            </button>
                        </TooltipWrapper>
                    </div>
                )}
            </nav>

            {/* Script Generator Button */}
            <TooltipWrapper text="Script Generator">
                <button
                    onClick={() => scriptInputRef.current?.click()}
                    style={{
                        ...iconButtonStyle,
                        marginTop: '0.75rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                >
                    <FileText size={20} />
                    <span style={textLabelStyle}>Script Generator</span>
                </button>
            </TooltipWrapper>

            {/* Voice Generator Button */}
            <TooltipWrapper text="Voice Generator">
                <button
                    onClick={() => voiceInputRef.current?.click()}
                    style={{
                        ...iconButtonStyle,
                        marginTop: '0.5rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                >
                    <Mic size={20} />
                    <span style={textLabelStyle}>Voice Generator</span>
                </button>
            </TooltipWrapper>

            {/* Image Generator Button */}
            <TooltipWrapper text="Image Generator">
                <button
                    onClick={() => imageInputRef.current?.click()}
                    style={{
                        ...iconButtonStyle,
                        marginTop: '0.5rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                >
                    <Image size={20} />
                    <span style={textLabelStyle}>Image Generator</span>
                </button>
            </TooltipWrapper>

            {/* Slides Generator Button */}
            <TooltipWrapper text="Slides Generator">
                <button
                    onClick={() => slidesInputRef.current?.click()}
                    style={{
                        ...iconButtonStyle,
                        marginTop: '0.5rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                >
                    <Presentation size={20} />
                    <span style={textLabelStyle}>Slides Generator</span>
                </button>
            </TooltipWrapper>

            {/* Translation Button */}
            <TooltipWrapper text="Translate Script">
                <button
                    onClick={() => translationInputRef.current?.click()}
                    style={{
                        ...iconButtonStyle,
                        marginTop: '0.5rem'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                        e.currentTarget.style.color = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                >
                    <Languages size={20} />
                    <span style={textLabelStyle}>Translate Script</span>
                </button>
            </TooltipWrapper>

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
                {/* User Profile */}
                {isOpen && (
                    <div style={{ marginBottom: '0.5rem' }}>
                        <UserProfile />
                    </div>
                )}

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

export default Sidebar;

