import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import ThemeToggle from './ThemeToggle';
import OutlineCard from './OutlineCard';
import WikiScriptEditor from './WikiScriptEditor';
import ComplianceReport from './ComplianceReport';

import { Menu, FileText, Video, Download, FileCode2, Copy, Check, UploadCloud, MessageSquare, Edit3, Upload, Trash2 } from 'lucide-react';

// const API_URL = 'https://slide-generator-61ic.onrender.com';
const API_URL = 'http://localhost:8000';

// LocalStorage key for persisting upload mode state
const STORAGE_KEY = 'spokentutorial_upload_state';
const MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

// Default messages
const DEFAULT_UPLOAD_MESSAGE = {
    id: 1,
    role: 'assistant',
    content: 'Hello! Please upload your tutorial content to get started. I\'ll help you generate a script, slides, and video from it.'
};

// Helper: Load state from localStorage
const loadFromLocalStorage = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const state = JSON.parse(saved);
            // Check if data is not too old
            if (Date.now() - state.savedAt < MAX_AGE_MS) {
                return state;
            }
            // Data expired, clear it
            localStorage.removeItem(STORAGE_KEY);
        }
    } catch (e) {
        console.error('Error loading from localStorage:', e);
    }
    return null;
};

// Helper: Save state to localStorage
const saveToLocalStorage = (uploadMessages, currentProjectId) => {
    try {
        const state = {
            uploadMessages,
            currentProjectId,
            savedAt: Date.now()
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
};

const ChatArea = ({ toggleSidebar }) => {
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

    const [outlineMessages, setOutlineMessages] = useState([
        {
            id: 2,
            role: 'assistant',
            content: 'Hi! 😊 I\'m here to help you create a Spoken Tutorial course outline, step by step.\n\nTo start, could you tell me what kind of course this is: **FOSS**, **ICT**, or **Other**?\n\nJust reply with `FOSS`, `ICT`, or `Other` (you can add a short note if you pick Other). Then I\'ll gently walk you through a few short questions.',
        }
    ]);
    const [outlineSession, setOutlineSession] = useState({ projectId: null, outlineData: null, phase: null });
    const [isTyping, setIsTyping] = useState(false);

    // Initialize currentProjectId from localStorage or null
    const [currentProjectId, setCurrentProjectId] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.currentProjectId || null;
    });

    const [copiedId, setCopiedId] = useState(null);
    const messagesEndRef = useRef(null);
    const editedScriptInputRef = useRef(null);
    const [openEditorId, setOpenEditorId] = useState(null);
    const [complianceReport, setComplianceReport] = useState(null);

    // Flag to track if we restored from localStorage
    const [sessionRestored, setSessionRestored] = useState(() => {
        const saved = loadFromLocalStorage();
        return saved?.uploadMessages?.length > 1; // More than just the welcome message
    });

    const activeMessages = mode === 'outline_chat' ? outlineMessages : uploadMessages;

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [activeMessages, isTyping, mode]);

    // Auto-save upload mode state to localStorage
    useEffect(() => {
        if (mode === 'upload' && uploadMessages.length > 0) {
            saveToLocalStorage(uploadMessages, currentProjectId);
        }
    }, [uploadMessages, currentProjectId, mode]);

    // Clear session and start fresh
    const handleClearSession = () => {
        if (window.confirm('Clear all upload data and start fresh? This cannot be undone.')) {
            localStorage.removeItem(STORAGE_KEY);
            setUploadMessages([DEFAULT_UPLOAD_MESSAGE]);
            setCurrentProjectId(null);
            setOpenEditorId(null);
            setSessionRestored(false);
            console.log('🗑️ Session cleared');
        }
    };

    const handleSendMessage = async (file) => {
        // Show upload status
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

            // Generate a simple project ID
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
    };

    const handleUploadScript = async (file) => {
        // Show upload status
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

            // Show compliance report if returned
            if (data.compliance_report) {
                setComplianceReport(data.compliance_report);
            }

            const violationCount = data.compliance_report?.total_violations || 0;
            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Script uploaded successfully! (${data.json_script.slides?.length || 0} slides)${violationCount > 0 ? `\n\n⚠️ ${violationCount} compliance issue${violationCount !== 1 ? 's' : ''} found. Check the report for details.` : ' All compliance checks passed!'} You can now generate slides directly.`,
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
    };

    const handleGenerateScript = async (outline, projectId) => {
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
                headers: {
                    'Content-Type': 'application/json',
                },
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
    };



    const handleGenerateSlides = async (jsonScript, projectId) => {
        console.log("🚀 handleGenerateSlides called with:", { jsonScript, projectId });
        setIsTyping(true);
        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Generating slides... (This might take a moment)`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            // Phase 2: Generate Slides PDF
            const response = await fetch(`${API_URL}/generate_slides`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
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
    };

    const handleApprove = async (jsonScript, pdfPath, projectId) => {
        setIsTyping(true);
        try {
            // Phase 3: Generate Video
            const response = await fetch(`${API_URL}/generate_video`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
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
    };

    const handleConfirmation = async (confirmed) => {
        if (mode !== 'outline_chat') return;
        const confirmationText = confirmed ? 'yes' : 'no';
        await handleSendChatText(confirmationText);
    };

    const handleSendChatText = async (text) => {
        if (mode !== 'outline_chat') return;
        const userMessage = { id: Date.now(), role: 'user', content: text };
        const conversationForApi = [...outlineMessages, userMessage].map(({ role, content }) => ({ role, content }));
        setOutlineMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const response = await fetch(`${API_URL}/outline_chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
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

            // Update session state
            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            // Build assistant message
            let assistantContent = data.assistant_message || 'Here is the updated outline.';

            // Add validation errors if any
            if (data.validation_errors && data.validation_errors.length > 0) {
                assistantContent += '\n\n⚠️ Issues to address:\n' + data.validation_errors.map(e => `- ${e}`).join('\n');
            }

            // Add pedagogy compliance badge if draft is ready
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


            // Add assistant message (already includes draft if ready)
            setOutlineMessages(prev => [...prev, assistantMessage]);

            // If approved, show export option
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
    };

    // Download script as editable .docx
    const handleDownloadScriptDocx = async (jsonScript) => {
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

            // Get the file and trigger download
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
    };

    // Upload edited script .docx and update the message
    const handleUploadEditedScript = async (file, messageId) => {
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

            // Update the message with edited script
            setUploadMessages(prev => prev.map(msg => {
                if (msg.id === messageId) {
                    return { ...msg, jsonScript: data.json_script, wasEdited: true };
                }
                return msg;
            }));

            // Add confirmation message
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
    };

    const handleExportMediaWiki = async (jsonScript) => {
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
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    json_script: jsonScript
                }),
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
    };

    // Handle saving edits from the WikiScriptEditor
    const handleSaveScriptEdit = (messageId, updatedScript) => {
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

        // Show confirmation
        const confirmMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `✅ Script updated! (${updatedScript.slides?.length || 0} slides edited inline). You can now generate slides or export.`
        };
        setUploadMessages(prev => [...prev, confirmMessage]);
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
                    {/* Clear Session button - only show in upload mode with existing session */}
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
                    <div style={{
                        padding: '0.25rem 0.75rem',
                        background: 'var(--accent-primary)',
                        borderRadius: '1rem',
                        fontSize: '0.8rem',
                        color: 'white',
                        fontWeight: 500,
                        boxShadow: 'var(--shadow-sm)',
                    }}>
                        Model: Gemini 2.5 Flash
                    </div>
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

                            {/* Show OutlineCard when outline data is ready for review */}
                            {mode === 'outline_chat' && msg.outlineData && msg.phase === 'review' && (
                                <OutlineCard
                                    outlineData={msg.outlineData}
                                    projectId={outlineSession.projectId || msg.outlineData?.project_id}
                                />
                            )}

                            {mode === 'upload' && msg.type === 'outline_uploaded' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    <button
                                        onClick={() => handleGenerateScript(msg.outline, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'var(--accent-primary)',
                                            color: isTyping ? 'var(--text-secondary)' : 'white',
                                            border: 'none',
                                            borderRadius: '0.75rem',
                                            cursor: isTyping ? 'not-allowed' : 'pointer',
                                            fontWeight: 600,
                                            fontSize: '1rem',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            transition: 'all 0.3s ease',
                                            boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                                            opacity: isTyping ? 0.6 : 1,
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                    >
                                        <FileText size={20} />
                                        Generate Script from Edited Content
                                    </button>
                                </div>
                            )}
                            {mode === 'upload' && msg.type === 'script_uploaded' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    <button
                                        onClick={() => handleGenerateSlides(msg.jsonScript, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'var(--accent-primary)',
                                            color: isTyping ? 'var(--text-secondary)' : 'white',
                                            border: 'none',
                                            borderRadius: '0.75rem',
                                            cursor: isTyping ? 'not-allowed' : 'pointer',
                                            fontWeight: 600,
                                            fontSize: '1rem',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            transition: 'all 0.3s ease',
                                            boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                                            opacity: isTyping ? 0.6 : 1,
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                    >
                                        <FileText size={20} />
                                        Generate Slides from Script
                                    </button>
                                </div>
                            )}
                            {mode === 'upload' && msg.type === 'script_review' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    <div style={{ marginBottom: '1rem' }}>
                                        <a
                                            href={`${API_URL}${msg.pdfUrl}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                color: 'var(--accent-primary)',
                                                textDecoration: 'none',
                                                fontWeight: 500,
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                transition: 'all 0.2s ease',
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                                            onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                                        >
                                            <FileText size={18} />
                                            View Script PDF
                                        </a>
                                        {msg.wasEdited && (
                                            <span style={{
                                                marginLeft: '0.75rem',
                                                color: '#059669',
                                                fontSize: '0.85rem',
                                                fontWeight: 500
                                            }}>
                                                ✓ Edited
                                            </span>
                                        )}
                                    </div>
                                    {/* Edit Script Section */}
                                    <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                                        <button
                                            onClick={() => handleDownloadScriptDocx(msg.jsonScript)}
                                            disabled={isTyping}
                                            style={{
                                                padding: '0.6rem 1rem',
                                                background: isTyping ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                                                color: 'var(--text-primary)',
                                                border: '1px solid var(--border-color)',
                                                borderRadius: '0.75rem',
                                                cursor: isTyping ? 'not-allowed' : 'pointer',
                                                fontWeight: 500,
                                                fontSize: '0.9rem',
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                transition: 'all 0.3s ease',
                                                opacity: isTyping ? 0.6 : 1,
                                            }}
                                            onMouseEnter={(e) => {
                                                if (!isTyping) {
                                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (!isTyping) {
                                                    e.currentTarget.style.background = 'var(--bg-secondary)';
                                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                                }
                                            }}
                                        >
                                            <Download size={18} />
                                            Download Script (.docx)
                                        </button>
                                        <input
                                            type="file"
                                            accept=".docx"
                                            style={{ display: 'none' }}
                                            ref={editedScriptInputRef}
                                            onChange={(e) => {
                                                const file = e.target.files[0];
                                                if (file) {
                                                    handleUploadEditedScript(file, msg.id);
                                                    e.target.value = '';
                                                }
                                            }}
                                        />
                                        <button
                                            onClick={() => editedScriptInputRef.current?.click()}
                                            disabled={isTyping}
                                            style={{
                                                padding: '0.6rem 1rem',
                                                background: isTyping ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                                                color: 'var(--text-primary)',
                                                border: '1px solid var(--border-color)',
                                                borderRadius: '0.75rem',
                                                cursor: isTyping ? 'not-allowed' : 'pointer',
                                                fontWeight: 500,
                                                fontSize: '0.9rem',
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                transition: 'all 0.3s ease',
                                                opacity: isTyping ? 0.6 : 1,
                                            }}
                                            onMouseEnter={(e) => {
                                                if (!isTyping) {
                                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (!isTyping) {
                                                    e.currentTarget.style.background = 'var(--bg-secondary)';
                                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                                }
                                            }}
                                        >
                                            <Upload size={18} />
                                            Upload Edited Script
                                        </button>
                                    </div>
                                    <button
                                        onClick={() => handleGenerateSlides(msg.jsonScript, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'var(--accent-primary)',
                                            color: isTyping ? 'var(--text-secondary)' : 'white',
                                            border: 'none',
                                            borderRadius: '0.75rem',
                                            cursor: isTyping ? 'not-allowed' : 'pointer',
                                            fontWeight: 600,
                                            fontSize: '1rem',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            transition: 'all 0.3s ease',
                                            boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                                            opacity: isTyping ? 0.6 : 1,
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                    >
                                        <FileText size={20} />
                                        Generate Slides PDF
                                    </button>
                                    <button
                                        onClick={() => handleExportMediaWiki(msg.jsonScript)}
                                        disabled={isTyping}
                                        style={{
                                            marginLeft: '0.75rem',
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'linear-gradient(135deg, #059669, #10b981)',
                                            color: isTyping ? 'var(--text-secondary)' : 'white',
                                            border: 'none',
                                            borderRadius: '0.75rem',
                                            cursor: isTyping ? 'not-allowed' : 'pointer',
                                            fontWeight: 600,
                                            fontSize: '1rem',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            transition: 'all 0.3s ease',
                                            boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                                            opacity: isTyping ? 0.6 : 1,
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                    >
                                        <FileCode2 size={20} />
                                        Export to MediaWiki
                                    </button>
                                    <button
                                        onClick={() => setOpenEditorId(openEditorId === msg.id ? null : msg.id)}
                                        style={{
                                            marginLeft: '0.75rem',
                                            padding: '0.75rem 1.5rem',
                                            background: openEditorId === msg.id
                                                ? 'linear-gradient(135deg, #7c3aed, #a855f7)'
                                                : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
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
                                            e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                        }}
                                    >
                                        <Edit3 size={20} />
                                        {openEditorId === msg.id ? 'Close Editor' : 'Edit Script Inline'}
                                    </button>

                                    {/* Wiki-style Script Editor */}
                                    <WikiScriptEditor
                                        jsonScript={msg.jsonScript}
                                        isOpen={openEditorId === msg.id}
                                        onSave={(updatedScript) => handleSaveScriptEdit(msg.id, updatedScript)}
                                        onClose={() => setOpenEditorId(null)}
                                    />
                                </div>
                            )}
                            {mode === 'upload' && msg.type === 'slides_review' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    <div style={{ marginBottom: '1rem' }}>
                                        <a
                                            href={msg.pdfUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                color: 'var(--accent-primary)',
                                                textDecoration: 'none',
                                                fontWeight: 500,
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                transition: 'all 0.2s ease',
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                                            onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                                        >
                                            <FileText size={18} />
                                            View Slides PDF
                                        </a>
                                    </div>
                                    <button
                                        onClick={() => handleApprove(msg.jsonScript, msg.pdfPath, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'var(--accent-primary)',
                                            color: isTyping ? 'var(--text-secondary)' : 'white',
                                            border: 'none',
                                            borderRadius: '0.75rem',
                                            cursor: isTyping ? 'not-allowed' : 'pointer',
                                            fontWeight: 600,
                                            fontSize: '1rem',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            transition: 'all 0.3s ease',
                                            boxShadow: isTyping ? 'none' : 'var(--shadow-md)',
                                            opacity: isTyping ? 0.6 : 1,
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isTyping) {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                    >
                                        <Video size={20} />
                                        Approve & Generate Video
                                    </button>
                                </div>
                            )}
                            {mode === 'upload' && msg.type === 'video_result' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    <video controls width="100%" style={{
                                        borderRadius: '0.75rem',
                                        boxShadow: 'var(--shadow-lg)',
                                        marginBottom: '1rem'
                                    }}>
                                        <source src={msg.videoUrl} type="video/mp4" />
                                        Your browser does not support the video tag.
                                    </video>
                                    <a
                                        href={msg.videoUrl}
                                        download="presentation.mp4"
                                        style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.75rem 1.5rem',
                                            background: 'var(--accent-primary)',
                                            color: 'white',
                                            textDecoration: 'none',
                                            borderRadius: '0.75rem',
                                            fontSize: '1rem',
                                            fontWeight: 600,
                                            border: 'none',
                                            boxShadow: 'var(--shadow-md)',
                                            transition: 'all 0.3s ease',
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                        }}
                                    >
                                        <Download size={20} />
                                        Download Video
                                    </a>
                                </div>
                            )}
                            {msg.type === 'mediawiki_export' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem', marginBottom: '1.5rem' }}>
                                    {/* MediaWiki content preview */}
                                    <div style={{
                                        background: 'var(--bg-tertiary)',
                                        borderRadius: '0.75rem',
                                        padding: '1rem',
                                        marginBottom: '1rem',
                                        maxHeight: '300px',
                                        overflowY: 'auto',
                                        border: '1px solid var(--border-color)'
                                    }}>
                                        <pre style={{
                                            margin: 0,
                                            fontFamily: 'monospace',
                                            fontSize: '0.85rem',
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word',
                                            color: 'var(--text-primary)'
                                        }}>
                                            {msg.mediawikiContent}
                                        </pre>
                                    </div>
                                    {/* Action buttons */}
                                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                                        <button
                                            onClick={() => {
                                                navigator.clipboard.writeText(msg.mediawikiContent);
                                                setCopiedId(msg.id);
                                                setTimeout(() => setCopiedId(null), 2000);
                                            }}
                                            style={{
                                                padding: '0.75rem 1.5rem',
                                                background: copiedId === msg.id
                                                    ? 'linear-gradient(135deg, #059669, #10b981)'
                                                    : 'var(--bg-tertiary)',
                                                color: copiedId === msg.id ? 'white' : 'var(--text-primary)',
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
                                                if (copiedId !== msg.id) {
                                                    e.currentTarget.style.background = 'var(--bg-secondary)';
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (copiedId !== msg.id) {
                                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                                }
                                            }}
                                        >
                                            {copiedId === msg.id ? <Check size={20} /> : <Copy size={20} />}
                                            {copiedId === msg.id ? 'Copied!' : 'Copy to Clipboard'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                // Create a blob and download to avoid navigation
                                                const blob = new Blob([msg.mediawikiContent], { type: 'text/plain' });
                                                const url = URL.createObjectURL(blob);
                                                const a = document.createElement('a');
                                                a.href = url;
                                                a.download = 'script.wiki';
                                                document.body.appendChild(a);
                                                a.click();
                                                document.body.removeChild(a);
                                                URL.revokeObjectURL(url);
                                            }}
                                            style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                padding: '0.75rem 1.5rem',
                                                background: 'linear-gradient(135deg, #059669, #10b981)',
                                                color: 'white',
                                                textDecoration: 'none',
                                                borderRadius: '0.75rem',
                                                fontSize: '1rem',
                                                fontWeight: 600,
                                                border: 'none',
                                                boxShadow: 'var(--shadow-md)',
                                                transition: 'all 0.3s ease',
                                                cursor: 'pointer',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }}
                                        >
                                            <Download size={20} />
                                            Download .wiki File
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

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

            {/* Compliance Report Modal */}
            {complianceReport && (
                <ComplianceReport
                    report={complianceReport}
                    onClose={() => setComplianceReport(null)}
                />
            )}
        </main>
    );
};

export default ChatArea;
