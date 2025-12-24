import React, { useState } from 'react';

const Tooltip = ({ children, text, position = 'right' }) => {
    const [isVisible, setIsVisible] = useState(false);

    const tooltipStyle = {
        position: 'absolute',
        backgroundColor: 'var(--bg-tertiary)',
        color: 'var(--text-primary)',
        padding: '0.5rem 0.75rem',
        borderRadius: '0.5rem',
        fontSize: '0.8rem',
        fontWeight: 500,
        whiteSpace: 'nowrap',
        zIndex: 1000,
        border: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-lg)',
        opacity: isVisible ? 1 : 0,
        visibility: isVisible ? 'visible' : 'hidden',
        transition: 'opacity 0.15s ease, visibility 0.15s ease',
        pointerEvents: 'none',
        // Position based on prop
        ...(position === 'right' && {
            left: 'calc(100% + 10px)',
            top: '50%',
            transform: 'translateY(-50%)',
        }),
        ...(position === 'bottom' && {
            top: 'calc(100% + 8px)',
            left: '50%',
            transform: 'translateX(-50%)',
        }),
        ...(position === 'top' && {
            bottom: 'calc(100% + 8px)',
            left: '50%',
            transform: 'translateX(-50%)',
        }),
    };

    const arrowStyle = {
        position: 'absolute',
        width: 0,
        height: 0,
        ...(position === 'right' && {
            left: '-6px',
            top: '50%',
            transform: 'translateY(-50%)',
            borderTop: '6px solid transparent',
            borderBottom: '6px solid transparent',
            borderRight: '6px solid var(--bg-tertiary)',
        }),
        ...(position === 'bottom' && {
            top: '-6px',
            left: '50%',
            transform: 'translateX(-50%)',
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderBottom: '6px solid var(--bg-tertiary)',
        }),
        ...(position === 'top' && {
            bottom: '-6px',
            left: '50%',
            transform: 'translateX(-50%)',
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderTop: '6px solid var(--bg-tertiary)',
        }),
    };

    return (
        <div
            style={{ position: 'relative', display: 'inline-block', width: '100%' }}
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            {children}
            <div style={tooltipStyle}>
                <div style={arrowStyle} />
                {text}
            </div>
        </div>
    );
};

export default Tooltip;

