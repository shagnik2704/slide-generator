// LocalStorage helpers for ChatArea persistence

const STORAGE_KEY = 'spokentutorial_upload_state';
const MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Load state from localStorage
 * @returns {Object|null} Saved state or null if expired/missing
 */
export const loadFromLocalStorage = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const state = JSON.parse(saved);
            // Check if data is not too old
            if (Date.now() - state.savedAt < MAX_AGE_MS) {
                return state;
            }
            // Data expired, clear it
            localStorage.removeItem(STORAGE_KEY);
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
