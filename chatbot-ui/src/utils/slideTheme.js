// Slide theme colour preference, persisted across sessions.
// The colour drives frame titles, bullets and title-slide accents in the
// generated Beamer deck (\setbeamercolor{structure}).

const STORAGE_KEY = 'spokentutorial_slide_theme_color';

export const DEFAULT_THEME_COLOR = '#708094';

// Contrast ratios are against a white slide background. The default slate is
// the weakest of the set (4.0:1, AA for large text only); the rest clear 4.5:1.
export const THEME_PALETTE = [
    { name: 'Slate', hex: '#708094' },
    { name: 'Charcoal', hex: '#37474F' },
    { name: 'Deep blue', hex: '#1F4E79' },
    { name: 'Teal', hex: '#0F6E6E' },
    { name: 'Forest', hex: '#2E6B4F' },
    { name: 'Maroon', hex: '#8C2F39' },
    { name: 'Plum', hex: '#6B3FA0' },
    { name: 'Burnt orange', hex: '#B5561F' },
];

const HEX_COLOR = /^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;

export const isValidThemeColor = (value) =>
    typeof value === 'string' && HEX_COLOR.test(value.trim());

/**
 * Normalise to #RRGGBB. `<input type="color">` and the swatch comparison both
 * need the 6-digit form, so #abc is expanded rather than stored as-is.
 */
export const normalizeThemeColor = (value) => {
    const digits = value.trim().replace('#', '').toUpperCase();
    const expanded =
        digits.length === 3 ? digits.split('').map((c) => c + c).join('') : digits;
    return `#${expanded}`;
};

/**
 * Read the saved theme colour, falling back to the default.
 */
export const getThemeColor = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (isValidThemeColor(saved)) return normalizeThemeColor(saved);
    } catch (e) {
        console.error('Error reading slide theme colour:', e);
    }
    return DEFAULT_THEME_COLOR;
};

/**
 * Persist the theme colour. Invalid values are ignored rather than stored.
 */
export const setThemeColor = (value) => {
    if (!isValidThemeColor(value)) return false;
    try {
        localStorage.setItem(STORAGE_KEY, normalizeThemeColor(value));
        return true;
    } catch (e) {
        console.error('Error saving slide theme colour:', e);
        return false;
    }
};
