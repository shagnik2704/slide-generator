// LocalStorage helpers for ChatArea persistence

const STORAGE_KEY = 'spokentutorial_upload_state';

/**
 * Load state from localStorage
 * @returns {Object|null} Saved state or null if missing
 */
export const loadFromLocalStorage = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            return JSON.parse(saved);
        }
    } catch (e) {
        console.error('Error loading from localStorage:', e);
    }
    return null;
};

/**
 * Save state to localStorage
 * @param {Array} uploadMessages - Current messages
 * @param {string} currentProjectId - Current project ID
 */
export const saveToLocalStorage = (uploadMessages, currentProjectId) => {
    try {
        const state = {
            uploadMessages,
            currentProjectId,
            savedAt: Date.now()
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
};

/**
 * Clear storage
 */
export const clearStorage = () => {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
        console.error('Error clearing localStorage:', e);
    }
};
