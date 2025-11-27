import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Mic } from 'lucide-react';

const InputArea = ({ onSendMessage, disabled }) => {
    const [input, setInput] = useState('');
    const textareaRef = useRef(null);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSendMessage(input);
            setInput('');
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleInput = (e) => {
        const target = e.target;
        target.style.height = 'auto';
        target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
        setInput(target.value);
    };

    return (
        <div style={{
            padding: '1.5rem',
            background: 'linear-gradient(to top, var(--bg-primary) 80%, transparent)',
            position: 'relative',
            zIndex: 10
        }}>
            <div style={{
                maxWidth: '800px',
                margin: '0 auto',
                position: 'relative'
            }}>
                <form onSubmit={handleSubmit} style={{
                    position: 'relative',
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: '0.5rem',
                    background: 'var(--bg-secondary)',
                    borderRadius: '1rem',
                    padding: '0.75rem',
                    boxShadow: 'var(--shadow-lg)',
                    border: '1px solid var(--border-color)'
                }}>
                    <button type="button" className="btn-icon">
                        <Paperclip size={20} />
                    </button>

                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={handleInput}
                        onKeyDown={handleKeyDown}
                        placeholder="Message Chatbot..."
                        rows={1}
                        disabled={disabled}
                        style={{
                            flex: 1,
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-primary)',
                            resize: 'none',
                            padding: '0.5rem',
                            fontSize: '1rem',
                            lineHeight: 1.5,
                            maxHeight: '200px',
                            outline: 'none',
                            fontFamily: 'inherit'
                        }}
                    />

                    {input.trim() ? (
                        <button type="submit" className="btn-primary" style={{ padding: '0.5rem', borderRadius: '0.5rem' }} disabled={disabled}>
                            <Send size={20} />
                        </button>
                    ) : (
                        <button type="button" className="btn-icon">
                            <Mic size={20} />
                        </button>
                    )}
                </form>
                <div style={{
                    textAlign: 'center',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    marginTop: '0.75rem'
                }}>
                    AI can make mistakes. Please verify important information.
                </div>
            </div>
        </div>
    );
};

export default InputArea;
