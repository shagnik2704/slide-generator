import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    X,
    Search,
    Save,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Edit3,
    FileText,
    UploadCloud,
    Trash2,
    BookOpen,
    Layers,
    Calendar,
    HelpCircle,
} from 'lucide-react';
import { apiJson, apiFormData } from '../../services/api';

export function ChangeContentModal({ isOpen, onClose }) {
    const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'editor'

    // FAQ items state (for Editor tab)
    const [faqs, setFaqs] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedId, setSelectedId] = useState(null);
    const [draft, setDraft] = useState(null);

    // Document state (for Documents tab)
    const [documents, setDocuments] = useState([]);
    const [isDocsLoading, setIsDocsLoading] = useState(false);
    const [selectedPdf, setSelectedPdf] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [docError, setDocError] = useState(null);
    const [docSuccess, setDocSuccess] = useState(null);
    const [deletingDoc, setDeletingDoc] = useState(null);
    const fileInputRef = useRef(null);

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

    const loadDocuments = useCallback(async () => {
        setIsDocsLoading(true);
        setDocError(null);
        try {
            const docs = await apiJson('/faq/documents');
            setDocuments(docs || []);
        } catch (err) {
            setDocError(err.message || 'Failed to load documents');
        } finally {
            setIsDocsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (isOpen) {
            loadFaqs();
            loadDocuments();
        }
    }, [isOpen, loadFaqs, loadDocuments]);

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

    const handleSaveFaq = async () => {
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

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                setDocError('Please select a valid .pdf document');
                return;
            }
            setSelectedPdf(file);
            setDocError(null);
        }
    };

    const handleUploadPdf = async () => {
        if (!selectedPdf) return;
        setIsUploading(true);
        setDocError(null);
        setDocSuccess(null);

        const formData = new FormData();
        formData.append('file', selectedPdf);

        try {
            const res = await apiFormData('/faq/documents/upload', formData);
            setDocSuccess(res.message || `Successfully extracted ${res.entries_extracted} FAQs from ${selectedPdf.name}`);
            setSelectedPdf(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
            // Refresh both documents and FAQs
            await Promise.all([loadDocuments(), loadFaqs()]);
            setTimeout(() => setDocSuccess(null), 5000);
        } catch (err) {
            setDocError(err.message || 'Failed to parse and extract FAQs from PDF');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeleteDocument = async (docName) => {
        const confirmed = window.confirm(
            `Are you sure you want to remove "${docName}"?\n\nAll FAQ entries extracted from this document will be permanently deleted from the chatbot knowledge base.`
        );
        if (!confirmed) return;

        setDeletingDoc(docName);
        setDocError(null);
        setDocSuccess(null);

        try {
            const res = await apiJson(`/faq/documents/${encodeURIComponent(docName)}`, {
                method: 'DELETE',
            });
            setDocSuccess(res.message || `Document "${docName}" removed.`);
            await Promise.all([loadDocuments(), loadFaqs()]);
            setTimeout(() => setDocSuccess(null), 4000);
        } catch (err) {
            setDocError(err.message || `Failed to remove ${docName}`);
        } finally {
            setDeletingDoc(null);
        }
    };

    const formatBytes = (bytes) => {
        if (!bytes || bytes === 0) return '—';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
                    maxHeight: '780px',
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
                            <BookOpen size={20} />
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.15rem', fontWeight: '600', margin: 0, color: 'var(--text-primary)' }}>
                                Manage FAQ Knowledge Base
                            </h2>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                                Add or remove guidelines via PDF upload, or fine-tune individual Q&A answers.
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
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs Bar */}
                <div
                    style={{
                        display: 'flex',
                        gap: '0.5rem',
                        padding: '0.5rem 1.5rem',
                        background: 'var(--bg-secondary)',
                        borderBottom: '1px solid var(--border-color)',
                    }}
                >
                    <button
                        onClick={() => setActiveTab('documents')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.45rem',
                            padding: '0.5rem 0.95rem',
                            borderRadius: '0.5rem',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            border: 'none',
                            background: activeTab === 'documents' ? 'var(--accent-primary)' : 'transparent',
                            color: activeTab === 'documents' ? '#ffffff' : 'var(--text-secondary)',
                            transition: 'all 0.15s',
                        }}
                    >
                        <FileText size={16} />
                        <span>PDF Documents</span>
                        <span
                            style={{
                                marginLeft: '0.25rem',
                                padding: '1px 6px',
                                borderRadius: '999px',
                                fontSize: '0.7rem',
                                background: activeTab === 'documents' ? 'rgba(255,255,255,0.25)' : 'var(--bg-tertiary)',
                            }}
                        >
                            {documents.length}
                        </span>
                    </button>

                    <button
                        onClick={() => setActiveTab('editor')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.45rem',
                            padding: '0.5rem 0.95rem',
                            borderRadius: '0.5rem',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            border: 'none',
                            background: activeTab === 'editor' ? 'var(--accent-primary)' : 'transparent',
                            color: activeTab === 'editor' ? '#ffffff' : 'var(--text-secondary)',
                            transition: 'all 0.15s',
                        }}
                    >
                        <Edit3 size={16} />
                        <span>Edit Q&A Entries</span>
                        <span
                            style={{
                                marginLeft: '0.25rem',
                                padding: '1px 6px',
                                borderRadius: '999px',
                                fontSize: '0.7rem',
                                background: activeTab === 'editor' ? 'rgba(255,255,255,0.25)' : 'var(--bg-tertiary)',
                            }}
                        >
                            {faqs.length}
                        </span>
                    </button>
                </div>

                {/* TAB 1: PDF Documents Ingestion */}
                {activeTab === 'documents' && (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', overflowY: 'auto', gap: '1.5rem' }}>
                        {/* Status Messages */}
                        {docError && (
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
                                <span>{docError}</span>
                            </div>
                        )}

                        {docSuccess && (
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
                                <span>{docSuccess}</span>
                            </div>
                        )}

                        {/* Upload Card */}
                        <div
                            style={{
                                border: '2px dashed var(--border-color)',
                                borderRadius: '0.75rem',
                                padding: '1.75rem',
                                background: 'var(--bg-primary)',
                                textAlign: 'center',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '0.75rem',
                            }}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                onChange={handleFileChange}
                                style={{ display: 'none' }}
                                id="faq-pdf-file-input"
                            />

                            <div
                                style={{
                                    width: '48px',
                                    height: '48px',
                                    borderRadius: '50%',
                                    background: 'rgba(99, 102, 241, 0.12)',
                                    color: 'var(--accent-primary)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <UploadCloud size={24} />
                            </div>

                            <div>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: 'var(--text-primary)', margin: 0 }}>
                                    Upload FAQ Document / Guidelines
                                </h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                                    Upload any official Spoken Tutorial PDF. The AI automatically parses all questions and answers into vector search.
                                </p>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
                                <label
                                    htmlFor="faq-pdf-file-input"
                                    style={{
                                        padding: '0.55rem 1.1rem',
                                        borderRadius: '0.5rem',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        fontSize: '0.85rem',
                                        fontWeight: '500',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s',
                                    }}
                                >
                                    Browse PDF File
                                </label>

                                {selectedPdf && (
                                    <span style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: '500' }}>
                                        📄 {selectedPdf.name} ({formatBytes(selectedPdf.size)})
                                    </span>
                                )}

                                {selectedPdf && (
                                    <button
                                        onClick={handleUploadPdf}
                                        disabled={isUploading}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.45rem',
                                            padding: '0.55rem 1.25rem',
                                            borderRadius: '0.5rem',
                                            border: 'none',
                                            background: 'var(--accent-primary)',
                                            color: '#ffffff',
                                            fontSize: '0.85rem',
                                            fontWeight: '600',
                                            cursor: isUploading ? 'not-allowed' : 'pointer',
                                            opacity: isUploading ? 0.75 : 1,
                                        }}
                                    >
                                        {isUploading ? (
                                            <>
                                                <Loader2 size={16} className="spin" />
                                                <span>Extracting FAQs via AI...</span>
                                            </>
                                        ) : (
                                            <>
                                                <UploadCloud size={16} />
                                                <span>Ingest PDF</span>
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Indexed Documents Table */}
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                                <h4 style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--text-primary)', margin: 0 }}>
                                    Currently Indexed Documents
                                </h4>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    {documents.length} document(s) contributing to chatbot
                                </span>
                            </div>

                            {isDocsLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
                                    <Loader2 size={24} className="spin" style={{ color: 'var(--accent-primary)' }} />
                                </div>
                            ) : documents.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '2rem', background: 'var(--bg-primary)', borderRadius: '0.5rem', color: 'var(--text-secondary)' }}>
                                    No documents indexed yet.
                                </div>
                            ) : (
                                <div
                                    style={{
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '0.75rem',
                                        overflow: 'hidden',
                                        background: 'var(--bg-primary)',
                                    }}
                                >
                                    {documents.map((doc, idx) => {
                                        const isDeleting = deletingDoc === doc.name;
                                        return (
                                            <div
                                                key={doc.name}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'space-between',
                                                    padding: '0.875rem 1.25rem',
                                                    borderBottom: idx === documents.length - 1 ? 'none' : '1px solid var(--border-color)',
                                                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)',
                                                }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <div
                                                        style={{
                                                            width: '34px',
                                                            height: '34px',
                                                            borderRadius: '6px',
                                                            background: 'rgba(239, 68, 68, 0.1)',
                                                            color: '#ef4444',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                        }}
                                                    >
                                                        <FileText size={18} />
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                                                            {doc.name}
                                                        </div>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '2px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                            <span>{doc.entry_count} Q&As</span>
                                                            {doc.size_bytes && <span>• {formatBytes(doc.size_bytes)}</span>}
                                                            {doc.is_default && (
                                                                <span
                                                                    style={{
                                                                        padding: '1px 6px',
                                                                        borderRadius: '4px',
                                                                        background: 'rgba(99, 102, 241, 0.15)',
                                                                        color: 'var(--accent-primary)',
                                                                        fontWeight: '500',
                                                                    }}
                                                                >
                                                                    Base Corpus
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>

                                                <button
                                                    onClick={() => handleDeleteDocument(doc.name)}
                                                    disabled={isDeleting}
                                                    title={`Remove ${doc.name} and delete all ${doc.entry_count} FAQs`}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.35rem',
                                                        padding: '0.4rem 0.75rem',
                                                        borderRadius: '0.4rem',
                                                        border: '1px solid rgba(239, 68, 68, 0.3)',
                                                        background: 'transparent',
                                                        color: '#ef4444',
                                                        fontSize: '0.8rem',
                                                        fontWeight: '500',
                                                        cursor: isDeleting ? 'not-allowed' : 'pointer',
                                                        transition: 'all 0.15s',
                                                    }}
                                                    onMouseEnter={(e) => {
                                                        e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
                                                    }}
                                                    onMouseLeave={(e) => {
                                                        e.currentTarget.style.background = 'transparent';
                                                    }}
                                                >
                                                    {isDeleting ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                                                    <span>Remove</span>
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* TAB 2: Fine-grained Q&A Editor */}
                {activeTab === 'editor' && (
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
                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
                                                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', fontWeight: '600' }}>
                                                        {item.category}
                                                    </span>
                                                    {item.source_doc && (
                                                        <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                                                            📄 {item.source_doc}
                                                        </span>
                                                    )}
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

                                    {draft.source_doc && (
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                            Source Document: <strong style={{ color: 'var(--text-primary)' }}>{draft.source_doc}</strong>
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
                                            onClick={handleSaveFaq}
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
                )}
            </div>
        </div>
    );
}
