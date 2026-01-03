/**
 * Main chat area hook - orchestrates all sub-hooks.
 * This is a slim coordinator that composes focused hooks for each feature area.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { loadFromLocalStorage, saveToLocalStorage, clearStorage } from '../utils/chatStorage';

// Sub-hooks
import { useUploadHandlers } from './useUploadHandlers';
import { useSidebarHandlers } from './useSidebarHandlers';
import { useGenerationHandlers } from './useGenerationHandlers';
import { useOutlineChat } from './useOutlineChat';
import { useExportHandlers } from './useExportHandlers';

// Default messages
const DEFAULT_UPLOAD_MESSAGE = {
    id: 1,
    role: 'assistant',
    content: 'Hello! Please upload your tutorial content to get started. I\'ll help you generate a script, slides, and video from it.'
};

/**
 * Main hook for ChatArea state and business logic.
 * Composes smaller, focused hooks for each feature area.
 */
export function useChatArea() {
    // =========================
    // CORE STATE
    // =========================

    const [mode, setMode] = useState('upload'); // 'upload' | 'outline_chat'

    // Initialize uploadMessages from localStorage or default
    const [uploadMessages, setUploadMessages] = useState(() => {
        const saved = loadFromLocalStorage();
        if (saved?.uploadMessages?.length > 0) {
            console.log('📂 Restored session from localStorage');
            return saved.uploadMessages;
        }
        return [DEFAULT_UPLOAD_MESSAGE];
    });

    const [isTyping, setIsTyping] = useState(false);

    // Initialize currentProjectId from localStorage or null
    const [currentProjectId, setCurrentProjectId] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.currentProjectId || null;
    });

    // =========================
    // UI STATE
    // =========================

    const [copiedId, setCopiedId] = useState(null);
    const [openEditorId, setOpenEditorId] = useState(null);
    const [openReportId, setOpenReportId] = useState(null);
    const [openQualityId, setOpenQualityId] = useState(null);
    const [qualityReports, setQualityReports] = useState({});
    const [isQualityLoading, setIsQualityLoading] = useState(false);

    // Global staging state (shared between Sidebar and InputArea)
    const [stagedFile, setStagedFile] = useState(null);

    // Session restored flag
    const [sessionRestored, setSessionRestored] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.uploadMessages?.length > 1;
    });

    // =========================
    // REFS
    // =========================

    const messagesEndRef = useRef(null);
    const editedScriptInputRef = useRef(null);

    // =========================
    // COMPOSE SUB-HOOKS
    // =========================

    // Upload handlers (outline, script, wiki)
    const uploadHandlers = useUploadHandlers(
        setUploadMessages,
        setIsTyping,
        setCurrentProjectId
    );

    // Sidebar handlers (compliance, quality, voice, images, slides)
    const sidebarHandlers = useSidebarHandlers(
        setUploadMessages,
        setIsTyping,
        setCurrentProjectId,
        setQualityReports,
        setOpenReportId,
        setOpenQualityId
    );

    // Generation handlers (script, slides, video)
    const generationHandlers = useGenerationHandlers(
        setUploadMessages,
        setIsTyping,
        currentProjectId,
        uploadMessages
    );

    // Outline chat (messages, session, handlers)
    const outlineChat = useOutlineChat(mode, setIsTyping);

    // Export handlers (DOCX, MediaWiki, quality)
    const exportHandlers = useExportHandlers(
        setUploadMessages,
        setIsTyping,
        setQualityReports,
        setOpenQualityId,
        setIsQualityLoading
    );

    // =========================
    // COMPUTED
    // =========================

    const activeMessages = mode === 'outline_chat' ? outlineChat.outlineMessages : uploadMessages;

    // =========================
    // EFFECTS
    // =========================

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [activeMessages, isTyping, mode, scrollToBottom]);

    // Auto-save upload mode state to localStorage
    useEffect(() => {
        if (mode === 'upload' && uploadMessages.length > 0) {
            saveToLocalStorage(uploadMessages, currentProjectId);
        }
    }, [uploadMessages, currentProjectId, mode]);

    // =========================
    // SESSION HANDLERS
    // =========================

    const handleClearSession = useCallback(() => {
        if (window.confirm('Clear all upload data and start fresh? This cannot be undone.')) {
            clearStorage();
            setUploadMessages([DEFAULT_UPLOAD_MESSAGE]);
            setCurrentProjectId(null);
            setOpenEditorId(null);
            setSessionRestored(false);
            console.log('🗑️ Session cleared');
        }
    }, []);

    // =========================
    // STAGING HANDLERS
    // =========================

    const handleConfirmStagedFile = useCallback(() => {
        if (!stagedFile) return;

        const { file, files, type } = stagedFile;

        switch (type) {
            case 'script':
                uploadHandlers.handleUploadScript(file);
                break;
            case 'wiki':
                uploadHandlers.handleScriptToWiki(file);
                break;
            case 'compliance':
                sidebarHandlers.handleSidebarComplianceUpload(file);
                break;
            case 'quality':
                sidebarHandlers.handleSidebarQualityUpload(file);
                break;
            case 'voice':
                sidebarHandlers.handleSidebarVoiceUpload(file);
                break;
            case 'images':
                sidebarHandlers.handleSidebarImageUpload(file);
                break;
            case 'slides':
                sidebarHandlers.handleSlidesUpload(file);
                break;
            case 'batch_compliance':
                // Multiple files for batch processing
                sidebarHandlers.handleSidebarBatchComplianceUpload(files);
                break;
            case 'outline':
            default:
                uploadHandlers.handleSendMessage(file);
        }

        setStagedFile(null);
    }, [stagedFile, uploadHandlers, sidebarHandlers]);

    const handleCancelStagedFile = useCallback(() => {
        setStagedFile(null);
    }, []);

    // =========================
    // RETURN MERGED API
    // =========================

    return {
        // Core State
        mode,
        setMode,
        uploadMessages,
        setUploadMessages,
        isTyping,
        currentProjectId,
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
        setQualityReports,
        isQualityLoading,
        sessionRestored,

        // Refs
        messagesEndRef,
        editedScriptInputRef,

        // Session
        handleClearSession,

        // Staging (shared between Sidebar and InputArea)
        stagedFile,
        setStagedFile,
        handleConfirmStagedFile,
        handleCancelStagedFile,

        // Outline Chat state (from sub-hook)
        outlineMessages: outlineChat.outlineMessages,
        outlineSession: outlineChat.outlineSession,

        // === SPREAD HANDLERS FROM SUB-HOOKS ===

        // Upload handlers
        handleSendMessage: uploadHandlers.handleSendMessage,
        handleUploadScript: uploadHandlers.handleUploadScript,
        handleScriptToWiki: uploadHandlers.handleScriptToWiki,

        // Sidebar handlers
        handleSidebarComplianceUpload: sidebarHandlers.handleSidebarComplianceUpload,
        handleSidebarQualityUpload: sidebarHandlers.handleSidebarQualityUpload,
        handleSidebarVoiceUpload: sidebarHandlers.handleSidebarVoiceUpload,
        handleSidebarImageUpload: sidebarHandlers.handleSidebarImageUpload,
        handleSidebarSlidesUpload: sidebarHandlers.handleSlidesUpload,
        handleSidebarBatchComplianceUpload: sidebarHandlers.handleSidebarBatchComplianceUpload,
        handleSidebarBatchQualityUpload: sidebarHandlers.handleSidebarBatchQualityUpload,
        handleSidebarScriptUpload: uploadHandlers.handleSendMessage, // Reuse upload handler

        // Generation handlers
        handleGenerateScript: generationHandlers.handleGenerateScript,
        handleGenerateSlides: generationHandlers.handleGenerateSlides,
        handleCreateSlides: generationHandlers.handleCreateSlides,
        handleApprove: generationHandlers.handleApprove,

        // Outline Chat handlers
        handleSendChatText: outlineChat.handleSendChatText,
        handleConfirmation: outlineChat.handleConfirmation,
        handleEditAnswer: outlineChat.handleEditAnswer,

        // Export handlers
        handleDownloadScriptDocx: exportHandlers.handleDownloadScriptDocx,
        handleUploadEditedScript: exportHandlers.handleUploadEditedScript,
        handleExportMediaWiki: exportHandlers.handleExportMediaWiki,
        handleSaveScriptEdit: exportHandlers.handleSaveScriptEdit,
        handleQualityCheck: exportHandlers.handleQualityCheck,
    };
}
