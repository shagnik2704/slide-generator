import React, { forwardRef, useImperativeHandle } from 'react';
import { Menu, UploadCloud, MessageSquare, Trash2 } from 'lucide-react';

// Components
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import ThemeToggle from './ThemeToggle';
import OutlineCard from './OutlineCard';
import VoicePreview from './VoicePreview';

// Message Action Components
import {
    ScriptUploadedActions,
    ScriptReviewActions,
    SlidesReviewActions,
    VideoResultActions,
    MediaWikiExportActions,
    OutlineUploadedActions,
} from './message-actions';

// Custom Hook
import { useChatArea } from '../hooks/useChatArea';

/**
 * ChatArea - Main chat interface component
 * 
 * This component handles the presentation layer for the chat interface.
 * All business logic and state management is handled by the useChatArea hook.
 */
const ChatArea = forwardRef(({ toggleSidebar }, ref) => {
    const {
        // State
        mode,
        setMode,
        uploadMessages,
        setUploadMessages,
        outlineSession,
        isTyping,
        activeMessages,

        // UI State
        copiedId,
        setCopiedId,
        openEditorId,
        setOpenEditorId,
        openReportId,
        setOpenReportId,
        openQualityId,
        setOpenQualityId,
        qualityReports,
        isQualityLoading,

        // Refs
        messagesEndRef,
        editedScriptInputRef,

        // Handlers
        handleClearSession,
        handleSendMessage,
        handleUploadScript,
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload,
        handleGenerateScript,
        handleGenerateSlides,
        handleApprove,
        handleConfirmation,
        handleSendChatText,
        handleDownloadScriptDocx,
        handleUploadEditedScript,
        handleExportMediaWiki,
        handleSaveScriptEdit,
        handleQualityCheck,
    } = useChatArea();

    // Expose handlers for sidebar via ref
    useImperativeHandle(ref, () => ({
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload
    }));

    // Helper to update compliance report in a message
    const handleUpdateComplianceReport = (messageId, updatedReport) => {
        setUploadMessages(prev => prev.map(m =>
            m.id === messageId ? { ...m, complianceReport: updatedReport } : m
        ));
    };

    return (
        <main style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            position: 'relative'
        }}>
            {/* Header */}
            <header style={{
                padding: '1rem 1.5rem',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                boxShadow: 'var(--shadow-md)',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                zIndex: 10
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button
                        onClick={toggleSidebar}
                        style={{
                            background: 'var(--bg-tertiary)',
                            border: 'none',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '0.5rem',
                            borderRadius: '50%',
                            width: '40px',
                            height: '40px',
                            transition: 'all 0.3s ease',
                            boxShadow: 'var(--shadow-sm)',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--accent-primary)';
                            e.currentTarget.style.color = 'white';
                            e.currentTarget.style.transform = 'scale(1.15)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--text-primary)';
                            e.currentTarget.style.transform = 'scale(1)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                        }}
                    >
                        <Menu size={24} strokeWidth={2.5} />
                    </button>
                    <img
                        src="/favicon.png"
                        alt="EduPyramids"
                        style={{ height: '36px', marginRight: '0.5rem' }}
                    />
                    <div style={{
                        fontWeight: 600,
                        fontSize: '1.25rem',
                        fontFamily: '"Outfit", sans-serif',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem'
                    }}>
                        <span style={{ color: 'var(--accent-secondary)' }}>Spoken</span>
                        <span style={{ color: 'var(--accent-primary)' }}>Tutorial Generator</span>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {/* Mode Toggle */}
                    <div style={{
                        display: 'flex',
                        background: 'var(--bg-secondary)',
                        borderRadius: '1rem',
                        padding: '0.25rem',
                        boxShadow: 'var(--shadow-sm)',
                        border: '1px solid var(--border-color)',
                        gap: '0.25rem'
                    }}>
                        <button
                            onClick={() => setMode('upload')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.75rem',
                                borderRadius: '0.75rem',
                                border: 'none',
                                background: mode === 'upload'
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: mode === 'upload' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: mode === 'upload' ? 'var(--shadow-sm)' : 'none'
                            }}
                        >
                            <UploadCloud size={18} />
                            Upload Mode
                        </button>
                        <button
                            onClick={() => setMode('outline_chat')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.75rem',
                                borderRadius: '0.75rem',
                                border: 'none',
                                background: mode === 'outline_chat'
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: mode === 'outline_chat' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: mode === 'outline_chat' ? 'var(--shadow-sm)' : 'none'
                            }}
                        >
                            <MessageSquare size={18} />
                            Outline Chat
                        </button>
                    </div>

                    {/* Clear Session button */}
                    {mode === 'upload' && uploadMessages.length > 1 && (
                        <button
                            onClick={handleClearSession}
                            style={{
                                padding: '0.25rem 0.75rem',
                                background: 'transparent',
                                border: '1px solid var(--border-color)',
                                borderRadius: '1rem',
                                fontSize: '0.8rem',
                                color: 'var(--text-secondary)',
                                fontWeight: 500,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                transition: 'all 0.2s ease',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#ef4444';
                                e.currentTarget.style.color = '#ef4444';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = 'var(--border-color)';
                                e.currentTarget.style.color = 'var(--text-secondary)';
                            }}
                        >
                            <Trash2 size={14} />
                            Clear Session
                        </button>
                    )}

                    <ThemeToggle />
                </div>
            </header>

            {/* Messages Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '6rem 1rem 1rem 1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                <div style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
                    {activeMessages.map((msg) => (
                        <div key={msg.id}>
                            <MessageBubble
                                message={msg}
                                onConfirmation={mode === 'outline_chat' ? handleConfirmation : null}
                            />

                            {/* OutlineCard for outline_chat mode */}
                            {mode === 'outline_chat' && msg.outlineData && msg.phase === 'review' && (
                                <OutlineCard
                                    outlineData={msg.outlineData}
                                    projectId={outlineSession.projectId || msg.outlineData?.project_id}
                                />
                            )}

                            {/* Message Action Components */}
                            {mode === 'upload' && msg.type === 'outline_uploaded' && (
                                <OutlineUploadedActions
                                    msg={msg}
                                    isTyping={isTyping}
                                    onGenerateScript={handleGenerateScript}
                                />
                            )}

                            {mode === 'upload' && msg.type === 'script_uploaded' && (
                                <ScriptUploadedActions
                                    msg={msg}
                                    isTyping={isTyping}
                                    openReportId={openReportId}
                                    setOpenReportId={setOpenReportId}
                                    openQualityId={openQualityId}
                                    setOpenQualityId={setOpenQualityId}
                                    qualityReports={qualityReports}
                                    isQualityLoading={isQualityLoading}
                                    onGenerateSlides={handleGenerateSlides}
                                    onQualityCheck={handleQualityCheck}
                                    onUpdateComplianceReport={handleUpdateComplianceReport}
                                />
                            )}

                            {mode === 'upload' && msg.type === 'script_review' && (
                                <ScriptReviewActions
                                    msg={msg}
                                    isTyping={isTyping}
                                    openEditorId={openEditorId}
                                    setOpenEditorId={setOpenEditorId}
                                    editedScriptInputRef={editedScriptInputRef}
                                    onGenerateSlides={handleGenerateSlides}
                                    onDownloadScriptDocx={handleDownloadScriptDocx}
                                    onUploadEditedScript={handleUploadEditedScript}
                                    onExportMediaWiki={handleExportMediaWiki}
                                    onSaveScriptEdit={handleSaveScriptEdit}
                                />
                            )}

                            {mode === 'upload' && msg.type === 'slides_review' && (
                                <SlidesReviewActions
                                    msg={msg}
                                    isTyping={isTyping}
                                    onApprove={handleApprove}
                                />
                            )}

                            {mode === 'upload' && msg.type === 'video_result' && (
                                <VideoResultActions msg={msg} />
                            )}

                            {msg.type === 'mediawiki_export' && (
                                <MediaWikiExportActions
                                    msg={msg}
                                    copiedId={copiedId}
                                    setCopiedId={setCopiedId}
                                />
                            )}

                            {msg.type === 'voice_preview' && msg.voiceData && (
                                <VoicePreview voiceData={msg.voiceData} isOpen={true} />
                            )}
                        </div>
                    ))}

                    {/* Typing Indicator */}
                    {isTyping && (
                        <div style={{ display: 'flex', gap: '0.5rem', padding: '0 1rem', marginBottom: '1.5rem' }}>
                            <div style={{
                                width: '36px', height: '36px', borderRadius: '50%',
                                background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <div className="typing-dot" style={{ width: '6px', height: '6px', background: 'var(--text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both' }}></div>
                                <div className="typing-dot" style={{ width: '6px', height: '6px', background: 'var(--text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both 0.16s' }}></div>
                                <div className="typing-dot" style={{ width: '6px', height: '6px', background: 'var(--text-secondary)', borderRadius: '50%', margin: '0 2px', animation: 'bounce 1.4s infinite ease-in-out both 0.32s' }}></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <InputArea
                mode={mode}
                onSendMessage={handleSendMessage}
                onUploadScript={handleUploadScript}
                onSendText={handleSendChatText}
                disabled={isTyping}
            />

            <style>{`
                @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
            `}</style>
        </main>
    );
});

export default ChatArea;
