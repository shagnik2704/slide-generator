import React, { forwardRef, useImperativeHandle } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, UploadCloud, MessageSquare, Trash2, RefreshCw, Image, Mic, Languages, Presentation } from 'lucide-react';

// Components
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import ThemeToggle from './ThemeToggle';
import OutlineCard from './OutlineCard';
import VoicePreview from './VoicePreview';
import ImagePromptReview from './ImagePromptReview';
import ImageGallery from './ImageGallery';
import ImageWorkflow from './ImageWorkflow';
import SlidesPreview from './SlidesPreview';
import AskAIChat from './AskAIChat';
import BatchUploadModal from './BatchUploadModal';
import BatchResultsList from './BatchResultsList';
import UserProfile from './UserProfile';
import TranslationModal from './TranslationModal';
import TranslationResults from './TranslationResults';
import RedesignForm from './RedesignForm';
import ComplianceReport from './ComplianceReport';
import CollapsibleSection from './CollapsibleSection';
import WorkflowCard from './WorkflowCard';
import QualityCheckModal from './QualityCheckModal';

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
import { apiJson, apiFormData } from '../services/api';

const timedScriptSteps = (filename, job) => {
    const isComplete = job.status === 'completed';
    const isFailed = job.status === 'failed';
    const isTranscribing = job.status === 'running' || job.current_stage === 'transcribing';

    return [
        { label: `Uploading ${filename}`, status: 'complete' },
        {
            label: 'Transcribing audio with Whisper',
            status: isTranscribing || isComplete ? (isComplete ? 'complete' : 'processing') : 'pending',
        },
        {
            label: isFailed ? 'Timed script failed' : 'Generating sentence timestamps',
            status: isComplete ? 'complete' : (isFailed ? 'error' : 'pending'),
        },
    ];
};

const timedScriptWorkflowFromJob = (job) => ({
    id: job.job_id,
    jobId: job.job_id,
    type: 'workflow',
    tool: 'timed_script',
    filename: job.original_filename || 'timed script audio',
    status: job.status === 'completed' ? 'complete' : (job.status === 'failed' ? 'error' : 'processing'),
    currentStep: job.status === 'completed' ? 3 : (job.status === 'running' ? 1 : 0),
    steps: timedScriptSteps(job.original_filename || 'audio', job),
    role: 'assistant',
    error: job.error_message || undefined,
    result: job.result ? { timedScriptData: job.result } : undefined,
});

/**
 * ChatArea - Main chat interface component
 * 
 * This component handles the presentation layer for the chat interface.
 * All business logic and state management is handled by the useChatArea hook.
 */
