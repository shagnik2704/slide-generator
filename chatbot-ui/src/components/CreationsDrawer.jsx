import React, { useState, useEffect, useMemo } from 'react';
import {
    X,
    FolderClock,
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
    Presentation,
    Mic,
    Video,
    Play,
} from 'lucide-react';
import { apiJson, API_URL } from '../services/api';

function formatDuration(val, secondsVal) {
    if (typeof val === 'string' && val.trim().length > 0) {
        if (val.includes(':')) {
            const parts = val.split(':');
            if (parts.length === 2) {
                const mins = parseInt(parts[0], 10);
                const secs = parseInt(parts[1], 10);
                return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
            }
            return val;
        }
        const num = parseFloat(val);
        if (!isNaN(num)) return `${Math.round(num)}s`;
        return val;
    }
    if (typeof val === 'number' && !isNaN(val)) {
        return `${Math.round(val)}s`;
    }
    if (typeof secondsVal === 'number' && !isNaN(secondsVal)) {
        const m = Math.floor(secondsVal / 60);
        const s = Math.round(secondsVal % 60);
        return m > 0 ? `${m}m ${s}s` : `${s}s`;
    }
    return null;
}

function formatDate(isoString) {
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
}

function getActivityIcon(type) {
    switch (type) {
        case 'timed_script':
            return <FileAudio size={14} />;
        case 'script_chat':
        case 'generate_script':
        case 'export_docx':
        case 'export_wiki':
            return <FileText size={14} />;
        case 'slide_generation':
        case 'slides_generation':
            return <Presentation size={14} />;
        case 'voice_generation':
        case 'voice_generation_combined':
        case 'voice_patch':
        case 'regenerate_slide':
            return <Mic size={14} />;
        case 'generate_video':
            return <Video size={14} />;
        default:
            return <Activity size={14} />;
    }
}

