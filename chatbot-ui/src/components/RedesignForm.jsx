import React, { useState } from 'react';
import { Send, X, Plus, Share2, Eye } from 'lucide-react';

/**
 * RedesignForm - Form component for submitting tutorial redesign requests
 */
export default function RedesignForm({ onSubmit, onCancel }) {
    const [step, setStep] = useState('generate'); // 'generate' | 'preview'
    const [generatedUrl, setGeneratedUrl] = useState('');
    const [hasShared, setHasShared] = useState(false);
    const [fossName, setFossName] = useState('');
    const [language, setLanguage] = useState('English');
    const [recipients, setRecipients] = useState([{ email: '', role: 'writer' }]);
    const [errors, setErrors] = useState({});

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

    const validateEmail = (email) => {
        if (!email) return true; // Empty emails are allowed (will be filtered out)
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleGenerate = async (e) => {
        e.preventDefault();
        
        // Validation
        const newErrors = {};
        if (!fossName.trim()) {
            newErrors.fossName = 'FOSS Name is required';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Submit generate request
        const result = await onSubmit({
            type: 'generate',
            foss_name: fossName.trim(),
            language: language.trim() || 'English'
        });

        if (result && result.url) {
            setGeneratedUrl(result.url);
            setStep('preview');
        }
    };

    const handleShare = async (e) => {
        e.preventDefault();
        
        // Validation
        const newErrors = {};
        const invalidRecipients = recipients.filter(recipient => recipient.email && !validateEmail(recipient.email));
        if (invalidRecipients.length > 0) {
            newErrors.emails = 'Please enter valid email addresses';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Filter out empty emails
        const validRecipients = recipients.filter(recipient => recipient.email.trim() !== '');

        // Submit share request
        await onSubmit({
            type: 'share',
            url: generatedUrl,
            recipients: validRecipients
        });

        setHasShared(true);

        // Keep the form open for further actions
    };

    const inputStyle = {
        width: '100%',
        padding: '0.75rem 1rem',
        borderRadius: '0.5rem',
        border: '1px solid var(--border-color)',
        background: 'var(--bg-secondary)',
        color: 'var(--text-primary)',
        fontSize: '0.95rem',
        fontFamily: 'inherit',
        outline: 'none',
        transition: 'border-color 0.2s ease'
    };

    const labelStyle = {
        display: 'block',
        marginBottom: '0.5rem',
        fontSize: '0.9rem',
        fontWeight: 500,
        color: 'var(--text-primary)'
    };

    const errorStyle = {
        color: '#ef4444',
        fontSize: '0.85rem',
        marginTop: '0.25rem'
    };

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '1rem',
            padding: '1.5rem',
            marginBottom: '1rem',
            boxShadow: 'var(--shadow-md)',
            maxWidth: '800px',
            margin: '0 auto 1rem auto'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.5rem'
            }}>
                <h2 style={{
                    fontSize: '1.25rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    margin: 0
                }}>
                    {step === 'generate' ? 'Generate Tutorial' : 'Preview & Share'}
                </h2>
                {onCancel && (
                    <button
                        onClick={onCancel}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.25rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '0.25rem',
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--text-primary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = 'var(--text-secondary)';
                        }}
                    >
                        <X size={20} />
                    </button>
                )}
            </div>

            {step === 'generate' ? (
                <form onSubmit={handleGenerate}>
                    {/* FOSS Name */}
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={labelStyle}>
                            FOSS Name <span style={{ color: '#ef4444' }}>*</span>
                        </label>
                        <input
                            type="text"
                            value={fossName}
                            onChange={(e) => {
                                setFossName(e.target.value);
                                if (errors.fossName) setErrors({ ...errors, fossName: null });
                            }}
                            style={{
                                ...inputStyle,
                                borderColor: errors.fossName ? '#ef4444' : 'var(--border-color)'
                            }}
                            placeholder="Enter FOSS name"
                            required
                        />
                        {errors.fossName && <div style={errorStyle}>{errors.fossName}</div>}
                    </div>

                    {/* Language */}
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={labelStyle}>Language</label>
                        <input
                            type="text"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            style={inputStyle}
                            placeholder="English"
                        />
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        style={{
                            width: '100%',
                            padding: '0.75rem 1.5rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            fontSize: '0.95rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            transition: 'all 0.2s ease',
                            boxShadow: 'var(--shadow-sm)'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = '0.9';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = '1';
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                        }}
                    >
                        <Send size={16} />
                        Update and Redesign
                    </button>
                </form>
            ) : (
                <div>
                    {/* Preview */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                            Preview Sheet
                        </h3>
                        <button
                            onClick={() => window.open(generatedUrl, '_blank')}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.75rem 1.5rem',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '0.5rem',
                                fontSize: '0.95rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                boxShadow: 'var(--shadow-sm)'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.opacity = '0.9';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.opacity = '1';
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            }}
                        >
                            <Eye size={16} />
                            Preview in New Tab
                        </button>
                    </div>

                    {/* Share Form */}
                    <form onSubmit={handleShare}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                            <Share2 size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                            Share with Users
                        </h3>

                        {/* Receipt Emails and Roles */}
                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Receipt Emails and Roles</label>
                            {recipients.map((recipient, index) => (
                                <div key={index} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                                    <input
                                        type="email"
                                        value={recipient.email}
                                        onChange={(e) => {
                                            handleRecipientChange(index, 'email', e.target.value);
                                            if (errors.emails) setErrors({ ...errors, emails: null });
                                        }}
                                        style={{
                                            ...inputStyle,
                                            borderColor: errors.emails ? '#ef4444' : 'var(--border-color)',
                                            flex: 1
                                        }}
                                        placeholder="user@example.com"
                                    />
                                    <select
                                        value={recipient.role}
                                        onChange={(e) => handleRecipientChange(index, 'role', e.target.value)}
                                        style={{
                                            ...inputStyle,
                                            width: '120px',
                                            padding: '0.75rem 0.5rem'
                                        }}
                                    >
                                        <option value="writer">Writer</option>
                                        <option value="commenter">Commenter</option>
                                        <option value="reader">Reader</option>
                                    </select>
                                    {recipients.length > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveRecipient(index)}
                                            style={{
                                                background: 'transparent',
                                                border: '1px solid var(--border-color)',
                                                borderRadius: '0.5rem',
                                                color: 'var(--text-secondary)',
                                                cursor: 'pointer',
                                                padding: '0.75rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                transition: 'all 0.2s ease'
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
                                            <X size={16} />
                                        </button>
                                    )}
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={handleAddRecipient}
                                style={{
                                    background: 'transparent',
                                    border: '1px dashed var(--border-color)',
                                    borderRadius: '0.5rem',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    padding: '0.5rem 0.75rem',
                                    fontSize: '0.85rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    transition: 'all 0.2s ease'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                                    e.currentTarget.style.color = 'var(--accent-primary)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                    e.currentTarget.style.color = 'var(--text-secondary)';
                                }}
                            >
                                <Plus size={14} />
                                Add Recipient
                            </button>
                            {errors.emails && <div style={errorStyle}>{errors.emails}</div>}
                        </div>

                        {/* Share Button */}
                        <button
                            type="submit"
                            style={{
                                width: '100%',
                                padding: '0.75rem 1.5rem',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '0.5rem',
                                fontSize: '0.95rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.2s ease',
                                boxShadow: 'var(--shadow-sm)'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.opacity = '0.9';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.opacity = '1';
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            }}
                        >
                            <Share2 size={16} />
                            Share
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
