import React, { useState, useEffect, useMemo } from 'react';
import {
    X,
    FolderClock,
    Clock,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Download,
    ExternalLink,
    RefreshCw,
    Search,
    Sparkles,
    Activity,
    FileAudio,
    FileText,
    Calendar,
    ChevronRight,
} from 'lucide-react';
import { apiJson, API_URL } from '../services/api';

export default function CreationsDrawer({ isOpen, onClose, onLoadJob }) {
    const [jobs, setJobs] = useState([]);
    const [activities, setActivities] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState('all'); // 'all' | 'timed_scripts' | 'activities'
    const [downloadingJobId, setDownloadingJobId] = useState(null);

    // Fetch jobs and activities whenever the drawer opens
    const fetchData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [jobsRes, actRes] = await Promise.allSettled([
                apiJson('/timed-script/jobs'),
                apiJson('/activity/me'),
            ]);

            if (jobsRes.status === 'fulfilled' && jobsRes.value?.jobs) {
                setJobs(jobsRes.value.jobs);
            }
            if (actRes.status === 'fulfilled' && actRes.value?.activities) {
                setActivities(actRes.value.activities);
            }
        } catch (err) {
            console.error('Failed to load past creations:', err);
            setError('Could not load creations. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchData();
        }
    }, [isOpen]);

    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && isOpen) {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    // Download DOCX handler for completed timed script
    const handleDownloadDocx = async (e, job) => {
        e.stopPropagation();
        if (!job.result) return;
        setDownloadingJobId(job.job_id);
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_URL}/timed-script/download-docx`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(job.result),
            });

            if (!response.ok) {
                throw new Error('Failed to generate DOCX');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${job.original_filename?.replace(/\.[^/.]+$/, '') || 'timed_script'}_timed_script.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download error:', err);
        } finally {
            setDownloadingJobId(null);
        }
    };

    const handleOpenInWorkspace = (job) => {
        if (onLoadJob) {
            onLoadJob(job);
        }
        onClose();
    };

    const formatDate = (isoString) => {
        if (!isoString) return '';
        try {
            const date = new Date(isoString);
            return date.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return isoString;
        }
    };

    // Filter items based on activeTab and searchQuery
    const filteredJobs = useMemo(() => {
        return jobs.filter((job) => {
            const query = searchQuery.toLowerCase();
            const matchName = (job.original_filename || '').toLowerCase().includes(query);
            const matchStatus = (job.status || '').toLowerCase().includes(query);
            return matchName || matchStatus;
        });
    }, [jobs, searchQuery]);

    const filteredActivities = useMemo(() => {
        return activities.filter((act) => {
            const query = searchQuery.toLowerCase();
            const matchType = (act.activity_type || '').toLowerCase().includes(query);
            const matchDetail = (act.detail || '').toLowerCase().includes(query);
            return matchType || matchDetail;
        });
    }, [activities, searchQuery]);

    if (!isOpen) return null;

    const totalCount = jobs.length + activities.length;

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 1500,
                display: 'flex',
                justifyContent: 'flex-end',
            }}
        >
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.55)',
                    backdropFilter: 'blur(3px)',
                    animation: 'fadeIn 0.2s ease-out',
                }}
            />

            {/* Slide-over Drawer Panel */}
            <div
                style={{
                    position: 'relative',
                    width: '100%',
                    maxWidth: '520px',
                    height: '100%',
                    background: 'var(--bg-secondary, #1e1e24)',
                    color: 'var(--text-primary, #ffffff)',
                    borderLeft: '1px solid var(--border-color, #2d2d38)',
                    boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.35)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 10,
                    animation: 'slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '1.25rem 1.5rem',
                        borderBottom: '1px solid var(--border-color, #2d2d38)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: 'var(--bg-tertiary, #252530)',
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
                            <FolderClock size={20} />
                        </div>
                        <div>
                            <h2 style={{ fontSize: '1.1rem', fontWeight: '600', margin: 0 }}>
                                My Creations & History
                            </h2>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #9ca3af)', margin: 0, marginTop: '2px' }}>
                                Access your generated scripts and recent activities
                            </p>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button
                            onClick={fetchData}
                            disabled={isLoading}
                            title="Refresh"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '32px',
                                height: '32px',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color, #2d2d38)',
                                background: 'transparent',
                                color: 'var(--text-secondary, #9ca3af)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.color = 'var(--text-primary, #ffffff)';
                                e.currentTarget.style.borderColor = 'var(--accent-primary, #6366f1)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.color = 'var(--text-secondary, #9ca3af)';
                                e.currentTarget.style.borderColor = 'var(--border-color, #2d2d38)';
                            }}
                        >
                            <RefreshCw size={15} className={isLoading ? 'spin' : ''} />
                        </button>
                        <button
                            onClick={onClose}
                            title="Close (Esc)"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '32px',
                                height: '32px',
                                borderRadius: '8px',
                                border: '1px solid var(--border-color, #2d2d38)',
                                background: 'transparent',
                                color: 'var(--text-secondary, #9ca3af)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.color = 'var(--text-primary, #ffffff)';
                                e.currentTarget.style.borderColor = 'var(--accent-primary, #6366f1)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.color = 'var(--text-secondary, #9ca3af)';
                                e.currentTarget.style.borderColor = 'var(--border-color, #2d2d38)';
                            }}
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Search & Filter Bar */}
                <div
                    style={{
                        padding: '1rem 1.5rem 0.75rem 1.5rem',
                        borderBottom: '1px solid var(--border-color, #2d2d38)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                        background: 'var(--bg-secondary, #1e1e24)',
                    }}
                >
                    {/* Search Input */}
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 0.75rem',
                            borderRadius: '8px',
                            background: 'var(--bg-primary, #141418)',
                            border: '1px solid var(--border-color, #2d2d38)',
                        }}
                    >
                        <Search size={16} style={{ color: 'var(--text-secondary, #9ca3af)' }} />
                        <input
                            type="text"
                            placeholder="Search creations or logs..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            style={{
                                flex: 1,
                                background: 'transparent',
                                border: 'none',
                                outline: 'none',
                                color: 'var(--text-primary, #ffffff)',
                                fontSize: '0.875rem',
                            }}
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: 'var(--text-secondary, #9ca3af)',
                                    cursor: 'pointer',
                                    padding: '2px',
                                }}
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>

                    {/* Filter Tabs */}
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {[
                            { id: 'all', label: 'All', count: totalCount },
                            { id: 'timed_scripts', label: 'Timed Scripts', count: jobs.length },
                            { id: 'activities', label: 'Activity Logs', count: activities.length },
                        ].map((tab) => {
                            const active = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.35rem',
                                        padding: '0.35rem 0.65rem',
                                        borderRadius: '6px',
                                        fontSize: '0.75rem',
                                        fontWeight: active ? '600' : '400',
                                        border: active ? '1px solid var(--accent-primary, #6366f1)' : '1px solid var(--border-color, #2d2d38)',
                                        background: active ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                                        color: active ? 'var(--accent-primary, #818cf8)' : 'var(--text-secondary, #9ca3af)',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s',
                                    }}
                                >
                                    <span>{tab.label}</span>
                                    <span
                                        style={{
                                            padding: '1px 5px',
                                            borderRadius: '10px',
                                            fontSize: '0.7rem',
                                            background: active ? 'var(--accent-primary, #6366f1)' : 'var(--bg-tertiary, #252530)',
                                            color: active ? '#fff' : 'var(--text-secondary, #9ca3af)',
                                        }}
                                    >
                                        {tab.count}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Items List Area */}
                <div
                    style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '1rem 1.5rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.85rem',
                    }}
                >
                    {isLoading ? (
                        <div
                            style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '240px',
                                color: 'var(--text-secondary, #9ca3af)',
                                gap: '0.75rem',
                            }}
                        >
                            <Loader2 size={28} className="spin" style={{ color: 'var(--accent-primary, #6366f1)' }} />
                            <span style={{ fontSize: '0.875rem' }}>Loading your creations...</span>
                        </div>
                    ) : error ? (
                        <div
                            style={{
                                padding: '1.25rem',
                                borderRadius: '8px',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                color: '#f87171',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                fontSize: '0.875rem',
                            }}
                        >
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </div>
                    ) : (
                        <>
                            {/* Section: Timed Scripts */}
                            {(activeTab === 'all' || activeTab === 'timed_scripts') && (
                                <>
                                    {activeTab === 'all' && filteredJobs.length > 0 && (
                                        <div
                                            style={{
                                                fontSize: '0.75rem',
                                                fontWeight: '600',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                                color: 'var(--text-secondary, #9ca3af)',
                                                marginTop: '0.25rem',
                                                marginBottom: '0.25rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                            }}
                                        >
                                            <FileAudio size={14} />
                                            <span>Timed Scripts ({filteredJobs.length})</span>
                                        </div>
                                    )}

                                    {filteredJobs.map((job) => {
                                        const isComplete = job.status === 'completed';
                                        const isProcessing = job.status === 'running' || job.status === 'queued';
                                        const isFailed = job.status === 'failed';
                                        const sentencesCount = job.result?.sentences?.length;
                                        const duration = job.result?.total_duration ? Math.round(job.result.total_duration) : null;

                                        return (
                                            <div
                                                key={job.job_id}
                                                style={{
                                                    borderRadius: '10px',
                                                    border: '1px solid var(--border-color, #2d2d38)',
                                                    background: 'var(--bg-primary, #141418)',
                                                    padding: '1rem',
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    gap: '0.75rem',
                                                    transition: 'border-color 0.2s',
                                                }}
                                            >
                                                {/* Card Header */}
                                                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                                                        <FileAudio size={18} style={{ color: 'var(--accent-primary, #818cf8)', flexShrink: 0 }} />
                                                        <div style={{ minWidth: 0 }}>
                                                            <div
                                                                style={{
                                                                    fontSize: '0.9rem',
                                                                    fontWeight: '600',
                                                                    color: 'var(--text-primary, #ffffff)',
                                                                    overflow: 'hidden',
                                                                    textOverflow: 'ellipsis',
                                                                    whiteSpace: 'nowrap',
                                                                }}
                                                                title={job.original_filename}
                                                            >
                                                                {job.original_filename || 'Timed Script Job'}
                                                            </div>
                                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '2px' }}>
                                                                <Calendar size={11} />
                                                                <span>{formatDate(job.created_at)}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Status Badge */}
                                                    <span
                                                        style={{
                                                            fontSize: '0.7rem',
                                                            padding: '2px 8px',
                                                            borderRadius: '999px',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.3rem',
                                                            fontWeight: '500',
                                                            flexShrink: 0,
                                                            background: isComplete ? 'rgba(34, 197, 94, 0.15)' : isProcessing ? 'rgba(234, 179, 8, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                                            color: isComplete ? '#4ade80' : isProcessing ? '#fde047' : '#f87171',
                                                            border: `1px solid ${isComplete ? 'rgba(34, 197, 94, 0.3)' : isProcessing ? 'rgba(234, 179, 8, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                                        }}
                                                    >
                                                        {isComplete && <CheckCircle2 size={12} />}
                                                        {isProcessing && <Loader2 size={12} className="spin" />}
                                                        {isFailed && <AlertCircle size={12} />}
                                                        <span style={{ textTransform: 'capitalize' }}>{job.status}</span>
                                                    </span>
                                                </div>

                                                {/* Stats / Info */}
                                                {isComplete && (sentencesCount || duration) && (
                                                    <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary, #9ca3af)' }}>
                                                        {sentencesCount !== undefined && (
                                                            <span style={{ background: 'var(--bg-tertiary, #252530)', padding: '2px 6px', borderRadius: '4px' }}>
                                                                {sentencesCount} sentences
                                                            </span>
                                                        )}
                                                        {duration !== null && (
                                                            <span style={{ background: 'var(--bg-tertiary, #252530)', padding: '2px 6px', borderRadius: '4px' }}>
                                                                {duration}s duration
                                                            </span>
                                                        )}
                                                    </div>
                                                )}

                                                {/* Action Buttons */}
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'flex-end',
                                                        gap: '0.5rem',
                                                        paddingTop: '0.25rem',
                                                        borderTop: '1px solid var(--border-color, #2d2d38)',
                                                    }}
                                                >
                                                    {isComplete && job.result && (
                                                        <button
                                                            onClick={(e) => handleDownloadDocx(e, job)}
                                                            disabled={downloadingJobId === job.job_id}
                                                            style={{
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '0.35rem',
                                                                padding: '0.4rem 0.75rem',
                                                                borderRadius: '6px',
                                                                fontSize: '0.75rem',
                                                                background: 'var(--bg-tertiary, #252530)',
                                                                border: '1px solid var(--border-color, #2d2d38)',
                                                                color: 'var(--text-primary, #ffffff)',
                                                                cursor: 'pointer',
                                                                transition: 'all 0.15s',
                                                            }}
                                                            onMouseEnter={(e) => {
                                                                e.currentTarget.style.borderColor = 'var(--accent-primary, #6366f1)';
                                                            }}
                                                            onMouseLeave={(e) => {
                                                                e.currentTarget.style.borderColor = 'var(--border-color, #2d2d38)';
                                                            }}
                                                        >
                                                            {downloadingJobId === job.job_id ? (
                                                                <Loader2 size={13} className="spin" />
                                                            ) : (
                                                                <Download size={13} />
                                                            )}
                                                            <span>DOCX</span>
                                                        </button>
                                                    )}

                                                    <button
                                                        onClick={() => handleOpenInWorkspace(job)}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.35rem',
                                                            padding: '0.4rem 0.85rem',
                                                            borderRadius: '6px',
                                                            fontSize: '0.75rem',
                                                            fontWeight: '500',
                                                            background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
                                                            border: 'none',
                                                            color: '#ffffff',
                                                            cursor: 'pointer',
                                                            transition: 'opacity 0.15s',
                                                        }}
                                                        onMouseEnter={(e) => {
                                                            e.currentTarget.style.opacity = '0.9';
                                                        }}
                                                        onMouseLeave={(e) => {
                                                            e.currentTarget.style.opacity = '1';
                                                        }}
                                                    >
                                                        <ExternalLink size={13} />
                                                        <span>Open in Workspace</span>
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </>
                            )}

                            {/* Section: Activity Logs */}
                            {(activeTab === 'all' || activeTab === 'activities') && (
                                <>
                                    {activeTab === 'all' && filteredActivities.length > 0 && (
                                        <div
                                            style={{
                                                fontSize: '0.75rem',
                                                fontWeight: '600',
                                                textTransform: 'uppercase',
                                                letterSpacing: '0.05em',
                                                color: 'var(--text-secondary, #9ca3af)',
                                                marginTop: '0.5rem',
                                                marginBottom: '0.25rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                            }}
                                        >
                                            <Activity size={14} />
                                            <span>Recent Activity ({filteredActivities.length})</span>
                                        </div>
                                    )}

                                    {filteredActivities.map((act) => (
                                        <div
                                            key={act.id}
                                            style={{
                                                borderRadius: '8px',
                                                border: '1px solid var(--border-color, #2d2d38)',
                                                background: 'var(--bg-primary, #141418)',
                                                padding: '0.75rem 1rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between',
                                                gap: '0.75rem',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', minWidth: 0 }}>
                                                <div
                                                    style={{
                                                        width: '28px',
                                                        height: '28px',
                                                        borderRadius: '6px',
                                                        background: 'var(--bg-tertiary, #252530)',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        color: 'var(--accent-primary, #818cf8)',
                                                        flexShrink: 0,
                                                    }}
                                                >
                                                    <Activity size={14} />
                                                </div>
                                                <div style={{ minWidth: 0 }}>
                                                    <div
                                                        style={{
                                                            fontSize: '0.85rem',
                                                            fontWeight: '500',
                                                            color: 'var(--text-primary, #ffffff)',
                                                            overflow: 'hidden',
                                                            textOverflow: 'ellipsis',
                                                            whiteSpace: 'nowrap',
                                                        }}
                                                    >
                                                        {act.detail || act.activity_type}
                                                    </div>
                                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', marginTop: '2px' }}>
                                                        {formatDate(act.created_at)}
                                                    </div>
                                                </div>
                                            </div>

                                            {act.status && (
                                                <span
                                                    style={{
                                                        fontSize: '0.7rem',
                                                        padding: '2px 6px',
                                                        borderRadius: '4px',
                                                        background: act.status === 'success' || act.status === 'completed' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                                                        color: act.status === 'success' || act.status === 'completed' ? '#4ade80' : '#fde047',
                                                        textTransform: 'capitalize',
                                                        flexShrink: 0,
                                                    }}
                                                >
                                                    {act.status}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </>
                            )}

                            {/* Empty State */}
                            {filteredJobs.length === 0 && filteredActivities.length === 0 && (
                                <div
                                    style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        height: '240px',
                                        textAlign: 'center',
                                        color: 'var(--text-secondary, #9ca3af)',
                                        gap: '0.5rem',
                                    }}
                                >
                                    <FolderClock size={36} style={{ opacity: 0.4 }} />
                                    <div style={{ fontSize: '0.95rem', fontWeight: '500', color: 'var(--text-primary, #ffffff)' }}>
                                        {searchQuery ? 'No matching creations found' : 'No creations yet'}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', maxWidth: '280px' }}>
                                        {searchQuery
                                            ? 'Try searching with a different keyword.'
                                            : 'Generate timed scripts or tutorials to see your history and creations here.'}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
