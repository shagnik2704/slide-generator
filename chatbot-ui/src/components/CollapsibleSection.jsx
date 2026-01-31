import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * CollapsibleSection - A reusable collapsible wrapper for workflow components
 * Helps reduce scrolling by allowing users to collapse sections they're not actively using.
 */
const CollapsibleSection = ({
    title,
    subtitle,
    icon,
    defaultOpen = true,
    children
}) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    const headerStyle = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.875rem 1.25rem',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        marginTop: '1rem',
    };

    const titleContainerStyle = {
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
    };

    const titleStyle = {
        fontWeight: 600,
        fontSize: '0.95rem',
        color: 'var(--text-primary)',
    };

    const subtitleStyle = {
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
        marginLeft: '0.5rem',
    };

    const chevronStyle = {
        color: 'var(--text-secondary)',
        transition: 'transform 0.2s ease',
    };

    const contentWrapperStyle = {
        // Minimal wrapper - let child components define their own size and styling
    };

    return (
        <div>
            <div
                style={headerStyle}
                onClick={() => setIsOpen(!isOpen)}
                onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'var(--bg-secondary)';
                }}
            >
                <div style={titleContainerStyle}>
                    {icon && <span style={{ display: 'flex', alignItems: 'center', color: 'var(--accent-primary)' }}>{icon}</span>}
                    <span style={titleStyle}>{title}</span>
                    {subtitle && <span style={subtitleStyle}>• {subtitle}</span>}
                </div>
                <div style={chevronStyle}>
                    {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
            </div>

            {isOpen && (
                <div style={contentWrapperStyle}>
                    {children}
                </div>
            )}
        </div>
    );
};

export default CollapsibleSection;