const ChatArea = forwardRef(({ toggleSidebar, isSidebarOpen, initialMode = 'create', showSidebarToggle = true }, ref) => {
    const location = useLocation();
    const {
        // State (mode from hook can be 'create' | 'outline_chat' | 'redesign')
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
        setQualityReports,
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
        handleCheckCompliance,
        handleUpdateOutlineComplianceReport,
        handleDownloadScriptDocx,
        handleUploadEditedScript,
        handleSaveScriptEdit,
        handleQualityCheck,
        handleRedesignSubmit,

        // Staging
        stagedFile,
        setStagedFile,
        handleConfirmStagedFile,
        handleCancelStagedFile,
    } = useChatArea(initialMode);

    // Batch Modal State
    const [isBatchModalOpen, setIsBatchModalOpen] = React.useState(false);
    const [batchMode, setBatchMode] = React.useState('compliance'); // 'compliance' | 'quality'

    // Translation Modal State
    const [isTranslationModalOpen, setIsTranslationModalOpen] = React.useState(false);
    const [translationFile, setTranslationFile] = React.useState(null);
    const [translationMode, setTranslationMode] = React.useState('script');  // 'script' or 'slides'

    // Auto-open translation modal when a translation file is staged
    React.useEffect(() => {
        if (stagedFile?.type === 'translation') {
            setTranslationFile(stagedFile.file);
            setTranslationMode('script');
            setIsTranslationModalOpen(true);
            setStagedFile(null);  // Clear staging since modal takes over
        } else if (stagedFile?.type === 'slides_translation') {
            setTranslationFile(stagedFile.file);
            setTranslationMode('slides');
            setIsTranslationModalOpen(true);
            setStagedFile(null);  // Clear staging since modal takes over
        }
    }, [stagedFile, setStagedFile]);

    // Quality Check Modal State
    const [isQualityModalOpen, setIsQualityModalOpen] = React.useState(false);
    const [qualityModalFile, setQualityModalFile] = React.useState(null);  // For single sidebar flow
    const [batchQualityFiles, setBatchQualityFiles] = React.useState(null); // For batch sidebar flow
    const [qualityModalMessage, setQualityModalMessage] = React.useState(null);  // For message button flow

    // Restore previously submitted timed-script jobs when the user returns.
    React.useEffect(() => {
        let cancelled = false;
        apiJson('/timed-script/jobs')
            .then(({ jobs = [] }) => {
                if (cancelled) return;
                const restored = jobs.map(timedScriptWorkflowFromJob);
                setUploadMessages(prev => {
                    const existingIds = new Set(prev.map(message => message.id));
                    return [...restored.filter(message => !existingIds.has(message.id)), ...prev];
                });
            })
            .catch(() => {
                // Job history is supplementary; the rest of ChatArea remains usable.
            });

        return () => {
            cancelled = true;
        };
    }, [setUploadMessages]);

    // Auto-open quality modal when a quality file is staged from sidebar
    React.useEffect(() => {
        if (stagedFile?.type === 'quality') {
            setQualityModalFile(stagedFile.file);
            setBatchQualityFiles(null);
            setIsQualityModalOpen(true);
            setStagedFile(null);  // Clear staging since modal takes over
        }
    }, [stagedFile, setStagedFile]);

    // Timed Script Workflow Handler - uses WorkflowCard instead of modal
    const handleTimedScriptGeneration = async (file) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'timed_script',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Uploading ${file.name}`, status: 'processing' },
                { label: 'Transcribing audio with Whisper', status: 'pending' },
                { label: 'Generating sentence timestamps', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);

        try {
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'processing',
                } : msg
            ));

            const formData = new FormData();
            formData.append('audio', file);
            const queuedJob = await apiFormData('/timed-script/generate', formData);
            const jobId = queuedJob.job_id;

            const updateFromJob = (job) => {
                const workflow = timedScriptWorkflowFromJob(job);
                setUploadMessages(prev => prev.map(msg => (
                    msg.id === workflowId ? { ...msg, ...workflow } : msg
                )));
            };

            let job = queuedJob;
            while (job.status !== 'completed' && job.status !== 'failed') {
                updateFromJob(job);
                await new Promise(resolve => setTimeout(resolve, 1500));
                job = await apiJson(`/timed-script/jobs/${jobId}`);
            }
            updateFromJob(job);

        } catch (error) {
            console.error('Timed script generation error:', error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message || 'Failed to generate timed script'
                } : msg
            ));
        }
    };

    // Wrapped confirm handler that intercepts timed_script type
    const wrappedHandleConfirmStagedFile = (options) => {
        if (stagedFile?.type === 'timed_script') {
            handleTimedScriptGeneration(stagedFile.file);
            setStagedFile(null);
        } else {
            handleConfirmStagedFile(options);
        }
    };


    // Handler to open quality check modal with message context (for message button flow)
    const handleOpenQualityModal = (msg) => {
        setQualityModalMessage(msg);
        setQualityModalFile(null);
        setBatchQualityFiles(null);
        setIsQualityModalOpen(true);
    };

    // Handler for quality check with language selection
    const handleQualityCheckWithLanguage = async ({ jsonScript, languageCode }) => {
        // If triggered from batch quality floral
        if (batchQualityFiles) {
            await handleSidebarBatchQualityUpload(batchQualityFiles, languageCode);
            setBatchQualityFiles(null);
            return;
        }

        // If triggered from sidebar (single file flow), run the sidebar quality upload with WorkflowCard
        if (qualityModalFile) {
            const workflowId = Date.now();
            const initialWorkflow = {
                id: workflowId,
                type: 'workflow',
                tool: 'quality_check',
                filename: qualityModalFile.name,
                status: 'processing',
                currentStep: 0,
                steps: [
                    { label: `Parsing ${qualityModalFile.name}`, status: 'processing' },
                    { label: `Translating (English ↔ Target Language)`, status: 'pending' },
                    { label: 'Analyzing quality', status: 'pending' }
                ],
                role: 'assistant'
            };

            setUploadMessages(prev => [...prev, initialWorkflow]);

            try {
                // Step 1: Parse the script
                const formData = new FormData();
                formData.append('file', qualityModalFile);
                const parseData = await apiFormData('/parse_script', formData);

                // Update to Step 2
                setUploadMessages(prev => prev.map(msg =>
                    msg.id === workflowId ? {
                        ...msg,
                        currentStep: 1,
                        steps: [
                            { label: `Parsing ${qualityModalFile.name}`, status: 'complete' },
                            { label: `Translating (English ↔ Target Language)`, status: 'processing' },
                            { label: 'Analyzing quality', status: 'pending' }
                        ]
                    } : msg
                ));

                // Step 2 & 3: Run quality check (includes translation and comparison)
                const qualityData = await apiJson('/check_quality', {
                    method: 'POST',
                    body: JSON.stringify({
                        json_script: parseData.json_script,
                        language_code: languageCode
                    })
                });

                // Update to Step 3 (complete)
                setUploadMessages(prev => prev.map(msg =>
                    msg.id === workflowId ? {
                        ...msg,
                        currentStep: 2,
                        steps: [
                            { label: `Parsing ${qualityModalFile.name}`, status: 'complete' },
                            { label: `Translating (English ↔ ${qualityData.language_name})`, status: 'complete' },
                            { label: 'Analyzing quality', status: 'processing' }
                        ]
                    } : msg
                ));

                // Small delay for visual feedback
                await new Promise(r => setTimeout(r, 500));

                // Update to Complete
                setUploadMessages(prev => prev.map(msg =>
                    msg.id === workflowId ? {
                        ...msg,
                        status: 'complete',
                        currentStep: 3,
                        steps: [
                            { label: `Parsing ${qualityModalFile.name}`, status: 'complete' },
                            { label: `Translating (English ↔ ${qualityData.language_name})`, status: 'complete' },
                            { label: 'Quality analysis complete', status: 'complete' }
                        ],
                        result: {
                            qualityReport: qualityData,
                            jsonScript: parseData.json_script
                        }
                    } : msg
                ));

                // Store quality report and auto-open
                setQualityReports(prev => ({ ...prev, [workflowId]: qualityData }));
                setOpenQualityId(workflowId);

            } catch (error) {
                console.error('Quality check error:', error);
                setUploadMessages(prev => prev.map(msg =>
                    msg.id === workflowId ? {
                        ...msg,
                        status: 'error',
                        error: error.message
                    } : msg
                ));
            }

            setQualityModalFile(null);
            return;
        }

        // If triggered from message button flow
        if (qualityModalMessage) {
            await handleQualityCheck(jsonScript, qualityModalMessage.id, languageCode);
            setQualityModalMessage(null);
        }
    };

    // Handler to close modal and start upload based on mode
    const handleBatchUpload = (files) => {
        if (batchMode === 'quality') {
            // Step 1 of 2: Store files and open language selection modal
            setBatchQualityFiles(files);
            setQualityModalFile(null);
            setQualityModalMessage(null);
            setIsQualityModalOpen(true);
        } else {
            handleSidebarBatchComplianceUpload(files);
        }
        setIsBatchModalOpen(false);
    };

    // Translation handler - handles both script and slides translation
    const handleTranslation = async ({ file, languages, translateVisualCues, mode: translationModeParam }) => {
        // Route to appropriate handler based on mode
        if (translationModeParam === 'slides') {
            return handleSlidesTranslation({ file, languages });
        }
        return handleScriptTranslation({ file, languages, translateVisualCues });
    };

    // Script translation handler (original logic)
    const handleScriptTranslation = async ({ file, languages, translateVisualCues }) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'translation',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: `Translating to ${languages.length} language(s)`, status: 'pending' },
                { label: 'Translation ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: `Translating to ${languages.length} language(s)`, status: 'processing' },
                        { label: 'Translation ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Batch translate
            const translationResults = await apiJson('/translation/batch_translate', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    languages: languages,
                    translate_visual_cues: translateVisualCues
                })
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: `Translating to ${languages.length} language(s)`, status: 'complete' },
                        { label: 'Translation ready', status: 'complete' }
                    ],
                    result: {
                        translationResults: translationResults
                    }
                } : msg
            ));

        } catch (error) {
            console.error('Translation error:', error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
            throw error;
        }
    };

    // Slides translation handler (.tex files)
    const handleSlidesTranslation = async ({ file, languages }) => {
        const workflowId = Date.now();
        const targetLang = languages[0];  // Single language for slides

        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'slides_translation',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Reading ${file.name}`, status: 'processing' },
                { label: 'Translating slide content', status: 'pending' },
                { label: 'Adding XeLaTeX support', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);

        try {
            // Step 1: Upload and parse .tex file
            const formData = new FormData();
            formData.append('file', file);
            formData.append('target_language', targetLang);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Reading ${file.name}`, status: 'complete' },
                        { label: 'Translating slide content', status: 'processing' },
                        { label: 'Adding XeLaTeX support', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2 & 3: Translate slides
            const translationResult = await apiFormData('/translate_slides', formData);

            // Update to Step 3
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 2,
                    steps: [
                        { label: `Reading ${file.name}`, status: 'complete' },
                        { label: 'Translating slide content', status: 'complete' },
                        { label: 'Adding XeLaTeX support', status: 'processing' }
                    ]
                } : msg
            ));

            // Small delay for visual feedback
            await new Promise(r => setTimeout(r, 500));

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Reading ${file.name}`, status: 'complete' },
                        { label: 'Translating slide content', status: 'complete' },
                        { label: 'XeLaTeX ready', status: 'complete' }
                    ],
                    result: {
                        slidesTranslation: translationResult
                    }
                } : msg
            ));

        } catch (error) {
            console.error('Slides translation error:', error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message || 'Failed to translate slides'
                } : msg
            ));
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
        setMode,  // Expose setMode for mode switching
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

    // Helper to update compliance report in a message (for create mode)
    const handleUpdateComplianceReport = (messageId, updatedReport) => {
        if (mode === 'create') {
            setUploadMessages(prev => prev.map(m =>
                m.id === messageId ? { ...m, complianceReport: updatedReport } : m
            ));
        }
        // For outline_chat mode, use handleUpdateOutlineComplianceReport
    };

    return (
        <main style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            position: 'relative',
            overflowX: 'hidden'
        }}>
            {/* Header */}
            <header className="chat-header" style={{
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
                            className="hamburger-btn"
                            onClick={toggleSidebar}
                            style={{
                                background: isSidebarOpen ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                                border: 'none',
                                color: isSidebarOpen ? 'white' : 'var(--text-primary)',
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
                        {/* Full title - hidden on mobile */}
                        <div className="header-title-full" style={{
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
                        {/* Short title - shown only on mobile */}
                        <div className="header-title-short" style={{
                            fontWeight: 600,
                            fontSize: '1rem',
                            fontFamily: '"Outfit", sans-serif',
                            display: 'none',
                            alignItems: 'center',
                            gap: '0.25rem'
                        }}>
                            <span style={{ color: 'var(--accent-secondary)' }}>STG</span>
                        </div>
                    </Link>
                </div>
                <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                    {/* Mode Navigation - hidden on mobile */}
                    <div className="hide-on-mobile" style={{
                        display: 'flex',
                        background: 'var(--bg-secondary)',
                        borderRadius: '0.75rem',
                        padding: '0.2rem',
                        boxShadow: 'var(--shadow-sm)',
                        border: '1px solid var(--border-color)',
                        gap: '0.2rem'
                    }}>
                        <Link
                            to="/create"
                            onClick={() => setMode('create')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.3rem 0.6rem',
                                borderRadius: '0.6rem',
                                border: 'none',
                                background: (location.pathname === '/create' && mode === 'create')
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: (location.pathname === '/create' && mode === 'create') ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                boxShadow: (location.pathname === '/create' && mode === 'create') ? 'var(--shadow-sm)' : 'none',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <UploadCloud size={16} />
                            Create Mode
                        </Link>
                        <Link
                            to="/outline-chat"
                            onClick={() => setMode('outline_chat')}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.3rem 0.6rem',
                                borderRadius: '0.6rem',
                                border: 'none',
                                background: (location.pathname === '/outline-chat' && mode === 'outline_chat')
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: (location.pathname === '/outline-chat' && mode === 'outline_chat') ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                boxShadow: (location.pathname === '/outline-chat' && mode === 'outline_chat') ? 'var(--shadow-sm)' : 'none',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <MessageSquare size={16} />
                            Outline Chat
                        </Link>
                        <Link
                            to="/create"
                            onClick={(e) => { e.preventDefault(); setMode('redesign'); }}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.3rem 0.6rem',
                                borderRadius: '0.6rem',
                                border: 'none',
                                background: mode === 'redesign'
                                    ? 'var(--accent-primary)'
                                    : 'transparent',
                                color: mode === 'redesign' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                boxShadow: mode === 'redesign' ? 'var(--shadow-sm)' : 'none',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            <RefreshCw size={16} />
                            Redesign
                        </Link>
                    </div>

                    {/* Clear Session button */}
                    {mode === 'create' && uploadMessages.length > 0 && (
                        <button
                            className="clear-session-btn"
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
                            <span>Clear Session</span>
                        </button>
                    )}

                    <ThemeToggle />

                    {/* User Profile - Compact version in header (always show on mobile) */}
                    {showSidebarToggle && (
                        <div className="header-user-profile" style={{ marginLeft: '0.5rem' }}>
                            <UserProfile compact={true} />
                        </div>
                    )}
                </div>
            </header>

            {/* Messages Area - always shown except for create mode welcome screen */}
            {!(mode === 'create' && uploadMessages.length === 0) && (
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '6rem 1rem 1rem 1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                }}>
                    <div style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
                        {/* Redesign Form - always shown in redesign mode */}
                        {mode === 'redesign' && (
                            <RedesignForm
                                onSubmit={handleRedesignSubmit}
                                onCancel={() => setMode('create')}
                            />
                        )}

                        {/* Message list */}
                        {activeMessages.map((msg) => (
                            <div key={msg.id}>
                                {msg.type === 'workflow' ? (
                                    <WorkflowCard
                                        workflow={msg}
                                        isTyping={isTyping}
                                        openReportId={openReportId}
                                        setOpenReportId={setOpenReportId}
                                        openQualityId={openQualityId}
                                        setOpenQualityId={setOpenQualityId}
                                        qualityReports={qualityReports}
                                        isQualityLoading={isQualityLoading}
                                        onQualityCheck={handleQualityCheck}
                                        onUpdateComplianceReport={handleUpdateOutlineComplianceReport}
                                        // Script-related props
                                        openEditorId={openEditorId}
                                        setOpenEditorId={setOpenEditorId}
                                        onDownloadScriptDocx={handleDownloadScriptDocx}
                                        onSaveScriptEdit={handleSaveScriptEdit}
                                    />
                                ) : (
                                    <MessageBubble
                                        message={msg}
                                        onConfirmation={mode === 'outline_chat' ? handleConfirmation : null}
                                        onEditAnswer={mode === 'outline_chat' ? handleEditAnswer : null}
                                        mode={mode}
                                        onShareComplete={(recipients) => {
                                            console.log('Share complete callback received with:', recipients);
                                            const shareMessage = {
                                                id: Date.now() + 2,
                                                role: 'assistant',
                                                content: recipients.map(r => `✅ Sheet shared to ${r.email} as ${r.role}`).join('\n')
                                            };
                                            console.log('Adding share message:', shareMessage);
                                            setUploadMessages(prev => {
                                                const updated = [...prev, shareMessage];
                                                console.log('Updated messages:', updated);
                                                return updated;
                                            });
                                        }}
                                    />
                                )}

                                {/* OutlineCard for outline_chat mode */}
                                {mode === 'outline_chat' && msg.outlineData && msg.phase === 'review' && (
                                    <OutlineCard
                                        outlineData={msg.outlineData}
                                        projectId={outlineSession.projectId || msg.outlineData?.project_id}
                                        messageId={msg.id}
                                        complianceReport={msg.complianceReport}
                                        openReportId={openReportId}
                                        setOpenReportId={setOpenReportId}
                                        onCheckCompliance={handleCheckCompliance}
                                        onUpdateComplianceReport={handleUpdateOutlineComplianceReport}
                                        isTyping={isTyping}
                                    />
                                )}

                                {/* Message Action Components */}
                                {mode === 'create' && msg.type === 'outline_uploaded' && (
                                    <OutlineUploadedActions
                                        msg={msg}
                                        isTyping={isTyping}
                                        onGenerateScript={handleGenerateScript}
                                    />
                                )}



                                {mode === 'create' && msg.type === 'script_uploaded' && (
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
                                        onOpenQualityModal={handleOpenQualityModal}
                                        onUpdateComplianceReport={handleUpdateComplianceReport}
                                    />
                                )}

                                {mode === 'create' && msg.type === 'script_review' && (
                                    <ScriptReviewActions
                                        msg={msg}
                                        isTyping={isTyping}
                                        openEditorId={openEditorId}
                                        setOpenEditorId={setOpenEditorId}
                                        editedScriptInputRef={editedScriptInputRef}
                                        onGenerateSlides={handleGenerateSlides}
                                        onDownloadScriptDocx={handleDownloadScriptDocx}
                                        onUploadEditedScript={handleUploadEditedScript}
                                        onSaveScriptEdit={handleSaveScriptEdit}
                                    />
                                )}

                                {mode === 'create' && msg.type === 'slides_review' && (
                                    <SlidesReviewActions
                                        msg={msg}
                                        isTyping={isTyping}
                                        onApprove={handleApprove}
                                    />
                                )}

                                {mode === 'create' && msg.type === 'video_result' && (
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
                                    <CollapsibleSection
                                        title="Voice Preview"
                                        icon={<Mic size={18} />}
                                        subtitle={`${msg.voiceData?.samples?.length || 0} samples`}
                                        defaultOpen={true}
                                    >
                                        <VoicePreview voiceData={msg.voiceData} isOpen={true} />
                                    </CollapsibleSection>
                                )}

                                {msg.type === 'translation_result' && msg.translationResults && (
                                    <CollapsibleSection
                                        title="Translation Results"
                                        icon={<Languages size={18} />}
                                        subtitle={`${msg.translationResults?.total_success || 0} languages`}
                                        defaultOpen={true}
                                    >
                                        <TranslationResults results={msg.translationResults} />
                                    </CollapsibleSection>
                                )}

                                {msg.type === 'image_prompt_review' && msg.enhancedPrompts && (
                                    <CollapsibleSection
                                        title="Image Workflow"
                                        icon={<Image size={18} />}
                                        defaultOpen={true}
                                    >
                                        <ImageWorkflow
                                            enhancedPrompts={msg.enhancedPrompts}
                                            projectId={msg.projectId}
                                        />
                                    </CollapsibleSection>
                                )}

                                {msg.type === 'image_gallery' && msg.imageData && (
                                    <CollapsibleSection
                                        title="Generated Images"
                                        icon={<Image size={18} />}
                                        subtitle={`${msg.imageData?.generated || 0} images`}
                                        defaultOpen={true}
                                    >
                                        <ImageGallery
                                            imageData={msg.imageData}
                                            projectId={msg.projectId}
                                        />
                                    </CollapsibleSection>
                                )}

                                {msg.type === 'slides_result' && msg.slidesData && (
                                    <CollapsibleSection
                                        title="Slides Preview"
                                        icon={<Presentation size={18} />}
                                        defaultOpen={true}
                                    >
                                        <SlidesPreview
                                            slidesData={msg.slidesData}
                                        />
                                    </CollapsibleSection>
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

                                {/* Outline Compliance Result - Show ComplianceReport component */}
                                {mode === 'outline_chat' && msg.type === 'outline_compliance_result' && msg.complianceReport && (
                                    <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                        {/* View Report Button */}
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

                                        {/* Compliance Report */}
                                        <ComplianceReport
                                            report={msg.complianceReport}
                                            isOpen={openReportId === msg.id}
                                            onSave={(updated) => {
                                                handleUpdateOutlineComplianceReport(msg.id, updated);
                                            }}
                                            onClose={() => setOpenReportId(null)}
                                        />
                                    </div>
                                )}
                            </div>
                        ))}

                        <div ref={messagesEndRef} />
                    </div>
                </div>
            )}

            {/* Input Area - hidden in redesign mode */}
            {mode !== 'redesign' && (
                <InputArea
                    mode={mode}
                    onSendMessage={handleSendMessage}
                    onUploadScript={handleUploadScript}
                    onScriptToWiki={handleScriptToWiki}
                    onSendText={handleSendChatText}
                    disabled={isTyping}
                    isWelcome={mode === 'create' && uploadMessages.length === 0}
                    stagedFile={stagedFile}
                    setStagedFile={setStagedFile}
                    onConfirmStagedFile={wrappedHandleConfirmStagedFile}
                    onCancelStagedFile={handleCancelStagedFile}
                />
            )}

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
                    setTranslationMode('script');
                }}
                file={translationFile}
                mode={translationMode}
                onTranslate={handleTranslation}
            />

            {/* Quality Check Modal - Single language selection */}
            <QualityCheckModal
                isOpen={isQualityModalOpen}
                onClose={() => {
                    setIsQualityModalOpen(false);
                    setQualityModalFile(null);
                    setQualityModalMessage(null);
                }}
                file={qualityModalFile || qualityModalMessage?.file}
                jsonScript={qualityModalMessage?.jsonScript}
                onSubmit={handleQualityCheckWithLanguage}
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
