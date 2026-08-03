import { useState } from 'react';
import { Check } from 'lucide-react';
import {
    DEFAULT_THEME_COLOR,
    THEME_PALETTE,
    getThemeColor,
    isValidThemeColor,
    normalizeThemeColor,
    setThemeColor,
} from '../utils/slideTheme';

/**
 * Colour picker for generated Beamer slides.
 *
 * The choice is stored in localStorage and read by the /generate_slides
 * callers, so this component owns its own state rather than being driven
 * by props threaded through the sidebar.
 */
const SlideThemePicker = ({ isOpen }) => {
    const [color, setColor] = useState(getThemeColor);

    const applyColor = (value) => {
        if (!isValidThemeColor(value)) return;
        const normalized = normalizeThemeColor(value);
        setThemeColor(normalized);
        setColor(normalized);
    };

    const isCustom = !THEME_PALETTE.some((entry) => entry.hex.toUpperCase() === color);

    if (!isOpen) {
        // Collapsed sidebar: just show the active colour.
        return (
            <div
                title={`Slide colour ${color}`}
                style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: color,
                    border: '1px solid var(--border-color)',
                    margin: '0.5rem auto',
                }}
            />
        );
    }

    return (
        <div style={{ padding: '0.5rem 0.75rem 0.75rem' }}>
            <div
                style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    marginBottom: '0.5rem',
                }}
            >
                Slide colour
            </div>

            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '0.4rem',
                }}
            >
                {THEME_PALETTE.map((entry) => {
                    const selected = entry.hex.toUpperCase() === color;
                    return (
                        <button
                            key={entry.hex}
                            type="button"
                            onClick={() => applyColor(entry.hex)}
                            title={`${entry.name} ${entry.hex}`}
                            aria-label={entry.name}
                            aria-pressed={selected}
                            style={{
                                height: '28px',
                                borderRadius: '0.4rem',
                                background: entry.hex,
                                border: selected
                                    ? '2px solid var(--text-primary)'
                                    : '1px solid var(--border-color)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                padding: 0,
                            }}
                        >
                            {selected && <Check size={14} color="#FFFFFF" aria-hidden="true" />}
                        </button>
                    );
                })}
            </div>

            <label
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginTop: '0.6rem',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                }}
            >
                <input
                    type="color"
                    value={color}
                    onChange={(e) => applyColor(e.target.value)}
                    aria-label="Custom slide colour"
                    style={{
                        width: '28px',
                        height: '28px',
                        padding: 0,
                        border: isCustom
                            ? '2px solid var(--text-primary)'
                            : '1px solid var(--border-color)',
                        borderRadius: '0.4rem',
                        background: 'transparent',
                        cursor: 'pointer',
                    }}
                />
                <span style={{ fontFamily: 'monospace' }}>{color}</span>
                {color !== DEFAULT_THEME_COLOR && (
                    <button
                        type="button"
                        onClick={() => applyColor(DEFAULT_THEME_COLOR)}
                        style={{
                            marginLeft: 'auto',
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            padding: 0,
                        }}
                    >
                        Reset
                    </button>
                )}
            </label>
        </div>
    );
};

export default SlideThemePicker;
