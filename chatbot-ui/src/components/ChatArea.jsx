import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import ThemeToggle from './ThemeToggle';

import { Menu, FileText, Video, Download, FileCode2, Copy, Check } from 'lucide-react';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const ChatArea = ({ toggleSidebar, isSidebarOpen }) => {
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! Please upload your presentation outline to get started. I\'ll help you generate a script, slides, and video from it.' }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const [currentProjectId, setCurrentProjectId] = useState(null);
    const [copiedId, setCopiedId] = useState(null);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSendMessage = async (file) => {
        // Show upload status
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Uploading outline: ${file.name}...`
        };
        setMessages(prev => [...prev, uploadMessage]);
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
                throw new Error(errorData.detail || 'Failed to upload outline');
            }

            const data = await response.json();

            // Generate a simple project ID
            const projectId = Date.now();
            setCurrentProjectId(projectId);

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Outline uploaded successfully!\n\nYou can now generate the script.`,
                outline: data.outline,
                projectId: projectId,
                type: 'outline_uploaded'
            };
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong."
            };
            setMessages(prev => [...prev, errorMessage]);
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
        setMessages(prev => [...prev, uploadMessage]);
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

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Script uploaded successfully! (${data.json_script.slides?.length || 0} slides) You can now generate slides directly.`,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_uploaded'
            };
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong uploading the script."
            };
            setMessages(prev => [...prev, errorMessage]);
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
        setMessages(prev => [...prev, statusMessage]);

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
                content: `I've generated a script for your presentation. Please review it below.`,
                pdfUrl: data.script_pdf_url,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_review'
            };
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating script."
            };
            setMessages(prev => [...prev, errorMessage]);
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
        setMessages(prev => [...prev, statusMessage]);

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
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating slides."
            };
            setMessages(prev => [...prev, errorMessage]);
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
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating the video."
            };
            setMessages(prev => [...prev, errorMessage]);
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
        setMessages(prev => [...prev, statusMessage]);

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
            setMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong exporting to MediaWiki."
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
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
                    <div style={{
                        fontWeight: 600,
                        fontSize: '1.25rem',
                        fontFamily: '"Google Sans", "Outfit", sans-serif',
                        background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        Spoken Tutorial Generator
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{
                        padding: '0.25rem 0.75rem',
                        background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                        borderRadius: '1rem',
                        fontSize: '0.8rem',
                        color: 'var(--bg-primary)',
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
                    {messages.map((msg) => (
                        <div key={msg.id}>
                            <MessageBubble message={msg} />

                            {msg.type === 'outline_uploaded' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
                                    <button
                                        onClick={() => handleGenerateScript(msg.outline, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                                        Generate Script from Edited Outline
                                    </button>
                                </div>
                            )}
                            {msg.type === 'script_uploaded' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
                                    <button
                                        onClick={() => handleGenerateSlides(msg.jsonScript, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                            {msg.type === 'script_review' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
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
                                    </div>
                                    <button
                                        onClick={() => handleGenerateSlides(msg.jsonScript, msg.projectId)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.75rem 1.5rem',
                                            background: isTyping
                                                ? 'var(--bg-tertiary)'
                                                : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                                </div>
                            )}
                            {msg.type === 'slides_review' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
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
                                                : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                            {msg.type === 'video_result' && (
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
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
                                            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
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
                                <div style={{ marginTop: '1rem', marginLeft: '3rem' }}>
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
            <InputArea onSendMessage={handleSendMessage} onUploadScript={handleUploadScript} disabled={isTyping} />

            <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
      `}</style>
        </main>
    );
};

export default ChatArea;
