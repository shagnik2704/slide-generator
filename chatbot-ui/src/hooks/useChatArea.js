import { useState, useEffect, useRef, useCallback } from 'react';
import { loadFromLocalStorage, saveToLocalStorage, clearStorage } from '../utils/chatStorage';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Default messages
const DEFAULT_UPLOAD_MESSAGE = {
    id: 1,
    role: 'assistant',
    content: 'Hello! Please upload your tutorial content to get started. I\'ll help you generate a script, slides, and video from it.'
};

const DEFAULT_OUTLINE_MESSAGE = {
    id: 2,
    role: 'assistant',
    content: 'Hi! 😊 I\'m here to help you create a Spoken Tutorial course outline, step by step.\n\nTo start, could you tell me what kind of course this is: **FOSS**, **ICT**, or **Other**?\n\nJust reply with `FOSS`, `ICT`, or `Other` (you can add a short note if you pick Other). Then I\'ll gently walk you through a few short questions.',
};

/**
 * Custom hook for ChatArea state and business logic
 */
export function useChatArea() {
    // Mode state
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

    const [outlineMessages, setOutlineMessages] = useState([DEFAULT_OUTLINE_MESSAGE]);
    const [outlineSession, setOutlineSession] = useState({ projectId: null, outlineData: null, phase: null });
    const [isTyping, setIsTyping] = useState(false);

    // Initialize currentProjectId from localStorage or null
    const [currentProjectId, setCurrentProjectId] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.currentProjectId || null;
    });

    // UI state
    const [copiedId, setCopiedId] = useState(null);
    const [openEditorId, setOpenEditorId] = useState(null);
    const [openReportId, setOpenReportId] = useState(null);
    const [openQualityId, setOpenQualityId] = useState(null);
    const [qualityReports, setQualityReports] = useState({});
    const [isQualityLoading, setIsQualityLoading] = useState(false);

    // Global staging state (shared between Sidebar and InputArea)
    const [stagedFile, setStagedFile] = useState(null);

    // Refs
    const messagesEndRef = useRef(null);
    const editedScriptInputRef = useRef(null);

    // Session restored flag
    const [sessionRestored, setSessionRestored] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.uploadMessages?.length > 1;
    });

    // Computed
    const activeMessages = mode === 'outline_chat' ? outlineMessages : uploadMessages;

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
    // UPLOAD HANDLERS
    // =========================

    const handleSendMessage = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Uploading content: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_URL}/upload_outline`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to upload content');
            }

            const data = await response.json();
            const projectId = Date.now();
            setCurrentProjectId(projectId);

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Content uploaded successfully!\n\nYou can now generate the script.`,
                outline: data.outline,
                projectId: projectId,
                type: 'outline_uploaded'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleUploadScript = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Uploading script: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_URL}/upload_script`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to upload script');
            }

            const data = await response.json();
            setCurrentProjectId(data.project_id);

            const failedCount = data.compliance_report?.summary?.ai_failed || 0;
            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Script uploaded successfully! (${data.json_script.slides?.length || 0} slides)${failedCount > 0 ? `\n\n⚠️ ${failedCount} compliance issue${failedCount !== 1 ? 's' : ''} found. Check the report for details.` : ' All compliance checks passed!'} You can now generate slides directly.`,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_uploaded',
                complianceReport: data.compliance_report
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong uploading the script."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    // =========================
    // SIDEBAR HANDLERS
    // =========================

    const handleSidebarComplianceUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Running Admin Compliance check on: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData,
            });

            if (!parseResponse.ok) {
                const errorData = await parseResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to parse script file');
            }

            const parseData = await parseResponse.json();
            setCurrentProjectId(parseData.project_id);

            const complianceResponse = await fetch(`${API_URL}/check_compliance`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    tutorial_type: parseData.tutorial_type
                }),
            });

            if (!complianceResponse.ok) {
                const errorData = await complianceResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to run compliance check');
            }

            const complianceReport = await complianceResponse.json();
            const messageId = Date.now() + 1;

            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `Admin Compliance Check Complete\n\n` +
                    `Checked: ${file.name}\n` +
                    `Rows: ${parseData.json_script.slides?.length || 0}`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'script_uploaded',
                complianceReport: complianceReport,
                hideQualityCheck: true,
                hideGenerateSlides: true
            };
            setUploadMessages(prev => [...prev, newBotMessage]);
            setOpenReportId(messageId);

        } catch (error) {
            console.error("Compliance check error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Compliance check failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleSidebarQualityUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Running Quality Compliance on: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData,
            });

            if (!parseResponse.ok) {
                const errorData = await parseResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to parse script file');
            }

            const parseData = await parseResponse.json();
            setCurrentProjectId(parseData.project_id);

            const qualityResponse = await fetch(`${API_URL}/check_quality`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ json_script: parseData.json_script }),
            });

            if (!qualityResponse.ok) {
                const errorData = await qualityResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to run quality check');
            }

            const qualityData = await qualityResponse.json();
            const messageId = Date.now() + 1;

            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `Quality Compliance Check Complete\n\n` +
                    `Checked: ${file.name}\n` +
                    `Rows: ${parseData.json_script.slides?.length || 0}`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'script_uploaded',
                complianceReport: null,
                qualityReport: qualityData,  // Embedded for localStorage persistence
                hideQualityCheck: true,
                hideGenerateSlides: true
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

            setQualityReports(prev => ({ ...prev, [messageId]: qualityData }));
            setOpenQualityId(messageId);

        } catch (error) {
            console.error("Quality check error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `Quality check failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleSidebarVoiceUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `🎤 Generating voice for: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // First parse the script
            const formData = new FormData();
            formData.append('file', file);

            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData,
            });

            if (!parseResponse.ok) {
                const errorData = await parseResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to parse script file');
            }

            const parseData = await parseResponse.json();
            setCurrentProjectId(parseData.project_id);

            // Generate voice (standard approach - batched is experimental)
            const voiceResponse = await fetch(`${API_URL}/generate_voice`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id,
                    target_audience: 'general'
                }),
            });

            if (!voiceResponse.ok) {
                const errorData = await voiceResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate voice');
            }

            const voiceData = await voiceResponse.json();
            const messageId = Date.now() + 1;

            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `🎤 Voice Generation Complete!\n\n` +
                    `File: ${file.name}\n` +
                    `Generated: ${voiceData.generated_slides}/${voiceData.total_slides} slides`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'voice_preview',
                voiceData: voiceData
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Voice generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Voice generation failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleSidebarImageUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Parsing script for image generation: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);

            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData,
            });

            if (!parseResponse.ok) {
                const errorData = await parseResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to parse script file');
            }

            const parseData = await parseResponse.json();
            setCurrentProjectId(parseData.project_id);

            // Update message to show enhancing
            const enhancingMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✨ Enhancing visual cues with AI...`
            };
            setUploadMessages(prev => [...prev, enhancingMessage]);

            // Step 2: Enhance prompts
            const enhanceResponse = await fetch(`${API_URL}/enhance_prompts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id
                })
            });

            if (!enhanceResponse.ok) {
                const errorData = await enhanceResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to enhance prompts');
            }

            const enhanceData = await enhanceResponse.json();
            const messageId = Date.now() + 2;

            // Create message with review component
            const reviewMessage = {
                id: messageId,
                role: 'assistant',
                content: `Review and edit the prompts below, then click Generate.`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'image_prompt_review',
                enhancedPrompts: enhanceData.enhanced_prompts
            };
            setUploadMessages(prev => [...prev, reviewMessage]);

        } catch (error) {
            console.error("Image generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleScriptToWiki = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Converting script to MediaWiki format: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_URL}/docx_to_mediawiki`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to convert script to MediaWiki');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ ${data.message}`,
                type: 'mediawiki_export',
                mediawikiContent: data.mediawiki_content,
                mediawikiFileUrl: data.mediawiki_file_url,
                slideCount: data.slide_count
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Script to Wiki error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Conversion failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    // Handle slides generation from uploaded file
    const handleSlidesUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `🎴 Generating slides from: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);

            const parseResponse = await fetch(`${API_URL}/parse_script`, {
                method: 'POST',
                body: formData,
            });

            if (!parseResponse.ok) {
                const errorData = await parseResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to parse script file');
            }

            const parseData = await parseResponse.json();
            setCurrentProjectId(parseData.project_id);

            // Step 2: Generate slides from the parsed script
            const response = await fetch(`${API_URL}/generate_slides`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    tutorial_name: parseData.json_script?.title || file.name.replace(/\.[^/.]+$/, '')
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate slides');
            }

            const data = await response.json();

            const resultMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Beamer template generated from "${file.name}"!\n\n` +
                    `📄 ${data.filename}\n` +
                    `📊 ${data.total_slides} total slides (${data.num_boilerplate_slides} boilerplate + ${data.num_content_slides} content)\n` +
                    `✨ Auto-filled from script!`,
                type: 'slides_result',
                slidesData: data
            };
            setUploadMessages(prev => [...prev, resultMessage]);

        } catch (error) {
            console.error("Slides generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    // =========================
    // STAGING HANDLERS (Shared between Sidebar and InputArea)
    // =========================

    const handleConfirmStagedFile = useCallback(() => {
        if (!stagedFile) return;

        const { file, type } = stagedFile;

        switch (type) {
            case 'script':
                handleUploadScript(file);
                break;
            case 'wiki':
                handleScriptToWiki(file);
                break;
            case 'compliance':
                handleSidebarComplianceUpload(file);
                break;
            case 'quality':
                handleSidebarQualityUpload(file);
                break;
            case 'voice':
                handleSidebarVoiceUpload(file);
                break;
            case 'images':
                handleSidebarImageUpload(file);
                break;
            case 'slides':
                handleSlidesUpload(file);
                break;
            case 'outline':
                handleSendMessage(file);
                break;
            default:
                handleSendMessage(file);
        }

        setStagedFile(null);
    }, [stagedFile, handleUploadScript, handleScriptToWiki, handleSidebarComplianceUpload, handleSidebarQualityUpload, handleSidebarVoiceUpload, handleSidebarImageUpload, handleSlidesUpload, handleSendMessage]);

    const handleCancelStagedFile = useCallback(() => {
        setStagedFile(null);
    }, []);

    // =========================
    // SLIDES GENERATION
    // =========================

    const handleCreateSlides = useCallback(async () => {
        // Find the most recent message with a jsonScript (loaded script data)
        const scriptMessage = [...uploadMessages].reverse().find(msg => msg.jsonScript);
        const jsonScript = scriptMessage?.jsonScript;

        const tutorialName = jsonScript?.title || jsonScript?.metadata?.title || 'Tutorial Name';

        const generatingMessage = {
            id: Date.now(),
            role: 'assistant',
            content: jsonScript
                ? `🎴 Generating Beamer slides from "${tutorialName}"...`
                : `🎴 Generating Beamer slides template...`
        };
        setUploadMessages(prev => [...prev, generatingMessage]);
        setIsTyping(true);

        try {
            const response = await fetch(`${API_URL}/generate_slides`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: jsonScript || null,  // Pass script if available
                    tutorial_name: tutorialName
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate slides');
            }

            const data = await response.json();

            const resultMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Beamer template generated!\n\n` +
                    `📄 ${data.filename}\n` +
                    `📊 ${data.total_slides} total slides (${data.num_boilerplate_slides} boilerplate + ${data.num_content_slides} content)` +
                    (jsonScript ? `\n✨ Auto-filled from script!` : ''),
                type: 'slides_result',
                slidesData: data
            };
            setUploadMessages(prev => [...prev, resultMessage]);

        } catch (error) {
            console.error("Slides generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Slides generation failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [uploadMessages]);

    // =========================
    // GENERATION HANDLERS
    // =========================

    const handleGenerateScript = useCallback(async (outline, projectId) => {
        setIsTyping(true);

        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Generating script...`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const requestBody = {
                outline: outline,
                title: `Project #${projectId}`,
                project_id: projectId
            };

            const response = await fetch(`${API_URL}/generate_script`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate script');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `I've generated a script for your tutorial. Please review it below.`,
                pdfUrl: data.script_pdf_url,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_review'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating script."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleGenerateSlides = useCallback(async (jsonScript, projectId) => {
        console.log("🚀 handleGenerateSlides called with:", { jsonScript, projectId });
        setIsTyping(true);
        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Generating slides... (This might take a moment)`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const response = await fetch(`${API_URL}/generate_slides`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: jsonScript,
                    project_id: projectId || currentProjectId,
                    style_mode: "standard"
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate slides PDF');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: "Slides PDF generated! Please review the slides below.",
                pdfUrl: data.slides_pdf_url,
                pdfPath: data.pdf_path,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'slides_review'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating slides."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [currentProjectId]);

    const handleApprove = useCallback(async (jsonScript, pdfPath, projectId) => {
        setIsTyping(true);
        try {
            const response = await fetch(`${API_URL}/generate_video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    json_script: jsonScript,
                    pdf_path: pdfPath,
                    project_id: projectId || currentProjectId
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate video');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Project #${data.project_id} completed! Video generated successfully! Watch it below.`,
                videoUrl: data.video_url,
                projectId: data.project_id,
                type: 'video_result'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating the video."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [currentProjectId]);

    // =========================
    // OUTLINE CHAT HANDLERS
    // =========================

    const handleSendChatText = useCallback(async (text) => {
        if (mode !== 'outline_chat') return;
        const userMessage = { id: Date.now(), role: 'user', content: text };
        const conversationForApi = [...outlineMessages, userMessage].map(({ role, content }) => ({ role, content }));
        setOutlineMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const response = await fetch(`${API_URL}/outline_chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation: conversationForApi,
                    outline_data: outlineSession.outlineData || null,
                    project_id: outlineSession.projectId,
                    phase: outlineSession.phase || null,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to update outline');
            }

            const data = await response.json();

            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            // Update the user message with the field_name that was answered
            if (data.answered_field) {
                setOutlineMessages(prev => prev.map(msg =>
                    msg.id === userMessage.id
                        ? { ...msg, fieldName: data.answered_field, wasEdited: false }
                        : msg
                ));
            }

            let assistantContent = data.assistant_message || 'Here is the updated outline.';

            if (data.validation_errors && data.validation_errors.length > 0) {
                assistantContent += '\n\n⚠️ Issues to address:\n' + data.validation_errors.map(e => `- ${e}`).join('\n');
            }

            if (data.is_draft_ready && data.pedagogy_compliance) {
                const pc = data.pedagogy_compliance;
                assistantContent += '\n\n**Pedagogy Compliance:**\n';
                assistantContent += `- Core Example: ${pc.core_example ? '✓' : '✗'}\n`;
                assistantContent += `- Demo Content: ${pc.demo_percentage?.toFixed(1) || 0}% ${pc.demo_percentage >= 75 ? '✓' : '⚠️'}\n`;
                assistantContent += `- Menu-free: ${pc.menu_free ? '✓' : '⚠️'}\n`;
                assistantContent += `- Time checks: ${pc.time_checks ? '✓' : '⚠️'}\n`;
                assistantContent += `- No repetition: ${pc.no_repetition ? '✓' : '⚠️'}\n`;
            }

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: assistantContent,
                outlineData: data.outline_data,
                isDraftReady: data.is_draft_ready,
                isApproved: data.is_approved,
                phase: data.phase,
                needsConfirmation: data.needs_confirmation || false,
                confirmationField: data.confirmation_field,
                confirmationValue: data.confirmation_value
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);

            if (data.is_approved) {
                const exportMessage = {
                    id: Date.now() + 3,
                    role: 'assistant',
                    content: `✅ Outline approved! You can export it using:\n\`GET /outline_chat/${data.project_id}/export?format=json\``,
                    type: 'outline_approved',
                    projectId: data.project_id
                };
                setOutlineMessages(prev => [...prev, exportMessage]);
            }
        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 3,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong in outline chat."
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineMessages, outlineSession]);

    const handleConfirmation = useCallback(async (confirmed) => {
        if (mode !== 'outline_chat') return;
        const confirmationText = confirmed ? 'yes' : 'no';
        // Call handleSendChatText directly to avoid circular dependency
        const userMessage = { id: Date.now(), role: 'user', content: confirmationText };
        const conversationForApi = [...outlineMessages, userMessage].map(({ role, content }) => ({ role, content }));
        setOutlineMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const response = await fetch(`${API_URL}/outline_chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation: conversationForApi,
                    outline_data: outlineSession.outlineData || null,
                    project_id: outlineSession.projectId,
                    phase: outlineSession.phase || null,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to update outline');
            }

            const data = await response.json();

            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            let assistantContent = data.assistant_message || 'Here is the updated outline.';

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: assistantContent,
                outlineData: data.outline_data,
                isDraftReady: data.is_draft_ready,
                isApproved: data.is_approved,
                phase: data.phase,
                needsConfirmation: data.needs_confirmation || false,
                confirmationField: data.confirmation_field,
                confirmationValue: data.confirmation_value
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong in outline chat."
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineMessages, outlineSession]);

    // =========================
    // OUTLINE CHAT EDIT HANDLER
    // =========================

    const handleEditAnswer = useCallback(async (messageId, fieldName, newValue, tutorialNumber = null) => {
        if (mode !== 'outline_chat') return;

        if (!outlineSession.projectId) {
            console.error('No project ID available for editing');
            return;
        }

        setIsTyping(true);

        try {
            const requestBody = {
                field_name: fieldName,
                new_value: newValue,
            };

            if (tutorialNumber !== null) {
                requestBody.tutorial_number = tutorialNumber;
            }

            const response = await fetch(`${API_URL}/outline_chat/${outlineSession.projectId}/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || errorData.error || 'Failed to edit answer');
            }

            const data = await response.json();

            // Update session with new outline data
            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            // Update the edited message
            setOutlineMessages(prev => prev.map(msg => {
                if (msg.id === messageId) {
                    return {
                        ...msg,
                        content: newValue,
                        wasEdited: true,
                        editedAt: Date.now()
                    };
                }
                return msg;
            }));

            // Add assistant response about the update
            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: data.assistant_message || 'Answer updated successfully.',
                outlineData: data.outline_data,
                phase: data.phase,
                isDraftReady: data.is_draft_ready,
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);

        } catch (error) {
            console.error("Edit error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed to update answer: ${error.message}`
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineSession]);

    // =========================
    // EXPORT/EDIT HANDLERS
    // =========================

    const handleDownloadScriptDocx = useCallback(async (jsonScript) => {
        setIsTyping(true);
        try {
            const response = await fetch(`${API_URL}/download_script_docx`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ json_script: jsonScript }),
            });

            if (!response.ok) {
                throw new Error('Failed to download script');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'script.docx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            console.log('✅ Script downloaded');
        } catch (error) {
            console.error('Download error:', error);
            const errorMessage = {
                id: Date.now(),
                role: 'assistant',
                content: error.message || 'Failed to download script'
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleUploadEditedScript = useCallback(async (file, messageId) => {
        if (!file) return;
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_URL}/upload_edited_script`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to upload edited script');
            }

            const data = await response.json();

            setUploadMessages(prev => prev.map(msg => {
                if (msg.id === messageId) {
                    return { ...msg, jsonScript: data.json_script, wasEdited: true };
                }
                return msg;
            }));

            const confirmMessage = {
                id: Date.now(),
                role: 'assistant',
                content: `✅ Script updated! (${data.slide_count} slides). You can now generate slides with your edits.`
            };
            setUploadMessages(prev => [...prev, confirmMessage]);

        } catch (error) {
            console.error('Upload error:', error);
            const errorMessage = {
                id: Date.now(),
                role: 'assistant',
                content: error.message || 'Failed to upload edited script'
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleExportMediaWiki = useCallback(async (jsonScript) => {
        setIsTyping(true);
        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Exporting script to MediaWiki format...`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const response = await fetch(`${API_URL}/export_mediawiki`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ json_script: jsonScript }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to export to MediaWiki');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ MediaWiki export complete! You can copy the content below or download the .wiki file.`,
                mediawikiContent: data.mediawiki_content,
                mediawikiFileUrl: data.mediawiki_file_url,
                type: 'mediawiki_export'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong exporting to MediaWiki."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, []);

    const handleSaveScriptEdit = useCallback((messageId, updatedScript) => {
        setUploadMessages(prev => prev.map(msg => {
            if (msg.id === messageId) {
                return {
                    ...msg,
                    jsonScript: updatedScript,
                    wasEdited: true
                };
            }
            return msg;
        }));

        const confirmMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `✅ Script updated! (${updatedScript.slides?.length || 0} slides edited inline). You can now generate slides or export.`
        };
        setUploadMessages(prev => [...prev, confirmMessage]);
    }, []);

    // =========================
    // QUALITY HANDLER
    // =========================

    const handleQualityCheck = useCallback(async (jsonScript, messageId) => {
        setIsQualityLoading(true);
        setOpenQualityId(messageId);

        try {
            const response = await fetch(`${API_URL}/check_quality`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ json_script: jsonScript }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to run quality check');
            }

            const data = await response.json();
            setQualityReports(prev => ({ ...prev, [messageId]: data }));

            console.log('✅ Quality check complete:', data.summary);

        } catch (error) {
            console.error('Quality check error:', error);
            setQualityReports(prev => ({
                ...prev,
                [messageId]: {
                    error: error.message,
                    checks: [{ id: 'error', criteria: 'Quality check failed', ai_review: null, ai_notes: error.message }],
                    summary: { ai_passed: 0, ai_failed: 0, total: 1 }
                }
            }));
        } finally {
            setIsQualityLoading(false);
        }
    }, []);

    // =========================
    // RETURN ALL STATE & HANDLERS
    // =========================

    return {
        // State
        mode,
        setMode,
        uploadMessages,
        setUploadMessages,
        outlineMessages,
        outlineSession,
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

        // Handlers - Session
        handleClearSession,

        // Handlers - Upload
        handleSendMessage,
        handleUploadScript,
        handleScriptToWiki,

        // Handlers - Sidebar
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload,
        handleSidebarScriptUpload: handleSendMessage, // Reuse same handler as Upload Content

        // Staging (shared between Sidebar and InputArea)
        stagedFile,
        setStagedFile,
        handleConfirmStagedFile,
        handleCancelStagedFile,

        // Handlers - Generation
        handleGenerateScript,
        handleGenerateSlides,
        handleCreateSlides,
        handleApprove,

        // Handlers - Outline Chat
        handleConfirmation,
        handleSendChatText,
        handleEditAnswer,

        // Handlers - Export/Edit
        handleDownloadScriptDocx,
        handleUploadEditedScript,
        handleExportMediaWiki,
        handleSaveScriptEdit,

        // Handlers - Quality
        handleQualityCheck,
    };
}
