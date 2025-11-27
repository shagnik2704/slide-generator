import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';

import { Menu } from 'lucide-react';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const ChatArea = ({ toggleSidebar, isSidebarOpen }) => {
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! I am your AI assistant. How can I help you today?' }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSendMessage = async (text) => {
        const newUserMessage = { id: Date.now(), role: 'user', content: text };
        setMessages(prev => [...prev, newUserMessage]);
        setIsTyping(true);

        try {
            // Phase 1: Generate Script
            const response = await fetch(`${API_URL}/generate_script`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ outline: text }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate script');
            }

            const data = await response.json();

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: "I've generated a script for your presentation. Please review it below.",
                pdfUrl: data.script_pdf_url,
                jsonScript: data.json_script,
                type: 'script_review'
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

    const handleGenerateSlides = async (jsonScript) => {
        setIsTyping(true);
        try {
            // Phase 2: Generate Slides PDF
            const response = await fetch(`${API_URL}/generate_slides`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ json_script: jsonScript }),
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
                pdfPath: data.pdf_path, // Store raw path
                jsonScript: data.json_script,
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

    const handleApprove = async (jsonScript, pdfPath) => { // Accept pdfPath
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
                    pdf_path: pdfPath // Send pdf_path
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
                content: "Video generated successfully! Watch it below.",
                videoUrl: data.video_url,
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
                background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                color: 'white',
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
                            background: 'transparent',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '0.25rem',
                            borderRadius: '0.25rem',
                            transition: 'background 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        <Menu size={24} />
                    </button>
                </div>
                <div style={{
                    position: 'absolute',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    fontWeight: 600,
                    fontSize: '1.1rem'
                }}>
                    New Chat
                </div>
                <div style={{
                    padding: '0.25rem 0.75rem',
                    background: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '1rem',
                    fontSize: '0.8rem',
                    color: 'white',
                    backdropFilter: 'blur(5px)'
                }}>
                    Model: GPT-4o
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
                            {msg.type === 'script_review' && (
                                <div style={{ marginTop: '0.5rem', marginLeft: '3rem' }}>
                                    <div style={{ marginBottom: '0.5rem' }}>
                                        <a href={msg.pdfUrl} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>
                                            View Script PDF
                                        </a>
                                    </div>
                                    <button
                                        onClick={() => handleGenerateSlides(msg.jsonScript)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.5rem 1rem',
                                            background: 'var(--accent-primary)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: 'pointer',
                                            fontWeight: 600
                                        }}
                                    >
                                        Generate Slides PDF
                                    </button>
                                </div>
                            )}
                            {msg.type === 'slides_review' && (
                                <div style={{ marginTop: '0.5rem', marginLeft: '3rem' }}>
                                    <div style={{ marginBottom: '0.5rem' }}>
                                        <a href={msg.pdfUrl} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>
                                            View Slides PDF
                                        </a>
                                    </div>
                                    <button
                                        onClick={() => handleApprove(msg.jsonScript, msg.pdfPath)}
                                        disabled={isTyping}
                                        style={{
                                            padding: '0.5rem 1rem',
                                            background: 'var(--accent-secondary)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: 'pointer',
                                            fontWeight: 600
                                        }}
                                    >
                                        Approve & Generate Video
                                    </button>
                                </div>
                            )}
                            {msg.type === 'video_result' && (
                                <div style={{ marginTop: '0.5rem', marginLeft: '3rem' }}>
                                    <video controls width="100%" style={{ borderRadius: '0.5rem' }}>
                                        <source src={msg.videoUrl} type="video/mp4" />
                                        Your browser does not support the video tag.
                                    </video>
                                    <div style={{ marginTop: '0.5rem' }}>
                                        <a
                                            href={msg.videoUrl}
                                            download="presentation.mp4"
                                            style={{
                                                display: 'inline-block',
                                                padding: '0.5rem 1rem',
                                                background: 'var(--bg-tertiary)',
                                                color: 'var(--text-primary)',
                                                textDecoration: 'none',
                                                borderRadius: '0.5rem',
                                                fontSize: '0.9rem',
                                                border: '1px solid var(--border-color)'
                                            }}
                                        >
                                            Download Video
                                        </a>
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
            <InputArea onSendMessage={handleSendMessage} disabled={isTyping} />

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
