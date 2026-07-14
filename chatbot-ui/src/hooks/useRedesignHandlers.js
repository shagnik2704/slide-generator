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
            const statusMessageId = Date.now();
            const statusMessage = {
                id: statusMessageId,
                role: 'assistant',
                content: `⏳ Queuing redesign task for ${formData.foss_name}...`
            };
            setUploadMessages(prev => [...prev, statusMessage]);

            try {
                const initData = await apiJson('/redesign/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        foss_name: formData.foss_name,
                        language: formData.language || 'English'
                    }),
                });

                if (initData.status === 'started' && initData.task_id) {
                    const taskId = initData.task_id;
                    let isCompleted = false;

                    while (!isCompleted) {
                        await new Promise(resolve => setTimeout(resolve, 1500));

                        try {
                            const progressData = await apiJson(`/redesign/progress/${taskId}`, {
                                method: 'GET'
                            });

                            if (formData.onProgress) {
                                formData.onProgress(progressData);
                            }

                            setUploadMessages(prev => prev.map(msg => {
                                if (msg.id === statusMessageId) {
                                    let icon = "⏳";
                                    if (progressData.status === "completed") icon = "✅";
                                    else if (progressData.status === "failed") icon = "❌";
                                    else if (progressData.progress > 80) icon = "📤";
                                    else if (progressData.progress > 40) icon = "🤖";
                                    else if (progressData.progress > 10) icon = "🔍";

                                    let contentText = `${icon} [${progressData.progress}%] ${progressData.message}`;
                                    if (progressData.status === "completed") {
                                        contentText += `\n\nGoogle Sheet URL: ${progressData.url}`;
                                    }
                                    return {
                                        ...msg,
                                        content: contentText
                                    };
                                }
                                return msg;
                            }));

                            if (progressData.status === 'completed') {
                                isCompleted = true;
                                return {
                                    status: 'success',
                                    url: progressData.url,
                                    task_id: taskId
                                };
                            } else if (progressData.status === 'failed') {
                                isCompleted = true;
                                throw new Error(progressData.message || "Failed to generate tutorial.");
                            }
                        } catch (pollError) {
                            console.error("Polling error:", pollError);
                        }
                    }
                } else {
                    const newBotMessage = {
                        id: Date.now() + 1,
                        role: 'assistant',
                        content: `✅ Tutorial generated successfully!\n\n` +
                            `URL: ${initData.url}\n\n` +
                            `You can now preview and share the sheet.`,
                        type: 'redesign_result',
                        redesignData: initData
                    };
                    setUploadMessages(prev => prev.map(msg => msg.id === statusMessageId ? newBotMessage : msg));
                    return initData;
                }

            } catch (error) {
                console.error("Error:", error);

                const isNotFoundError = error.message &&
                    (error.message.includes("No tutorials found") ||
                        error.message.includes("not available in the selected language"));

                const errorMessageText = isNotFoundError
                    ? `⚠️ ${error.message}\n\nPlease try selecting a different language or FOSS that has available tutorials.`
                    : error.message || "Sorry, something went wrong generating the tutorial.";

                setUploadMessages(prev => prev.map(msg => {
                    if (msg.id === statusMessageId) {
                        return {
                            ...msg,
                            content: `❌ Generation failed.\n\n${errorMessageText}`
                        };
                    }
                    return msg;
                }));

                throw error;
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
                const data = await apiJson('/redesign/share', {
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
