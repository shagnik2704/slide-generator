import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, Settings, LogOut, FolderOpen, Clock } from 'lucide-react';

// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const Sidebar = ({ isOpen }) => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            fetchProjects();
        }
    }, [isOpen]);

    const fetchProjects = async () => {
        try {
            const response = await fetch(`${API_URL}/projects`);
            if (response.ok) {
                const data = await response.json();
                setProjects(data);
            }
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        const colors = {
            'completed': '#10b981',
            'generating_video': '#3b82f6',
            'slides_ready': '#8b5cf6',
            'script_ready': '#f59e0b',
            'draft': '#6b7280',
            'failed': '#ef4444'
        };
        return colors[status] || '#6b7280';
    };

    const getStatusLabel = (status) => {
        const labels = {
            'generating_script': 'Generating Script',
            'script_ready': 'Script Ready',
            'generating_slides': 'Generating Slides',
            'slides_ready': 'Slides Ready',
            'generating_video': 'Generating Video',
            'completed': 'Completed',
            'failed': 'Failed',
            'draft': 'Draft'
        };
        return labels[status] || status;
    };

    return (
        <aside style={{
            width: isOpen ? '300px' : '0',
            opacity: isOpen ? 1 : 0,
            visibility: isOpen ? 'visible' : 'hidden',
            backgroundColor: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            padding: isOpen ? '1rem' : '0',
            flexShrink: 0,
            transition: 'all 0.3s ease-in-out',
            overflow: 'hidden',
            whiteSpace: 'nowrap'
        }}>
            <button className="btn-primary" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                width: '100%',
                justifyContent: 'center',
                marginBottom: '1.5rem'
            }}
                onClick={() => window.location.reload()}
            >
                <Plus size={18} />
                <span>New Project</span>
            </button>

            <div style={{ flex: 1, overflowY: 'auto' }}>
                <div style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.75rem',
                    paddingLeft: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                }}>
                    <FolderOpen size={14} />
                    {loading ? 'Loading...' : `Projects (${projects.length})`}
                </div>

                {loading ? (
                    <div style={{
                        padding: '1rem',
                        textAlign: 'center',
                        color: 'var(--text-secondary)',
                        fontSize: '0.9rem'
                    }}>
                        Loading projects...
                    </div>
                ) : projects.length === 0 ? (
                    <div style={{
                        padding: '1rem',
                        textAlign: 'center',
                        color: 'var(--text-secondary)',
                        fontSize: '0.85rem'
                    }}>
                        No projects yet
                    </div>
                ) : (
                    projects.map((project) => (
                        <div key={project.id} style={{
                            padding: '0.75rem',
                            marginBottom: '0.5rem',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '0.5rem',
                            border: '1px solid var(--border-color)',
                            transition: 'all 0.2s'
                        }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'var(--bg-primary)';
                                e.currentTarget.style.borderColor = 'var(--accent-primary)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'var(--bg-tertiary)';
                                e.currentTarget.style.borderColor = 'var(--border-color)';
                            }}
                        >
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                marginBottom: '0.5rem'
                            }}>
                                <MessageSquare size={14} color="var(--text-secondary)" />
                                <span style={{
                                    fontSize: '0.85rem',
                                    fontWeight: 600,
                                    color: 'var(--text-primary)',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis'
                                }}>
                                    Project #{project.id}
                                </span>
                            </div>
                            <div style={{
                                fontSize: '0.75rem',
                                color: 'var(--text-secondary)',
                                marginBottom: '0.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem'
                            }}>
                                <Clock size={12} />
                                {new Date(project.created_at).toLocaleDateString()}
                            </div>
                            <div style={{
                                display: 'inline-block',
                                padding: '0.25rem 0.5rem',
                                background: getStatusColor(project.status) + '20',
                                color: getStatusColor(project.status),
                                borderRadius: '0.25rem',
                                fontSize: '0.7rem',
                                fontWeight: 600
                            }}>
                                {getStatusLabel(project.status)}
                            </div>
                        </div>
                    ))
                )}
            </div>

            <div style={{
                borderTop: '1px solid var(--border-color)',
                paddingTop: '1rem',
                marginTop: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                <button className="btn-icon" style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}>
                    <Settings size={18} />
                    <span>Settings</span>
                </button>
                <button className="btn-icon" style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem' }}>
                    <LogOut size={18} />
                    <span>Log out</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
