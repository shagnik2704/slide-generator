import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { X, Search, Save, CheckCircle2, AlertCircle, Loader2, Edit3, HelpCircle } from 'lucide-react';
import { apiJson } from '../../services/api';

export function ChangeContentModal({ isOpen, onClose }) {
    const [faqs, setFaqs] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedId, setSelectedId] = useState(null);
    const [draft, setDraft] = useState(null);

    const loadFaqs = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await apiJson('/faq/admin/list');
            setFaqs(data || []);
            if (data && data.length > 0) {
                setSelectedId((curr) => curr || data[0].id);
            }
        } catch (err) {
            setError(err.message || 'Failed to load FAQ content');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (isOpen) {
            loadFaqs();
        }
    }, [isOpen, loadFaqs]);

    useEffect(() => {
        const selected = faqs.find((f) => f.id === selectedId) || null;
        if (selected) {
            setDraft({
                ...selected,
                aliasesStr: (selected.aliases || []).join(', '),
            });
        } else {
            setDraft(null);
        }
    }, [faqs, selectedId]);

    const filteredFaqs = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) return faqs;
        return faqs.filter(
            (f) =>
                (f.question || '').toLowerCase().includes(query) ||
                (f.answer || '').toLowerCase().includes(query) ||
                (f.category || '').toLowerCase().includes(query)
        );
    }, [faqs, searchQuery]);

    const handleSave = async () => {
        if (!draft) return;
        setIsSaving(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const aliasesArray = draft.aliasesStr
                ? draft.aliasesStr.split(',').map((s) => s.trim()).filter(Boolean)
                : [];

            const updated = await apiJson(`/faq/admin/${draft.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    category: draft.category,
                    question: draft.question,
                    answer: draft.answer,
                    aliases: aliasesArray,
                }),
            });

            setFaqs((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
            setSuccessMessage('FAQ updated and re-indexed successfully!');
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            setError(err.message || 'Failed to save FAQ');
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '1.5rem',
            }}
        >
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(0, 0, 0, 0.65)',
                    backdropFilter: 'blur(4px)',
                }}
            />

            {/* Modal Dialog */}
            <div
                style={{
                    position: 'relative',
                    width: '100%',
                    maxWidth: '960px',
                    height: '85vh',
                    maxHeight: '750px',
                    background: 'var(--bg-secondary)',
                    borderRadius: '1rem',
                    border: '1px solid var(--border-color)',
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    zIndex: 10,
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '1.25rem 1.5rem',
                        borderBottom: '1px solid var(--border-color)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: 'var(--bg-tertiary)',
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div
                            style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '8px',
                                background: 'rgba(99, 102, 241, 0.15)',
                                color: 'var(--accent-primary)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                        >
                            <Edit3 size={20} />
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.15rem', fontWeight: '600', margin: 0, color: 'var(--text-primary)' }}>
                                Manage FAQ Content
                            </h2>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                                Edit questions and answers. Edits apply immediately with real-time vector re-indexing.
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.5rem',
                            borderRadius: '0.5rem',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content Split: Left List / Right Editor */}
                <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
                    {/* Left Pane: Search + FAQ List */}
                    <div
                        style={{
                            width: '38%',
                            borderRight: '1px solid var(--border-color)',
                            display: 'flex',
                            flexDirection: 'column',
                            background: 'var(--bg-primary)',
                        }}
                    >
                        {/* Search Input */}
                        <div style={{ padding: '0.875rem 1rem', borderBottom: '1px solid var(--border-color)' }}>
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    background: 'var(--bg-secondary)',
                                    padding: '0.45rem 0.75rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                }}
                            >
                                <Search size={15} style={{ color: 'var(--text-secondary)' }} />
                                <input
                                    type="text"
                                    placeholder="Search FAQs..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        outline: 'none',
                                        color: 'var(--text-primary)',
                                        fontSize: '0.85rem',
                                        width: '100%',
                                    }}
                                />
                            </div>
                        </div>

                        {/* List */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
                            {isLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
                                    <Loader2 size={24} className="spin" style={{ color: 'var(--accent-primary)' }} />
                                </div>
                            ) : filteredFaqs.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                    No FAQs found
                                </div>
                            ) : (
                                filteredFaqs.map((item) => {
                                    const isSelected = item.id === selectedId;
                                    return (
                                        <button
                                            key={item.id}
                                            onClick={() => setSelectedId(item.id)}
                                            style={{
                                                display: 'block',
                                                width: '100%',
                                                textAlign: 'left',
                                                padding: '0.75rem',
                                                borderRadius: '0.5rem',
                                                border: isSelected ? '1px solid var(--accent-primary)' : '1px solid transparent',
                                                background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'transparent',
                                                cursor: 'pointer',
                                                marginBottom: '0.25rem',
                                                transition: 'all 0.15s',
                                            }}
                                        >
                                            <div style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', fontWeight: '600', marginBottom: '2px' }}>
                                                {item.category}
                                            </div>
                                            <div
                                                style={{
                                                    fontSize: '0.85rem',
                                                    color: 'var(--text-primary)',
                                                    fontWeight: isSelected ? '600' : '400',
                                                    whiteSpace: 'nowrap',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                }}
                                            >
                                                {item.question}
                                            </div>
                                        </button>
                                    );
                                })
                            )}
                        </div>
                    </div>

                    {/* Right Pane: Edit Form */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', overflowY: 'auto' }}>
                        {draft ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                                {error && (
                                    <div
                                        style={{
                                            padding: '0.75rem 1rem',
                                            borderRadius: '0.5rem',
                                            background: 'rgba(239, 68, 68, 0.1)',
                                            border: '1px solid rgba(239, 68, 68, 0.25)',
                                            color: '#f87171',
                                            fontSize: '0.85rem',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                        }}
                                    >
                                        <AlertCircle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}

                                {successMessage && (
                                    <div
                                        style={{
                                            padding: '0.75rem 1rem',
                                            borderRadius: '0.5rem',
                                            background: 'rgba(34, 197, 94, 0.1)',
                                            border: '1px solid rgba(34, 197, 94, 0.25)',
                                            color: '#4ade80',
                                            fontSize: '0.85rem',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                        }}
                                    >
                                        <CheckCircle2 size={16} />
                                        <span>{successMessage}</span>
                                    </div>
                                )}

                                <div>
                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                                        CATEGORY
                                    </label>
                                    <input
                                        type="text"
                                        value={draft.category}
                                        onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '0.6rem 0.85rem',
                                            borderRadius: '0.5rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-primary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.875rem',
                                            outline: 'none',
                                        }}
                                    />
                                </div>

                                <div>
                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                                        QUESTION
                                    </label>
                                    <input
                                        type="text"
                                        value={draft.question}
                                        onChange={(e) => setDraft({ ...draft, question: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '0.6rem 0.85rem',
                                            borderRadius: '0.5rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-primary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.875rem',
                                            outline: 'none',
                                        }}
                                    />
                                </div>

                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                                        OFFICIAL ANSWER
                                    </label>
                                    <textarea
                                        rows={8}
                                        value={draft.answer}
                                        onChange={(e) => setDraft({ ...draft, answer: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem 0.85rem',
                                            borderRadius: '0.5rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-primary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.875rem',
                                            lineHeight: '1.6',
                                            outline: 'none',
                                            resize: 'vertical',
                                        }}
                                    />
                                </div>

                                <div>
                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                                        SEARCH ALIASES / KEYWORDS (comma separated)
                                    </label>
                                    <input
                                        type="text"
                                        value={draft.aliasesStr || ''}
                                        onChange={(e) => setDraft({ ...draft, aliasesStr: e.target.value })}
                                        placeholder="e.g. max students, student limit, batch capacity"
                                        style={{
                                            width: '100%',
                                            padding: '0.6rem 0.85rem',
                                            borderRadius: '0.5rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-primary)',
                                            color: 'var(--text-primary)',
                                            fontSize: '0.875rem',
                                            outline: 'none',
                                        }}
                                    />
                                </div>

                                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                                    <button
                                        onClick={handleSave}
                                        disabled={isSaving}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.65rem 1.25rem',
                                            borderRadius: '0.5rem',
                                            border: 'none',
                                            background: 'var(--accent-primary)',
                                            color: '#ffffff',
                                            fontSize: '0.9rem',
                                            fontWeight: '500',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        {isSaving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                                        <span>Save Changes</span>
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                                Select an FAQ entry to edit
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
