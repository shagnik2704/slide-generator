import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, Check, X, Edit2, Save, XCircle, Eye, Share2, Plus, Trash2, Download } from 'lucide-react';
import { apiJson, API_URL } from '../services/api';

const MessageBubble = ({ message, onConfirmation, onEditAnswer, mode, onShareComplete }) => {
    const isUser = message.role === 'user';
    const needsConfirmation = message.needsConfirmation && !isUser;
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(message.content);
    const [isSaving, setIsSaving] = useState(false);
    
    // Share form state
    const [showShareForm, setShowShareForm] = useState(false);
    const [recipients, setRecipients] = useState([{ email: '', role: 'writer' }]);
    const [isSharing, setIsSharing] = useState(false);
    const [shareMessage, setShareMessage] = useState(null);
    
    // Show edit button only for user messages in outline_chat mode that have a fieldName
    const canEdit = isUser && mode === 'outline_chat' && message.fieldName && !isEditing;
    
    const handleEdit = () => {
        setIsEditing(true);
        setEditValue(message.content);
    };
    
    const handleCancel = () => {
        setIsEditing(false);
        setEditValue(message.content);
    };
    
    const handleAddRecipient = () => {
        setRecipients([...recipients, { email: '', role: 'writer' }]);
    };

    const handleRemoveRecipient = (index) => {
        if (recipients.length > 1) {
            setRecipients(recipients.filter((_, i) => i !== index));
        }
    };

    const handleRecipientChange = (index, field, value) => {
        const newRecipients = [...recipients];
        newRecipients[index][field] = value;
        setRecipients(newRecipients);
    };

    const handleShareSubmit = async () => {
        const validRecipients = recipients.filter(r => r.email.trim());
        if (validRecipients.length === 0) {
            setShareMessage({ type: 'error', text: 'Please enter at least one email address' });
            return;
        }

        setIsSharing(true);
        setShareMessage(null);

        try {
            const data = await apiJson('/redesign/share', {
                method: 'POST',
                body: JSON.stringify({
                    url: message.previewButton.url,
                    recipients: validRecipients
                }),
            });

            setShareMessage({ type: 'success', text: data.message });
            
            // Call the callback to add a message showing share details
            if (onShareComplete) {
                console.log('Calling onShareComplete with recipients:', validRecipients);
                onShareComplete(validRecipients);
            } else {
                console.log('onShareComplete callback not available');
            }
            
            setTimeout(() => {
                setRecipients([{ email: '', role: 'writer' }]);
                setShowShareForm(false);
            }, 1500);
        } catch (error) {
            console.error('Error sharing:', error);
            setShareMessage({ type: 'error', text: error.message || 'Failed to share the sheet' });
        } finally {
            setIsSharing(false);
        }
    };
    
    const handleSave = async () => {
        if (!onEditAnswer || !message.fieldName) return;
        
        setIsSaving(true);
        try {
            // Determine tutorial number if it's a tutorial field
            let tutorialNumber = null;
            if (message.fieldName.startsWith('tutorial_')) {
                // Extract tutorial number from fieldName or message metadata
                // For tutorial fields, we may need to track which tutorial it belongs to
                // For now, we'll let the backend handle it or use message.tutorialNumber if available
                tutorialNumber = message.tutorialNumber || null;
            }
            
            await onEditAnswer(message.id, message.fieldName, editValue, tutorialNumber);
            setIsEditing(false);
        } catch (error) {
            console.error('Failed to save edit:', error);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            marginBottom: '1rem',
            padding: '0 1rem',
            animation: 'fadeIn 0.3s ease-out',
            position: 'relative',
            alignItems: 'flex-start'
        }}>
            <div style={{
                display: 'flex',
                flexDirection: isUser ? 'row-reverse' : 'row',
                maxWidth: isUser ? '70%' : '85%',
                gap: '0.5rem',
                width: isUser ? 'fit-content' : '100%',
                position: 'relative',
                alignItems: 'flex-start'
            }}>
                {/* Avatar */}
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: isUser ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: 'var(--shadow-sm)'
                }}>
                    {isUser ? <User size={18} color="white" /> : <Bot size={18} color="var(--accent-primary)" />}
                </div>

                {/* Edit Button - Outside bubble (placed before bubble for row-reverse to work correctly) */}
                {canEdit && !isEditing && (
                    <button
                        onClick={handleEdit}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '28px',
                            height: '28px',
                            padding: '0',
                            background: 'var(--bg-tertiary)',
                            color: 'var(--text-secondary)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '50%',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            transition: 'all 0.2s ease',
                            boxShadow: 'var(--shadow-sm)',
                            opacity: 0.7,
                            flexShrink: 0,
                            alignSelf: 'flex-start',
                            marginTop: '2px'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = '1';
                            e.currentTarget.style.background = 'var(--bg-secondary)';
                            e.currentTarget.style.borderColor = 'var(--accent-primary)';
                            e.currentTarget.style.color = 'var(--accent-primary)';
                            e.currentTarget.style.transform = 'scale(1.1)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = '0.7';
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.borderColor = 'var(--border-color)';
                            e.currentTarget.style.color = 'var(--text-secondary)';
                            e.currentTarget.style.transform = 'scale(1)';
                        }}
                        title={`Edit ${message.fieldName?.replace(/_/g, ' ')}`}
                    >
                        <Edit2 size={14} />
                    </button>
                )}

                {/* Message Content */}
                <div 
                    style={{
                        backgroundColor: isUser ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                        color: isUser ? 'var(--bg-primary)' : 'var(--text-primary)',
                        padding: isUser ? '0.6rem 1rem' : '0.75rem 1.25rem',
                        borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
                        boxShadow: 'var(--shadow-md)',
                        lineHeight: 1.5,
                        fontSize: '0.9rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: needsConfirmation || isEditing ? '0.75rem' : '0',
                        position: 'relative',
                        width: isUser ? 'fit-content' : '100%',
                        minWidth: isUser ? 'auto' : '200px',
                        maxWidth: '100%'
                    }}
                    className="message-bubble-container"
                >
                    {isEditing ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <textarea
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                                        handleSave();
                                    } else if (e.key === 'Escape') {
                                        handleCancel();
                                    }
                                }}
                                style={{
                                    width: '100%',
                                    minHeight: '60px',
                                    padding: '0.5rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.95rem',
                                    fontFamily: 'inherit',
                                    resize: 'vertical'
                                }}
                                disabled={isSaving}
                                autoFocus
                            />
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                <button
                                    onClick={handleCancel}
                                    disabled={isSaving}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                        padding: '0.4rem 0.75rem',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '0.5rem',
                                        cursor: isSaving ? 'not-allowed' : 'pointer',
                                        fontSize: '0.85rem',
                                        opacity: isSaving ? 0.5 : 1
                                    }}
                                >
                                    <XCircle size={14} />
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={isSaving || !editValue.trim()}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                        padding: '0.4rem 0.75rem',
                                        background: isSaving || !editValue.trim() ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, #059669, #10b981)',
                                        color: isSaving || !editValue.trim() ? 'var(--text-secondary)' : 'white',
                                        border: 'none',
                                        borderRadius: '0.5rem',
                                        cursor: isSaving || !editValue.trim() ? 'not-allowed' : 'pointer',
                                        fontSize: '0.85rem',
                                        fontWeight: 600
                                    }}
                                >
                                    <Save size={14} />
                                    {isSaving ? 'Saving...' : 'Save'}
                                </button>
                            </div>
                        </div>
                    ) : (
                            <div style={{ position: 'relative', width: '100%' }}>
                            <div className="markdown-content">
                                <ReactMarkdown>{message.content}</ReactMarkdown>
                                {message.isStreaming && <span className="streaming-cursor">▌</span>}
                                {message.wasEdited && (
                                    <span style={{
                                        fontSize: '0.75rem',
                                        opacity: 0.7,
                                        marginLeft: '0.5rem',
                                        fontStyle: 'italic'
                                    }}>✓ Updated</span>
                                )}
                            </div>
                            
                            {/* Redesign Result Download Button */}
                            {message.type === 'redesign_result' && message.downloadButton && (
                                <div style={{
                                    display: 'flex',
                                    gap: '0.75rem',
                                    marginTop: '1rem',
                                    flexWrap: 'wrap'
                                }}>
                                    <a
                                        href={`${API_URL}/download/redesign/${message.downloadButton.filename}`}
                                        download={message.downloadButton.filename}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.6rem 1.2rem',
                                            background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: 'pointer',
                                            fontWeight: 600,
                                            fontSize: '0.9rem',
                                            textDecoration: 'none',
                                            transition: 'all 0.3s ease',
                                            boxShadow: 'var(--shadow-md)'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-2px)';
                                            e.currentTarget.style.boxShadow = '0 8px 16px rgba(59, 130, 246, 0.4)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                        }}
                                    >
                                        <Download size={18} />
                                        {message.downloadButton.label}
                                    </a>
                                </div>
                            )}
                        </div>
                    )}

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