export default function CreationsDrawer({ isOpen, onClose, onLoadJob }) {
    const [timedScripts, setTimedScripts] = useState([]);
    const [scripts, setScripts] = useState([]);
    const [slides, setSlides] = useState([]);
    const [audio, setAudio] = useState([]);
    const [videos, setVideos] = useState([]);
    const [activities, setActivities] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState('all');
    const [downloadingDocxId, setDownloadingDocxId] = useState(null);

    // Fetch creations and activities whenever the drawer opens
    const fetchData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [creationsRes, actRes] = await Promise.allSettled([
                apiJson('/activity/creations'),
                apiJson('/activity/me'),
            ]);

            if (creationsRes.status === 'fulfilled' && creationsRes.value?.creations) {
                const c = creationsRes.value.creations;
                setTimedScripts(c.timed_scripts || []);
                setScripts(c.scripts || []);
                setSlides(c.slides || []);
                setAudio(c.audio || []);
                setVideos(c.videos || []);
            } else {
                // Fallback to /timed-script/jobs if /activity/creations is not supported
                const fallbackJobs = await apiJson('/timed-script/jobs').catch(() => ({ jobs: [] }));
                if (fallbackJobs?.jobs) setTimedScripts(fallbackJobs.jobs);
            }

            if (actRes.status === 'fulfilled' && actRes.value?.activities) {
                setActivities(actRes.value.activities);
            }
        } catch (err) {
            console.error('Failed to load creations and activities:', err);
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
    const handleDownloadTimedDocx = async (e, job) => {
        e.stopPropagation();
        if (!job.result) return;
        const targetId = job.job_id || job.id;
        setDownloadingDocxId(targetId);
        try {
            const token = localStorage.getItem('auth_token');
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
            setDownloadingDocxId(null);
        }
    };

    // Download DOCX for script chat thread
    const handleDownloadScriptDocx = async (e, script) => {
        e.stopPropagation();
        const threadId = script.thread_id || script.id;
        setDownloadingDocxId(threadId);
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(`${API_URL}/script-chat/export-docx/${threadId}`, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
            });
            if (!response.ok) throw new Error('Failed to export DOCX');
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${script.foss_name || script.title || 'tutorial'}_script.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Script DOCX download error:', err);
        } finally {
            setDownloadingDocxId(null);
        }
    };

    const handleOpenInWorkspace = (job) => {
        if (onLoadJob) {
            onLoadJob(job);
        }
        onClose();
    };

    const handleOpenScriptChat = (script) => {
        const threadId = script.thread_id || script.id;
        window.location.href = `/script-chat?thread_id=${threadId}`;
    };

    const handleOpenUrl = (e, targetUrl) => {
        e.stopPropagation();
        if (!targetUrl) return;
        const fullUrl = targetUrl.startsWith('http') ? targetUrl : `${API_URL}${targetUrl.startsWith('/') ? '' : '/'}${targetUrl}`;
        window.open(fullUrl, '_blank');
    };

    // Search filters
    const query = searchQuery.toLowerCase().trim();

    const filteredTimedScripts = useMemo(() => {
        if (!query) return timedScripts;
        return timedScripts.filter((job) =>
            (job.original_filename || '').toLowerCase().includes(query) ||
            (job.status || '').toLowerCase().includes(query)
        );
    }, [timedScripts, query]);

    const filteredScripts = useMemo(() => {
        if (!query) return scripts;
        return scripts.filter((s) =>
            (s.title || '').toLowerCase().includes(query) ||
            (s.foss_name || '').toLowerCase().includes(query) ||
            (s.current_stage || '').toLowerCase().includes(query) ||
            (s.status || '').toLowerCase().includes(query)
        );
    }, [scripts, query]);

    const filteredSlides = useMemo(() => {
        if (!query) return slides;
        return slides.filter((s) =>
            (s.detail || '').toLowerCase().includes(query) ||
            (s.status || '').toLowerCase().includes(query)
        );
    }, [slides, query]);

    const filteredAudio = useMemo(() => {
        if (!query) return audio;
        return audio.filter((a) =>
            (a.detail || '').toLowerCase().includes(query) ||
            (a.status || '').toLowerCase().includes(query)
        );
    }, [audio, query]);

    const filteredVideos = useMemo(() => {
        if (!query) return videos;
        return videos.filter((v) =>
            (v.detail || '').toLowerCase().includes(query) ||
            (v.status || '').toLowerCase().includes(query)
        );
    }, [videos, query]);

    const filteredActivities = useMemo(() => {
        if (!query) return activities;
        return activities.filter((act) =>
            (act.activity_type || '').toLowerCase().includes(query) ||
            (act.detail || '').toLowerCase().includes(query) ||
            (act.status || '').toLowerCase().includes(query)
        );
    }, [activities, query]);

    if (!isOpen) return null;

    const totalCreationsCount = timedScripts.length + scripts.length + slides.length + audio.length + videos.length;
    const totalCount = totalCreationsCount + activities.length;

    const tabs = [
        { id: 'all', label: 'All', count: totalCount },
        { id: 'timed_scripts', label: 'Timed Scripts', count: timedScripts.length },
        { id: 'scripts', label: 'Tutorial Scripts', count: scripts.length },
        { id: 'slides', label: 'Slide Decks', count: slides.length },
        { id: 'audio', label: 'Voice & Audio', count: audio.length },
        { id: 'activities', label: 'Activity Logs', count: activities.length },
    ];

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
                    <div
                        style={{
                            display: 'flex',
                            gap: '0.5rem',
                            overflowX: 'auto',
                            paddingBottom: '4px',
                            scrollbarWidth: 'none',
                        }}
                    >
                        {tabs.map((tab) => {
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
                                        whiteSpace: 'nowrap',
                                        flexShrink: 0,
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
                                    {activeTab === 'all' && filteredTimedScripts.length > 0 && (
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
                                            <span>Timed Scripts ({filteredTimedScripts.length})</span>
                                        </div>
                                    )}

                                    {filteredTimedScripts.map((job) => {
                                        const isComplete = job.status === 'completed';
                                        const isProcessing = job.status === 'running' || job.status === 'queued';
                                        const isFailed = job.status === 'failed';
                                        const sentencesCount = job.result?.sentences?.length;
                                        const durationText = formatDuration(job.result?.total_duration);
                                        const jobId = job.job_id || job.id;

                                        return (
                                            <div
                                                key={jobId}
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
                                                                {job.original_filename || 'Timed Script'}
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
                                                {isComplete && (sentencesCount || durationText) && (
                                                    <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary, #9ca3af)' }}>
                                                        {sentencesCount !== undefined && (
                                                            <span style={{ background: 'var(--bg-tertiary, #252530)', padding: '2px 6px', borderRadius: '4px' }}>
                                                                {sentencesCount} sentences
                                                            </span>
                                                        )}
                                                        {durationText && (
                                                            <span style={{ background: 'var(--bg-tertiary, #252530)', padding: '2px 6px', borderRadius: '4px' }}>
                                                                {durationText} duration
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
                                                            onClick={(e) => handleDownloadTimedDocx(e, job)}
                                                            disabled={downloadingDocxId === jobId}
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
                                                            {downloadingDocxId === jobId ? (
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

                            {/* Section: Tutorial Scripts (Script Chat) */}
                            {(activeTab === 'all' || activeTab === 'scripts') && (
                                <>
                                    {activeTab === 'all' && filteredScripts.length > 0 && (
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
                                            <FileText size={14} />
                                            <span>Tutorial Scripts ({filteredScripts.length})</span>
                                        </div>
                                    )}

                                    {filteredScripts.map((script) => {
                                        const scriptId = script.thread_id || script.id;
                                        return (
                                            <div
                                                key={scriptId}
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
                                                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                                                        <FileText size={18} style={{ color: '#10b981', flexShrink: 0 }} />
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
                                                                title={script.title || script.foss_name}
                                                            >
                                                                {script.title || script.foss_name || 'Tutorial Script'}
                                                            </div>
                                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '2px' }}>
                                                                <Calendar size={11} />
                                                                <span>{formatDate(script.created_at || script.updated_at)}</span>
                                                                {script.foss_name && (
                                                                    <span style={{ marginLeft: '4px', color: '#818cf8' }}>• {script.foss_name}</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {script.current_stage && (
                                                        <span
                                                            style={{
                                                                fontSize: '0.7rem',
                                                                padding: '2px 8px',
                                                                borderRadius: '999px',
                                                                background: 'rgba(16, 185, 129, 0.15)',
                                                                color: '#34d399',
                                                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                                                textTransform: 'capitalize',
                                                                flexShrink: 0,
                                                            }}
                                                        >
                                                            {script.current_stage.replace(/_/g, ' ')}
                                                        </span>
                                                    )}
                                                </div>

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
                                                    <button
                                                        onClick={(e) => handleDownloadScriptDocx(e, script)}
                                                        disabled={downloadingDocxId === scriptId}
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
                                                            e.currentTarget.style.borderColor = '#10b981';
                                                        }}
                                                        onMouseLeave={(e) => {
                                                            e.currentTarget.style.borderColor = 'var(--border-color, #2d2d38)';
                                                        }}
                                                    >
                                                        {downloadingDocxId === scriptId ? (
                                                            <Loader2 size={13} className="spin" />
                                                        ) : (
                                                            <Download size={13} />
                                                        )}
                                                        <span>DOCX</span>
                                                    </button>

                                                    <button
                                                        onClick={() => handleOpenScriptChat(script)}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.35rem',
                                                            padding: '0.4rem 0.85rem',
                                                            borderRadius: '6px',
                                                            fontSize: '0.75rem',
                                                            fontWeight: '500',
                                                            background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
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
                                                        <span>Open in Script Chat</span>
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </>
                            )}

                            {/* Section: Slide Decks */}
                            {(activeTab === 'all' || activeTab === 'slides') && (
                                <>
                                    {activeTab === 'all' && filteredSlides.length > 0 && (
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
                                            <Presentation size={14} />
                                            <span>Slide Decks ({filteredSlides.length})</span>
                                        </div>
                                    )}

                                    {filteredSlides.map((slide) => (
                                        <div
                                            key={slide.id}
                                            style={{
                                                borderRadius: '10px',
                                                border: '1px solid var(--border-color, #2d2d38)',
                                                background: 'var(--bg-primary, #141418)',
                                                padding: '1rem',
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.75rem',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                                                    <Presentation size={18} style={{ color: '#a855f7', flexShrink: 0 }} />
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
                                                            title={slide.title || slide.detail}
                                                        >
                                                            {slide.title || slide.detail || 'Slide Presentation'}
                                                        </div>
                                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '2px' }}>
                                                            <Calendar size={11} />
                                                            <span>{formatDate(slide.created_at)}</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {slide.slide_count && (
                                                    <span
                                                        style={{
                                                            fontSize: '0.7rem',
                                                            padding: '2px 8px',
                                                            borderRadius: '999px',
                                                            background: 'rgba(168, 85, 247, 0.15)',
                                                            color: '#c084fc',
                                                            border: '1px solid rgba(168, 85, 247, 0.3)',
                                                            flexShrink: 0,
                                                        }}
                                                    >
                                                        {slide.slide_count} slides
                                                    </span>
                                                )}
                                            </div>

                                            {(slide.download_url || slide.url) && (
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'flex-end',
                                                        paddingTop: '0.25rem',
                                                        borderTop: '1px solid var(--border-color, #2d2d38)',
                                                    }}
                                                >
                                                    <button
                                                        onClick={(e) => handleOpenUrl(e, slide.download_url || slide.url)}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.35rem',
                                                            padding: '0.4rem 0.85rem',
                                                            borderRadius: '6px',
                                                            fontSize: '0.75rem',
                                                            fontWeight: '500',
                                                            background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
                                                            border: 'none',
                                                            color: '#ffffff',
                                                            cursor: 'pointer',
                                                        }}
                                                    >
                                                        <Download size={13} />
                                                        <span>Download Slides</span>
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </>
                            )}

                            {/* Section: Voice & Audio */}
                            {(activeTab === 'all' || activeTab === 'audio') && (
                                <>
                                    {activeTab === 'all' && filteredAudio.length > 0 && (
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
                                            <Mic size={14} />
                                            <span>Voice & Audio ({filteredAudio.length})</span>
                                        </div>
                                    )}

                                    {filteredAudio.map((aud) => {
                                        const dur = formatDuration(aud.duration);
                                        return (
                                            <div
                                                key={aud.id}
                                                style={{
                                                    borderRadius: '10px',
                                                    border: '1px solid var(--border-color, #2d2d38)',
                                                    background: 'var(--bg-primary, #141418)',
                                                    padding: '1rem',
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    gap: '0.75rem',
                                                }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                                                        <Mic size={18} style={{ color: '#ec4899', flexShrink: 0 }} />
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
                                                                title={aud.title || aud.detail}
                                                            >
                                                                {aud.title || aud.detail || 'Voice Narration'}
                                                            </div>
                                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '2px' }}>
                                                                <Calendar size={11} />
                                                                <span>{formatDate(aud.created_at)}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {dur && (
                                                        <span
                                                            style={{
                                                                fontSize: '0.7rem',
                                                                padding: '2px 8px',
                                                                borderRadius: '999px',
                                                                background: 'rgba(236, 72, 153, 0.15)',
                                                                color: '#f472b6',
                                                                border: '1px solid rgba(236, 72, 153, 0.3)',
                                                                flexShrink: 0,
                                                            }}
                                                        >
                                                            {dur}
                                                        </span>
                                                    )}
                                                </div>

                                                {(aud.audio_url || aud.url) && (
                                                    <div
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'flex-end',
                                                            paddingTop: '0.25rem',
                                                            borderTop: '1px solid var(--border-color, #2d2d38)',
                                                        }}
                                                    >
                                                        <button
                                                            onClick={(e) => handleOpenUrl(e, aud.audio_url || aud.url)}
                                                            style={{
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '0.35rem',
                                                                padding: '0.4rem 0.85rem',
                                                                borderRadius: '6px',
                                                                fontSize: '0.75rem',
                                                                fontWeight: '500',
                                                                background: 'linear-gradient(135deg, #db2777 0%, #ec4899 100%)',
                                                                border: 'none',
                                                                color: '#ffffff',
                                                                cursor: 'pointer',
                                                            }}
                                                        >
                                                            <Play size={13} />
                                                            <span>Play / Audio</span>
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </>
                            )}

                            {/* Section: Videos */}
                            {(activeTab === 'all' || activeTab === 'videos') && (
                                <>
                                    {activeTab === 'all' && filteredVideos.length > 0 && (
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
                                            <Video size={14} />
                                            <span>Videos ({filteredVideos.length})</span>
                                        </div>
                                    )}

                                    {filteredVideos.map((vid) => (
                                        <div
                                            key={vid.id}
                                            style={{
                                                borderRadius: '10px',
                                                border: '1px solid var(--border-color, #2d2d38)',
                                                background: 'var(--bg-primary, #141418)',
                                                padding: '1rem',
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.75rem',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                                                    <Video size={18} style={{ color: '#3b82f6', flexShrink: 0 }} />
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
                                                            title={vid.title || vid.detail}
                                                        >
                                                            {vid.title || vid.detail || 'Generated Video'}
                                                        </div>
                                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #9ca3af)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '2px' }}>
                                                            <Calendar size={11} />
                                                            <span>{formatDate(vid.created_at)}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            {(vid.video_url || vid.url) && (
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'flex-end',
                                                        paddingTop: '0.25rem',
                                                        borderTop: '1px solid var(--border-color, #2d2d38)',
                                                    }}
                                                >
                                                    <button
                                                        onClick={(e) => handleOpenUrl(e, vid.video_url || vid.url)}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.35rem',
                                                            padding: '0.4rem 0.85rem',
                                                            borderRadius: '6px',
                                                            fontSize: '0.75rem',
                                                            fontWeight: '500',
                                                            background: 'linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)',
                                                            border: 'none',
                                                            color: '#ffffff',
                                                            cursor: 'pointer',
                                                        }}
                                                    >
                                                        <ExternalLink size={13} />
                                                        <span>Watch Video</span>
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    ))}
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
                                                    {getActivityIcon(act.activity_type)}
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
                            {(filteredTimedScripts.length === 0 &&
                                filteredScripts.length === 0 &&
                                filteredSlides.length === 0 &&
                                filteredAudio.length === 0 &&
                                filteredVideos.length === 0 &&
                                filteredActivities.length === 0) && (
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
                                            : 'Generate scripts, timed recordings, or slide decks to see your creations here.'}
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
