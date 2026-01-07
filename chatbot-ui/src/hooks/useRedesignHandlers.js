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
        if (formData.type === 'generate') {
            setIsTyping(true);

            const statusMessage = {
                id: Date.now(),
                role: 'assistant',
                content: `Generating tutorial for ${formData.foss_name}...`
            };
            setUploadMessages(prev => [...prev, statusMessage]);

            try {
                const data = await apiJson('/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        foss_name: formData.foss_name,
                        language: formData.language || 'English'
                    }),
                });

                const newBotMessage = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: `✅ Tutorial generated successfully!\n\n` +
                        `URL: ${data.url}\n\n` +
                        `You can now preview and share the sheet.`,
                    type: 'redesign_result',
                    redesignData: data
                };
                setUploadMessages(prev => [...prev, newBotMessage]);

                return data; // Return for the form to use

            } catch (error) {
                console.error("Error:", error);
                const errorMessage = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: error.message || "Sorry, something went wrong generating the tutorial."
                };
                setUploadMessages(prev => [...prev, errorMessage]);
            } finally {
                setIsTyping(false);
            }
        } else if (formData.type === 'share') {
            setIsTyping(true);

            const statusMessage = {
                id: Date.now(),
                role: 'assistant',
                content: `Sharing sheet with ${formData.recipients.length} recipients...`
            };
            setUploadMessages(prev => [...prev, statusMessage]);

            try {
                const data = await apiJson('/share', {
                    method: 'POST',
                    body: JSON.stringify({
                        url: formData.url,
                        recipients: formData.recipients
                    }),
                });

                const newBotMessage = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: `✅ ${data.message}`,
                    type: 'share_result',
                    shareData: data
                };
                setUploadMessages(prev => [...prev, newBotMessage]);

            } catch (error) {
                console.error("Error:", error);
                const errorMessage = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: error.message || "Sorry, something went wrong sharing the sheet."
                };
                setUploadMessages(prev => [...prev, errorMessage]);
            } finally {
                setIsTyping(false);
            }
        }
    }, [setUploadMessages, setIsTyping]);

    return {
        handleRedesignSubmit,
    };
}
