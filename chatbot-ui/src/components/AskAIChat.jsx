import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Minimize2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const AskAIChat = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        if (isOpen && !isMinimized) {
            scrollToBottom();
            // Focus input when opened
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [messages, isOpen, isMinimized]);

    const handleSend = async () => {
        const question = inputValue.trim();
        if (!question || isLoading) return;

        // Add user message
        const userMessage = { role: 'user', content: question, id: Date.now() };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        try {
            const response = await fetch(`${API_URL}/general_chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
            });

            if (!response.ok) {
                throw new Error('Failed to get answer');
            }

            const data = await response.json();
            const assistantMessage = {
                role: 'assistant',
                content: data.answer || 'Sorry, I could not generate an answer.',
                id: Date.now() + 1,
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                id: Date.now() + 1,
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleToggle = () => {
        if (isOpen) {
            if (isMinimized) {
                setIsMinimized(false);
            } else {
                setIsMinimized(true);
            }
        } else {
            setIsOpen(true);
            setIsMinimized(false);
        }
    };

    const handleClose = () => {
        setIsOpen(false);
        setIsMinimized(false);
    };

    return (
        <>
            {/* Floating Button */}
            {!isOpen && (
                <button
                    onClick={handleToggle}
                    style={{
                        position: 'fixed',
                        bottom: '2rem',
                        right: '2rem',
                        width: '56px',
                        height: '56px',
                        borderRadius: '50%',
                        background: 'var(--accent-primary)',
                        color: 'white',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: 'var(--shadow-lg)',
                        zIndex: 1000,
                        transition: 'all 0.3s ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.1)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-glow)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'scale(1)';
                        e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
                    }}
                    title="Ask AI"
                >
                    <MessageCircle size={24} />
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: isMinimized ? '2rem' : '2rem',
                        right: '2rem',
                        width: isMinimized ? '320px' : '400px',
                        height: isMinimized ? '60px' : '600px',
                        maxHeight: '80vh',
                        background: 'var(--bg-secondary)',
                        borderRadius: '1rem',
                        border: '1px solid var(--border-color)',
                        boxShadow: 'var(--shadow-lg)',
                        display: 'flex',
                        flexDirection: 'column',
                        zIndex: 1000,
                        transition: 'all 0.3s ease',
                        overflow: 'hidden',
                    }}
                >
                    {/* Header */}
                    <div
                        style={{
                            padding: '1rem',
                            borderBottom: '1px solid var(--border-color)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: 'var(--bg-primary)',
                            cursor: isMinimized ? 'pointer' : 'default',
                        }}
                        onClick={isMinimized ? handleToggle : undefined}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <MessageCircle size={20} color="var(--accent-primary)" />
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                Ask AI
                            </span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            {!isMinimized && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setIsMinimized(true);
                                    }}
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: 'var(--text-secondary)',
                                        cursor: 'pointer',
                                        padding: '0.25rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        borderRadius: '0.25rem',
                                        transition: 'all 0.2s ease',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.background = 'var(--bg-tertiary)';
                                        e.currentTarget.style.color = 'var(--text-primary)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = 'transparent';
                                        e.currentTarget.style.color = 'var(--text-secondary)';
                                    }}
                                    title="Minimize"
                                >
                                    <Minimize2 size={16} />
                                </button>
                            )}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleClose();
                                }}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    padding: '0.25rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    borderRadius: '0.25rem',
                                    transition: 'all 0.2s ease',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    e.currentTarget.style.color = 'var(--text-primary)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'transparent';
                                    e.currentTarget.style.color = 'var(--text-secondary)';
                                }}
                                title="Close"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    </div>

                    {/* Messages Area */}
                    {!isMinimized && (
                        <>
                            <div
                                style={{
                                    flex: 1,
                                    overflowY: 'auto',
                                    padding: '1rem',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '1rem',
                                }}
                            >
                                {messages.length === 0 ? (
                                    <div
                                        style={{
                                            textAlign: 'center',
                                            color: 'var(--text-secondary)',
                                            fontSize: '0.9rem',
                                            padding: '2rem 1rem',
                                        }}
                                    >
                                        Ask me anything! I'm here to help.
                                    </div>
                                ) : (
                                    messages.map((msg) => (
                                        <div
                                            key={msg.id}
                                            style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.25rem',
                                                alignItems:
                                                    msg.role === 'user' ? 'flex-end' : 'flex-start',
                                            }}
                                        >
                                            <div
                                                style={{
                                                    maxWidth: '85%',
                                                    padding: '0.75rem 1rem',
                                                    borderRadius: '0.75rem',
                                                    background:
                                                        msg.role === 'user'
                                                            ? 'var(--accent-primary)'
                                                            : 'var(--bg-tertiary)',
                                                    color:
                                                        msg.role === 'user'
                                                            ? 'white'
                                                            : 'var(--text-primary)',
                                                    fontSize: '0.9rem',
                                                    lineHeight: 1.5,
                                                    wordWrap: 'break-word',
                                                }}
                                            >
                                                {msg.content}
                                            </div>
                                        </div>
                                    ))
                                )}
                                {isLoading && (
                                    <div
                                        style={{
                                            display: 'flex',
                                            gap: '0.5rem',
                                            alignItems: 'flex-start',
                                        }}
                                    >
                                        <div
                                            style={{
                                                padding: '0.75rem 1rem',
                                                borderRadius: '0.75rem',
                                                background: 'var(--bg-tertiary)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.9rem',
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: 'flex',
                                                    gap: '0.25rem',
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        width: '6px',
                                                        height: '6px',
                                                        borderRadius: '50%',
                                                        background: 'var(--text-secondary)',
                                                        animation: 'bounce 1.4s infinite ease-in-out both',
                                                    }}
                                                />
                                                <span
                                                    style={{
                                                        width: '6px',
                                                        height: '6px',
                                                        borderRadius: '50%',
                                                        background: 'var(--text-secondary)',
                                                        animation: 'bounce 1.4s infinite ease-in-out both 0.16s',
                                                    }}
                                                />
                                                <span
                                                    style={{
                                                        width: '6px',
                                                        height: '6px',
                                                        borderRadius: '50%',
                                                        background: 'var(--text-secondary)',
                                                        animation: 'bounce 1.4s infinite ease-in-out both 0.32s',
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input Area */}
                            <div
                                style={{
                                    padding: '1rem',
                                    borderTop: '1px solid var(--border-color)',
                                    background: 'var(--bg-primary)',
                                }}
                            >
                                <div
                                    style={{
                                        display: 'flex',
                                        gap: '0.5rem',
                                        alignItems: 'flex-end',
                                    }}
                                >
                                    <textarea
                                        ref={inputRef}
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Ask a question..."
                                        disabled={isLoading}
                                        style={{
                                            flex: 1,
                                            minHeight: '40px',
                                            maxHeight: '120px',
                                            padding: '0.75rem',
                                            borderRadius: '0.75rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.9rem',
                                            resize: 'none',
                                            fontFamily: 'inherit',
                                            outline: 'none',
                                        }}
                                        onInput={(e) => {
                                            e.target.style.height = 'auto';
                                            e.target.style.height = `${e.target.scrollHeight}px`;
                                        }}
                                    />
                                    <button
                                        onClick={handleSend}
                                        disabled={!inputValue.trim() || isLoading}
                                        style={{
                                            padding: '0.75rem',
                                            borderRadius: '0.75rem',
                                            border: 'none',
                                            background:
                                                !inputValue.trim() || isLoading
                                                    ? 'var(--bg-tertiary)'
                                                    : 'var(--accent-primary)',
                                            color:
                                                !inputValue.trim() || isLoading
                                                    ? 'var(--text-secondary)'
                                                    : 'white',
                                            cursor:
                                                !inputValue.trim() || isLoading
                                                    ? 'not-allowed'
                                                    : 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            transition: 'all 0.2s ease',
                                            boxShadow: 'var(--shadow-sm)',
                                        }}
                                        onMouseEnter={(e) => {
                                            if (inputValue.trim() && !isLoading) {
                                                e.currentTarget.style.transform = 'scale(1.05)';
                                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'scale(1)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                        }}
                                    >
                                        <Send size={18} />
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}

            <style>{`
                @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
            `}</style>
        </>
    );
};

export default AskAIChat;
