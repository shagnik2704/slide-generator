import React, { useState, useEffect } from 'react';
import { X, Share2, Plus, Trash2 } from 'lucide-react';
import { apiJson } from '../services/api';

const ShareRedesignModal = ({ isOpen, onClose, url }) => {
    const [recipients, setRecipients] = useState([{ email: '', role: 'writer' }]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState(null);

    // Close on Escape key
    useEffect(() => {
        const handleEscape = (e) => {
            if (e.key === 'Escape') onClose();
        };
        if (isOpen) {
            document.addEventListener('keydown', handleEscape);
            document.body.style.overflow = 'hidden';
        }
        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.body.style.overflow = 'unset';
        };
    }, [isOpen, onClose]);

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

    const handleShare = async () => {
        // Validate emails
        const validRecipients = recipients.filter(r => r.email.trim());
        if (validRecipients.length === 0) {
            setMessage({ type: 'error', text: 'Please enter at least one email address' });
            return;
        }

        setIsLoading(true);
        setMessage(null);

        try {
            const data = await apiJson('/redesign/share', {
                method: 'POST',
                body: JSON.stringify({
                    url: url,
                    recipients: validRecipients
                }),
            });

            setMessage({ type: 'success', text: data.message });
            setTimeout(() => {
                setRecipients([{ email: '', role: 'writer' }]);
                onClose();
            }, 1500);
        } catch (error) {
            console.error('Error sharing:', error);
            setMessage({ type: 'error', text: error.message || 'Failed to share the sheet' });
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    const modalOverlayStyle = {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(4px)',
    };

    const modalContentStyle = {
        background: 'var(--bg-secondary)',
        borderRadius: '16px',
        border: '1px solid var(--border-primary)',
        width: '90%',
        maxWidth: '500px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    };

    const headerStyle = {
        padding: '1.25rem 1.5rem',
        borderBottom: '1px solid var(--border-primary)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    };

    const bodyStyle = {
        padding: '1.5rem',
        maxHeight: '60vh',
        overflowY: 'auto',
    };

    const footerStyle = {
        padding: '1rem 1.5rem',
        borderTop: '1px solid var(--border-primary)',
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '0.75rem',
    };

    const buttonStyle = (isPrimary) => ({
        padding: '0.75rem 1.5rem',
        borderRadius: '10px',
        fontWeight: 600,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: isPrimary ? 'var(--accent-primary)' : 'transparent',
        color: isPrimary ? 'white' : 'var(--text-secondary)',
        border: isPrimary ? 'none' : '1px solid var(--border-primary)',
        transition: 'all 0.2s ease',
        opacity: isPrimary && isLoading ? 0.6 : 1,
        cursor: isPrimary && isLoading ? 'not-allowed' : 'pointer',
    });

    const inputStyle = {
        padding: '0.75rem',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        fontSize: '0.95rem',
        fontFamily: 'inherit',
    };

    const selectStyle = {
        ...inputStyle,
        cursor: 'pointer',
    };

    const recipientRowStyle = {
        display: 'grid',
        gridTemplateColumns: '1fr 120px 40px',
        gap: '0.75rem',
        alignItems: 'flex-end',
        marginBottom: '1rem',
    };

    return (
        <div style={modalOverlayStyle} onClick={onClose}>
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={headerStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Share2 size={24} style={{ color: 'var(--accent-primary)' }} />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                            Share Sheet
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.5rem',
                        }}
                        disabled={isLoading}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div style={bodyStyle}>
                    <p style={{
                        color: 'var(--text-secondary)',
                        fontSize: '0.95rem',
                        marginBottom: '1.5rem',
                    }}>
                        Share this tutorial sheet with others. Add their email addresses and choose their role.
                    </p>

                    {/* Recipients List */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{
                            display: 'block',
                            fontSize: '0.9rem',
                            fontWeight: 600,
                            marginBottom: '0.75rem',
                            color: 'var(--text-primary)',
                        }}>
                            Recipients
                        </label>

                        {recipients.map((recipient, index) => (
                            <div key={index} style={recipientRowStyle}>
                                <input
                                    type="email"
                                    placeholder="Enter email address"
                                    value={recipient.email}
                                    onChange={(e) => handleRecipientChange(index, 'email', e.target.value)}
                                    style={inputStyle}
                                    disabled={isLoading}
                                />
                                <select
                                    value={recipient.role}
                                    onChange={(e) => handleRecipientChange(index, 'role', e.target.value)}
                                    style={selectStyle}
                                    disabled={isLoading}
                                >
                                    <option value="reader">Reader</option>
                                    <option value="writer">Writer</option>
                                    <option value="commenter">Commenter</option>
                                </select>
                                <button
                                    onClick={() => handleRemoveRecipient(index)}
                                    disabled={recipients.length === 1 || isLoading}
                                    style={{
                                        background: 'transparent',
                                        border: '1px solid var(--border-color)',
                                        color: 'var(--text-secondary)',
                                        cursor: recipients.length === 1 || isLoading ? 'not-allowed' : 'pointer',
                                        padding: '0.75rem',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        opacity: recipients.length === 1 || isLoading ? 0.5 : 1,
                                    }}
                                    title="Remove recipient"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        ))}

                        {/* Add Recipient Button */}
                        <button
                            onClick={handleAddRecipient}
                            disabled={isLoading}
                            style={{
                                background: 'transparent',
                                border: '1px dashed var(--border-color)',
                                color: 'var(--accent-primary)',
                                cursor: isLoading ? 'not-allowed' : 'pointer',
                                padding: '0.75rem 1rem',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                fontWeight: 500,
                                width: '100%',
                                opacity: isLoading ? 0.5 : 1,
                            }}
                        >
                            <Plus size={18} />
                            Add another recipient
                        </button>
                    </div>

                    {/* Message */}
                    {message && (
                        <div style={{
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            marginBottom: '1rem',
                            fontSize: '0.95rem',
                            background: message.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                            color: message.type === 'error' ? '#ef4444' : '#10b981',
                            border: `1px solid ${message.type === 'error' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                        }}>
                            {message.text}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={footerStyle}>
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        style={{ ...buttonStyle(false), opacity: isLoading ? 0.5 : 1 }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleShare}
                        disabled={isLoading}
                        style={{ ...buttonStyle(true) }}
                    >
                        <Share2 size={18} />
                        {isLoading ? 'Sharing...' : 'Share Sheet'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ShareRedesignModal;
