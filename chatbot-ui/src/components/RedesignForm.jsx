import React, { useState } from 'react';
import { Send, X, Plus } from 'lucide-react';

/**
 * RedesignForm - Form component for submitting tutorial redesign requests
 */
export default function RedesignForm({ onSubmit, onCancel }) {
    const [fossName, setFossName] = useState('');
    const [language, setLanguage] = useState('English');
    const [userEmails, setUserEmails] = useState(['']);
    const [userRole, setUserRole] = useState('writer');
    const [exportEnabled, setExportEnabled] = useState(true);
    const [errors, setErrors] = useState({});

    const handleAddEmail = () => {
        setUserEmails([...userEmails, '']);
    };

    const handleRemoveEmail = (index) => {
        if (userEmails.length > 1) {
            setUserEmails(userEmails.filter((_, i) => i !== index));
        }
    };

    const handleEmailChange = (index, value) => {
        const newEmails = [...userEmails];
        newEmails[index] = value;
        setUserEmails(newEmails);
    };

    const validateEmail = (email) => {
        if (!email) return true; // Empty emails are allowed (will be filtered out)
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        // Validation
        const newErrors = {};
        if (!fossName.trim()) {
            newErrors.fossName = 'FOSS Name is required';
        }

        // Validate emails
        const invalidEmails = userEmails.filter(email => email && !validateEmail(email));
        if (invalidEmails.length > 0) {
            newErrors.emails = 'Please enter valid email addresses';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Filter out empty emails
        const validEmails = userEmails.filter(email => email.trim() !== '');

        // Submit form data
        onSubmit({
            foss_name: fossName.trim(),
            language: language.trim() || 'English',
            user_emails: validEmails,
            user_role: userRole.trim() || 'writer',
            export: exportEnabled
        });
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
            maxWidth: '600px',
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
                    Tutorial Redesign
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

            <form onSubmit={handleSubmit}>
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

                {/* User Emails */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <label style={labelStyle}>User Emails</label>
                    {userEmails.map((email, index) => (
                        <div key={index} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => {
                                    handleEmailChange(index, e.target.value);
                                    if (errors.emails) setErrors({ ...errors, emails: null });
                                }}
                                style={{
                                    ...inputStyle,
                                    borderColor: errors.emails ? '#ef4444' : 'var(--border-color)'
                                }}
                                placeholder="user@example.com"
                            />
                            {userEmails.length > 1 && (
                                <button
                                    type="button"
                                    onClick={() => handleRemoveEmail(index)}
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
                        onClick={handleAddEmail}
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
                        Add Email
                    </button>
                    {errors.emails && <div style={errorStyle}>{errors.emails}</div>}
                </div>

                {/* User Role */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <label style={labelStyle}>User Role</label>
                    <input
                        type="text"
                        value={userRole}
                        onChange={(e) => setUserRole(e.target.value)}
                        style={inputStyle}
                        placeholder="writer"
                    />
                </div>

                {/* Export Checkbox */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: 'pointer',
                        fontSize: '0.95rem',
                        color: 'var(--text-primary)'
                    }}>
                        <input
                            type="checkbox"
                            checked={exportEnabled}
                            onChange={(e) => setExportEnabled(e.target.checked)}
                            style={{
                                width: '18px',
                                height: '18px',
                                cursor: 'pointer',
                                accentColor: 'var(--accent-primary)'
                            }}
                        />
                        <span>Export</span>
                    </label>
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
                    Submit Redesign Request
                </button>
            </form>
        </div>
    );
}
