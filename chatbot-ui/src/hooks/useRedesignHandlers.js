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
                                        contentText += `\n\nExcel file generated successfully! You can download it below.`;
                                    }
                                    return {
                                        ...msg,
                                        content: contentText,
                                        ...(progressData.status === "completed" ? {
                                            type: 'redesign_result',
                                            downloadButton: {
                                                label: 'Download XLSX',
                                                filename: progressData.url
                                            }
                                        } : {})
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
                                throw { isPipelineFailure: true, message: progressData.message || "Failed to generate tutorial." };
                            }
                        } catch (pollError) {
                            if (pollError && pollError.isPipelineFailure) {
                                throw new Error(pollError.message);
                            }
                            console.error("Polling error:", pollError);
                        }
                    }
                } else {
                    const newBotMessage = {
                        id: Date.now() + 1,
                        role: 'assistant',
                        content: `✅ Tutorial generated successfully!\n\n` +
                            `Excel file generated successfully! You can download it below.`,
                        type: 'redesign_result',
                        downloadButton: {
                            label: 'Download XLSX',
                            filename: initData.url
                        }
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
        }
    }, [setUploadMessages, setIsTyping]);

    return {
        handleRedesignSubmit,
    };
}
