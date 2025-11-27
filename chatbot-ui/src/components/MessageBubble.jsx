import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';

const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user';

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
                    color: isUser ? 'white' : 'var(--text-primary)',
                    padding: '0.75rem 1.25rem',
                    borderRadius: isUser ? '1.25rem 1.25rem 0.25rem 1.25rem' : '1.25rem 1.25rem 1.25rem 0.25rem',
                    boxShadow: 'var(--shadow-md)',
                    lineHeight: 1.6,
                    fontSize: '0.95rem'
                }}>
                    <div className="markdown-content">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
