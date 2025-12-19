import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, Check, X } from 'lucide-react';

const MessageBubble = ({ message, onConfirmation }) => {
    const isUser = message.role === 'user';
    const needsConfirmation = message.needsConfirmation && !isUser;

    return (
        <div style={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            marginBottom: '1.5rem',
            padding: '0 1rem',
            animation: 'fadeIn 0.3s ease-out'
        }}>
            <div style={{
                display: 'flex',
                flexDirection: isUser ? 'row-reverse' : 'row',
                maxWidth: '80%',
                gap: '0.75rem'
            }}>
                {/* Avatar */}
                <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    backgroundColor: isUser ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: 'var(--shadow-sm)'
                }}>
                    {isUser ? <User size={20} color="white" /> : <Bot size={20} color="var(--accent-secondary)" />}
                </div>

                {/* Message Content */}
                <div style={{
                    backgroundColor: isUser ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                    color: isUser ? 'var(--bg-primary)' : 'var(--text-primary)',
                    padding: '0.75rem 1.25rem',
                    borderRadius: isUser ? '1.25rem 1.25rem 0.25rem 1.25rem' : '1.25rem 1.25rem 1.25rem 0.25rem',
                    boxShadow: 'var(--shadow-md)',
                    lineHeight: 1.6,
                    fontSize: '0.95rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: needsConfirmation ? '0.75rem' : '0'
                }}>
                    <div className="markdown-content">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                    
                    {/* Confirmation Buttons */}
                    {needsConfirmation && onConfirmation && (
                        <div style={{
                            display: 'flex',
                            gap: '0.5rem',
                            marginTop: '0.5rem'
                        }}>
                            <button
                                onClick={() => onConfirmation(true)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 1rem',
                                    background: 'linear-gradient(135deg, #059669, #10b981)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    transition: 'all 0.3s ease',
                                    boxShadow: 'var(--shadow-sm)'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                }}
                            >
                                <Check size={18} />
                                Yes
                            </button>
                            <button
                                onClick={() => onConfirmation(false)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 1rem',
                                    background: 'var(--bg-tertiary)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    transition: 'all 0.3s ease',
                                    boxShadow: 'var(--shadow-sm)'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'var(--bg-secondary)';
                                    e.currentTarget.style.borderColor = '#ef4444';
                                    e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                }}
                            >
                                <X size={18} />
                                No
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
