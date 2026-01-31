/**
 * Export and edit handlers for the chat area.
 * Handles: DOCX download, script upload, MediaWiki export, inline edit, quality check.
 */

import { useCallback } from 'react';
import { apiJson, apiBlob, apiFormData, API_URL } from '../services/api';

/**
 * Hook for export and edit handlers.
 * @param {Function} setUploadMessages - State setter for upload messages
 * @param {Function} setIsTyping - State setter for typing indicator
 * @param {Function} setQualityReports - State setter for quality reports
 * @param {Function} setOpenQualityId - State setter for open quality ID
 * @param {Function} setIsQualityLoading - State setter for quality loading state
 * @returns {Object} Export and edit handler functions
 */
export function useExportHandlers(
    setUploadMessages,
    setIsTyping,
    setQualityReports,
    setOpenQualityId,
    setIsQualityLoading
) {

    /**
     * Download the script as a DOCX file.
     */
    const handleDownloadScriptDocx = useCallback(async (jsonScript) => {
        setIsTyping(true);

        try {
            const blob = await apiBlob('/download_script_docx', {
                method: 'POST',
                body: JSON.stringify({ json_script: jsonScript }),
            });

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'script.docx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            console.log('✅ Script downloaded');
        } catch (error) {
            console.error('Download error:', error);
            const errorMessage = {
                id: Date.now(),
                role: 'assistant',
                content: error.message || 'Failed to download script'
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Upload an edited DOCX script and update the message.
     */
    const handleUploadEditedScript = useCallback(async (file, messageId) => {
        if (!file) return;
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const data = await apiFormData('/upload_edited_script', formData);

            setUploadMessages(prev => prev.map(msg => {
                if (msg.id === messageId) {
                    return { ...msg, jsonScript: data.json_script, wasEdited: true };
                }
                return msg;
            }));

            const confirmMessage = {
                id: Date.now(),
                role: 'assistant',
                content: `✅ Script updated! (${data.slide_count} slides). You can now generate slides with your edits.`
            };
            setUploadMessages(prev => [...prev, confirmMessage]);

        } catch (error) {
            console.error('Upload error:', error);
            const errorMessage = {
                id: Date.now(),
                role: 'assistant',
                content: error.message || 'Failed to upload edited script'
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Export a script to MediaWiki format.
     */
    const handleExportMediaWiki = useCallback(async (jsonScript) => {
        setIsTyping(true);

        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Exporting script to MediaWiki format...`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const data = await apiJson('/export_mediawiki', {
                method: 'POST',
                body: JSON.stringify({ json_script: jsonScript }),
            });

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ MediaWiki export complete! You can copy the content below or download the .wiki file.`,
                mediawikiContent: data.mediawiki_content,
                mediawikiFileUrl: data.mediawiki_file_url,
                type: 'mediawiki_export'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong exporting to MediaWiki."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Save an inline script edit (updates message state only, no API call).
     */
    const handleSaveScriptEdit = useCallback((messageId, updatedScript) => {
        setUploadMessages(prev => prev.map(msg => {
            if (msg.id === messageId) {
                return {
                    ...msg,
                    jsonScript: updatedScript,
                    wasEdited: true
                };
            }
            return msg;
        }));

        const confirmMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `✅ Script updated! (${updatedScript.slides?.length || 0} slides edited inline). You can now generate slides or export.`
        };
        setUploadMessages(prev => [...prev, confirmMessage]);
    }, [setUploadMessages]);

    /**
     * Run a quality check on a script.
     * @param {Object} jsonScript - The script to check
     * @param {string|number} messageId - The message ID to associate the report with
     * @param {string} languageCode - Target language code (e.g., 'hi', 'ta', 'te'). Defaults to 'hi'
     */
    const handleQualityCheck = useCallback(async (jsonScript, messageId, languageCode = 'hi') => {
        setIsQualityLoading(true);
        setOpenQualityId(messageId);

        try {
            const data = await apiJson('/check_quality', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: jsonScript,
                    language_code: languageCode
                }),
            });

            setQualityReports(prev => ({ ...prev, [messageId]: data }));
            console.log(`✅ Quality check complete (${data.language_name || languageCode}):`, data.summary);

        } catch (error) {
            console.error('Quality check error:', error);
            setQualityReports(prev => ({
                ...prev,
                [messageId]: {
                    error: error.message,
                    checks: [{ id: 'error', criteria: 'Quality check failed', ai_review: null, ai_notes: error.message }],
                    summary: { ai_passed: 0, ai_failed: 0, total: 1 }
                }
            }));
        } finally {
            setIsQualityLoading(false);
        }
    }, [setQualityReports, setOpenQualityId, setIsQualityLoading]);

    return {
        handleDownloadScriptDocx,
        handleUploadEditedScript,
        handleExportMediaWiki,
        handleSaveScriptEdit,
        handleQualityCheck,
    };
}
