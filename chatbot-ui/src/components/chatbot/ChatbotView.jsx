import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, Sparkles, Edit3, Trash2, HelpCircle, CheckCircle2, MessageSquareQuote } from 'lucide-react';
import { apiJson } from '../../services/api';
import { ChatbotMessage } from './ChatbotMessage';
import { ChatbotComposer } from './ChatbotComposer';
import { ChangeContentModal } from './ChangeContentModal';
import { fetchVoiceStatus } from './voice';

const STARTER_QUESTIONS = [
    'How many students can I upload in one Master Batch?',
    'Can organiser and invigilator be the same person?',
    'What is the minimum score required for a certificate?',
    'How do I request an online test?',
    'Which browser is recommended for workshop activities?',
    'What if email ID is already used?',
];

export default function ChatbotView() {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [voiceEnabled, setVoiceEnabled] = useState(false);
    const [isChangeContentOpen, setIsChangeContentOpen] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        fetchVoiceStatus().then((status) => {
            setVoiceEnabled(status.enabled);
        });
    }, []);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, scrollToBottom]);

    const handleSend = async (questionText) => {
        const text = questionText.trim();
        if (!text || isLoading) return;

        const userMsg = {
            id: String(Date.now()),
            role: 'user',
            content: text,
        };

        const loadingMsg = {
            id: String(Date.now() + 1),
            role: 'bot',
            content: '',
            loading: true,
        };

        // Prepare conversation history for grounding
        const historyForApi = messages
            .filter((m) => !m.loading && !m.error)
            .slice(-10)
            .map((m) => ({
                role: m.role === 'user' ? 'user' : 'assistant',
                content: m.content,
            }));

        setMessages((prev) => [...prev, userMsg, loadingMsg]);
        setIsLoading(true);

        try {
            const data = await apiJson('/faq/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message: text,
                    history: historyForApi,
                }),
            });

            setMessages((prev) => {
                const filtered = prev.filter((m) => m.id !== loadingMsg.id);
                return [
                    ...filtered,
                    {
                        id: String(Date.now() + 2),
                        role: 'assistant',
                        content: data.answer,
                        confidence: data.confidence,
                        category: data.category,
                        sources: data.sources || [],
                    },
                ];
            });
        } catch (err) {
            console.error('FAQ Chat error:', err);
            const errorMessage = err?.message || 'Sorry, I encountered an error connecting to the FAQ assistant. Please try again.';
            setMessages((prev) => {
                const filtered = prev.filter((m) => m.id !== loadingMsg.id);
                return [
                    ...filtered,
                    {
                        id: String(Date.now() + 2),
                        role: 'assistant',
                        content: errorMessage,
                        error: true,
                    },
                ];
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleClearChat = () => {
        if (messages.length > 0 && window.confirm('Clear the current FAQ conversation?')) {
            setMessages([]);
        }
    };

    return (
        <div
            style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                position: 'relative',
                background: 'var(--bg-primary)',
            }}
        >
            {/* Header */}
            <div
                style={{
                    padding: '0.85rem 1.5rem',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'var(--bg-secondary)',
                    zIndex: 10,
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div
                        style={{
                            width: '38px',
                            height: '38px',
                            borderRadius: '10px',
                            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.2) 100%)',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--accent-primary, #6366f1)',
                        }}
                    >
                        <Bot size={22} />
                    </div>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <h2 style={{ fontSize: '1.05rem', fontWeight: '600', margin: 0, color: 'var(--text-primary)' }}>
                                Spoken Tutorial FAQ Chatbot
                            </h2>
                            <span
                                style={{
                                    fontSize: '0.7rem',
                                    padding: '2px 7px',
                                    borderRadius: '999px',
                                    background: 'rgba(34, 197, 94, 0.12)',
                                    color: '#22c55e',
                                    fontWeight: '500',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                }}
                            >
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e' }} />
                                Online
                            </span>
                        </div>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                            Official guidance for organisers, invigilators, and students
                        </p>
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {/* Change Content Button */}
                    <button
                        onClick={() => setIsChangeContentOpen(true)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.45rem 0.85rem',
                            borderRadius: '0.5rem',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'var(--accent-primary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                        }}
                    >
                        <Edit3 size={14} style={{ color: 'var(--accent-primary)' }} />
                        <span>Change Content</span>
                    </button>

                    {/* Clear Chat Button */}
                    {messages.length > 0 && (
                        <button
                            onClick={handleClearChat}
                            title="Clear conversation"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '34px',
                                height: '34px',
                                borderRadius: '0.5rem',
                                border: '1px solid var(--border-color)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                cursor: 'pointer',
                            }}
                        >
                            <Trash2 size={16} />
                        </button>
                    )}
                </div>
            </div>

            {/* Main Chat Scroll Area */}
            <div
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                <div style={{ maxWidth: '820px', width: '100%', margin: '0 auto', flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {messages.length === 0 ? (
                        <div
                            style={{
                                flex: 1,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                textAlign: 'center',
                                padding: '2rem 1rem',
                                gap: '1.5rem',
                            }}
                        >
                            <div
                                style={{
                                    width: '64px',
                                    height: '64px',
                                    borderRadius: '16px',
                                    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%)',
                                    border: '1px solid rgba(99, 102, 241, 0.25)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--accent-primary)',
                                    boxShadow: '0 8px 24px rgba(99, 102, 241, 0.12)',
                                }}
                            >
                                <Bot size={36} />
                            </div>

                            <div style={{ maxWidth: '520px' }}>
                                <h3 style={{ fontSize: '1.35rem', fontWeight: '600', color: 'var(--text-primary)', margin: '0 0 0.5rem 0' }}>
                                    How can I help you today?
                                </h3>
                                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
                                    Ask any question about Master Batch creation, student limits, online test approvals, invigilators, or certificates. Answers are strictly grounded in official guidelines.
                                </p>
                            </div>

                            {/* Starter Question Chips */}
                            <div style={{ width: '100%', maxWidth: '680px', marginTop: '0.5rem' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                                    Popular Questions
                                </div>
                                <div
                                    style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                        gap: '0.65rem',
                                    }}
                                >
                                    {STARTER_QUESTIONS.map((q, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => handleSend(q)}
                                            style={{
                                                padding: '0.85rem 1rem',
                                                borderRadius: '0.75rem',
                                                border: '1px solid var(--border-color)',
                                                background: 'var(--bg-secondary)',
                                                color: 'var(--text-primary)',
                                                fontSize: '0.85rem',
                                                textAlign: 'left',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.65rem',
                                                transition: 'all 0.15s ease',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                                                e.currentTarget.style.transform = 'translateY(-2px)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.borderColor = 'var(--border-color)';
                                                e.currentTarget.style.transform = 'translateY(0)';
                                            }}
                                        >
                                            <MessageSquareQuote size={16} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                                            <span>{q}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                            {messages.map((msg) => (
                                <ChatbotMessage
                                    key={msg.id}
                                    message={msg}
                                    voiceEnabled={voiceEnabled}
                                />
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>
            </div>

            {/* Composer Footer */}
            <div
                style={{
                    paddingTop: '0.5rem',
                    paddingBottom: '0.5rem',
                    background: 'var(--bg-primary)',
                    borderTop: '1px solid var(--border-color)',
                }}
            >
                <ChatbotComposer
                    onSend={handleSend}
                    disabled={isLoading}
                    voiceEnabled={voiceEnabled}
                />
            </div>

            {/* Change Content Admin Modal */}
            <ChangeContentModal
                isOpen={isChangeContentOpen}
                onClose={() => setIsChangeContentOpen(false)}
            />
        </div>
    );
}
