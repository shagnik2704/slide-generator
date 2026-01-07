/**
 * Redesign handlers for the chat area.
 * Handles: tutorial redesign submission.
 */

import { useCallback } from 'react';
import { apiJson } from '../services/api';

/**
 * Hook for redesign-related handlers.
 * @param {Function} setUploadMessages - State setter for upload messages
 * @param {Function} setIsTyping - State setter for typing indicator
 * @returns {Object} Redesign handler functions
 */
export function useRedesignHandlers(setUploadMessages, setIsTyping) {

    /**
     * Submit a redesign tutorial request.
     */
    const handleRedesignSubmit = useCallback(async (formData) => {
        setIsTyping(true);

        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Submitting redesign request for ${formData.foss_name}...`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const data = await apiJson('/sharing', {
                method: 'POST',
                body: JSON.stringify({
                    foss_name: formData.foss_name,
                    language: formData.language || 'English',
                    export: formData.export !== false,
                    user_emails: formData.user_emails || [],
                    user_role: formData.user_role || 'writer'
                }),
            });

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Redesign request submitted successfully!\n\n` +
                    `Status: ${data.status}\n` +
                    (data.url ? `URL: ${data.url}\n\n` : '') +
                    `The tutorial pipeline has been started.`,
                type: 'redesign_result',
                redesignData: data
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong submitting the redesign request."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    return {
        handleRedesignSubmit,
    };
}
