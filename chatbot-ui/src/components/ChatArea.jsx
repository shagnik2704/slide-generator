import React, { forwardRef, useImperativeHandle } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, UploadCloud, MessageSquare, Trash2 } from 'lucide-react';

// Components
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import ThemeToggle from './ThemeToggle';
import OutlineCard from './OutlineCard';
import VoicePreview from './VoicePreview';
import ImagePromptReview from './ImagePromptReview';
import ImageGallery from './ImageGallery';
import SlidesPreview from './SlidesPreview';
import AskAIChat from './AskAIChat';
import BatchUploadModal from './BatchUploadModal';
import BatchResultsList from './BatchResultsList';
import UserProfile from './UserProfile';
import TranslationModal from './TranslationModal';
import TranslationResults from './TranslationResults';

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
const ChatArea = forwardRef(({ toggleSidebar, isSidebarOpen, mode = 'upload', showSidebarToggle = true }, ref) => {
    const location = useLocation();
    const {
        // State
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
        handleScriptToWiki,
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload,
        handleSidebarScriptUpload,
        handleSidebarBatchComplianceUpload,
        handleSidebarBatchQualityUpload,
        handleGenerateScript,
        handleGenerateSlides,
        handleCreateSlides,
        handleApprove,
        handleConfirmation,
        handleSendChatText,
        handleEditAnswer,
        handleDownloadScriptDocx,
        handleUploadEditedScript,
        handleExportMediaWiki,
        handleSaveScriptEdit,
        handleQualityCheck,

        // Staging
        stagedFile,
        setStagedFile,
        handleConfirmStagedFile,
        handleCancelStagedFile,
    } = useChatArea(mode);

    // Batch Modal State
    const [isBatchModalOpen, setIsBatchModalOpen] = React.useState(false);
    const [batchMode, setBatchMode] = React.useState('compliance'); // 'compliance' | 'quality'

    // Translation Modal State
    const [isTranslationModalOpen, setIsTranslationModalOpen] = React.useState(false);
    const [translationFile, setTranslationFile] = React.useState(null);

    // Auto-open translation modal when a translation file is staged
    React.useEffect(() => {
        if (stagedFile?.type === 'translation') {
            setTranslationFile(stagedFile.file);
            setIsTranslationModalOpen(true);
            setStagedFile(null);  // Clear staging since modal takes over
        }
    }, [stagedFile, setStagedFile]);

    // Handler to close modal and start upload based on mode
    const handleBatchUpload = (files) => {
        if (batchMode === 'quality') {
            handleSidebarBatchQualityUpload(files);
        } else {
            handleSidebarBatchComplianceUpload(files);
        }
        setIsBatchModalOpen(false);
    };

    // Translation handler
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const handleTranslation = async ({ file, languages, translateVisualCues }) => {
        // Show loading message
        const loadingMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `🌐 Translating script to ${languages.length} language(s)...`
        };
        setUploadMessages(prev => [...prev, loadingMessage]);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData
            });
            const parseData = await parseResponse.json();

            // Step 2: Batch translate
            const translateResponse = await fetch(`${API_URL}/translation/batch_translate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    languages: languages,
                    translate_visual_cues: translateVisualCues
                })
            });
            const translationResults = await translateResponse.json();

            // Add results message
            const resultMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `🌍 Translation Complete!\n\n` +
                    `File: ${file.name}\n` +
                    `Languages: ${translationResults.total_success}/${translationResults.total_requested} successful`,
                type: 'translation_result',
                translationResults: translationResults
            };
            setUploadMessages(prev => [...prev, resultMessage]);

        } catch (error) {
            console.error('Translation error:', error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Translation failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
            throw error;
        }
    };

    // Expose handlers for sidebar via ref
    useImperativeHandle(ref, () => ({
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload,
        handleSidebarScriptUpload,
        handleCreateSlides,
        setStagedFile,  // Expose staging for Sidebar
        openBatchModal: () => {
            setBatchMode('compliance');
            setIsBatchModalOpen(true);
        },
        openBatchQualityModal: () => {
            setBatchMode('quality');
            setIsBatchModalOpen(true);
        },
        openTranslationModal: (file) => {
            setTranslationFile(file);
            setIsTranslationModalOpen(true);
        }
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
                    {showSidebarToggle && (
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
                    )}
                    <Link
                        to="/"
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            textDecoration: 'none',
                            color: 'inherit',
                            cursor: 'pointer',
                        }}
                    >
                        <img
                            src="/favicon.png"
                            alt="EduPyramids"
                            style={{ height: '36px' }}
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
                    </Link>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {/* Mode Navigation */}
                    <div style={{
                        display: 'flex',
                        background: 'var(--bg-secondary)',
                        borderRadius: '1rem',
                        padding: '0.25rem',
                        boxShadow: 'var(--shadow-sm)',
                        border: '1px solid var(--border-color)',
                        gap: '0.25rem'
                    }}>
                        <Link
                            to="/upload"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.75rem',
                                borderRadius: '0.75rem',
                                border: 'none',
                                background: location.pathname === '/upload'
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: location.pathname === '/upload' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: location.pathname === '/upload' ? 'var(--shadow-sm)' : 'none',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <UploadCloud size={18} />
                            Upload Mode
                        </Link>
                        <Link
                            to="/outline-chat"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                padding: '0.4rem 0.75rem',
                                borderRadius: '0.75rem',
                                border: 'none',
                                background: location.pathname === '/outline-chat'
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: location.pathname === '/outline-chat' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                boxShadow: location.pathname === '/outline-chat' ? 'var(--shadow-sm)' : 'none',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <MessageSquare size={18} />
                            Outline Chat
                        </Link>
                    </div>

                    {/* Clear Session button */}
                    {mode === 'upload' && uploadMessages.length > 0 && (
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
                    
                    {/* User Profile - Compact version in header */}
                    {showSidebarToggle && !isSidebarOpen && (
                        <div style={{ marginLeft: '0.5rem' }}>
                            <UserProfile compact={true} />
                        </div>
                    )}
                </div>
            </header>

            {/* Messages Area - hidden when welcome screen is shown */}
            {!(mode === 'upload' && uploadMessages.length === 0) && (
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
                                    onEditAnswer={mode === 'outline_chat' ? handleEditAnswer : null}
                                    mode={mode}
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

                                {msg.type === 'translation_result' && msg.translationResults && (
                                    <TranslationResults results={msg.translationResults} />
                                )}

                                {msg.type === 'image_prompt_review' && msg.enhancedPrompts && (
                                    <ImagePromptReview
                                        enhancedPrompts={msg.enhancedPrompts}
                                        projectId={msg.projectId}
                                        onGenerateComplete={(result) => {
                                            // Add gallery message when images are generated
                                            const galleryMessage = {
                                                id: Date.now(),
                                                role: 'assistant',
                                                content: `🖼️ Images Generated!\n\n` +
                                                    `Generated: ${result.generated} images\n` +
                                                    `Failed: ${result.failed}`,
                                                type: 'image_gallery',
                                                imageData: result,
                                                projectId: msg.projectId
                                            };
                                            setUploadMessages(prev => [...prev, galleryMessage]);
                                        }}
                                    />
                                )}

                                {msg.type === 'image_gallery' && msg.imageData && (
                                    <ImageGallery
                                        imageData={msg.imageData}
                                        projectId={msg.projectId}
                                    />
                                )}

                                {msg.type === 'slides_result' && msg.slidesData && (
                                    <SlidesPreview
                                        slidesData={msg.slidesData}
                                    />
                                )}

                                {msg.type === 'batch_compliance_result' && msg.batchResults && (
                                    <BatchResultsList
                                        batchResults={msg.batchResults}
                                        batchSummary={msg.batchSummary}
                                        type="compliance"
                                    />
                                )}

                                {msg.type === 'batch_quality_result' && msg.batchResults && (
                                    <BatchResultsList
                                        batchResults={msg.batchResults}
                                        batchSummary={msg.batchSummary}
                                        type="quality"
                                    />
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
            )}

            {/* Input Area */}
            <InputArea
                mode={mode}
                onSendMessage={handleSendMessage}
                onUploadScript={handleUploadScript}
                onScriptToWiki={handleScriptToWiki}
                onSendText={handleSendChatText}
                disabled={isTyping}
                isWelcome={mode === 'upload' && uploadMessages.length === 0}
                stagedFile={stagedFile}
                setStagedFile={setStagedFile}
                onConfirmStagedFile={handleConfirmStagedFile}
                onCancelStagedFile={handleCancelStagedFile}
            />

            {/* Batch Upload Modal */}
            <BatchUploadModal
                isOpen={isBatchModalOpen}
                onClose={() => setIsBatchModalOpen(false)}
                onUpload={handleBatchUpload}
            />

            {/* Translation Modal */}
            <TranslationModal
                isOpen={isTranslationModalOpen}
                onClose={() => {
                    setIsTranslationModalOpen(false);
                    setTranslationFile(null);
                }}
                file={translationFile}
                onTranslate={handleTranslation}
            />

            {/* Ask AI Chat - only show in outline_chat mode */}
            {mode === 'outline_chat' && <AskAIChat />}

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
