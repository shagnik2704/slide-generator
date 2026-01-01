/**
 * Upload handlers for the chat area.
 * Handles: outline upload, script upload, script-to-wiki conversion.
 */

import { useCallback } from 'react';
import { apiFormData, apiJson } from '../services/api';

/**
 * Hook for upload-related handlers.
 * @param {Function} setUploadMessages - State setter for upload messages
 * @param {Function} setIsTyping - State setter for typing indicator
 * @param {Function} setCurrentProjectId - State setter for project ID
 * @returns {Object} Upload handler functions
 */
export function useUploadHandlers(setUploadMessages, setIsTyping, setCurrentProjectId) {

    /**
     * Upload an outline/content file and parse it.
     */
    const handleSendMessage = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Uploading content: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const data = await apiFormData('/upload_outline', formData);
            const projectId = Date.now();
            setCurrentProjectId(projectId);

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Content uploaded successfully!\n\nYou can now generate the script.`,
                outline: data.outline,
                projectId: projectId,
                type: 'outline_uploaded'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Upload an existing script file (JSON or DOCX).
     */
    const handleUploadScript = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Uploading script: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const data = await apiFormData('/upload_script', formData);
            setCurrentProjectId(data.project_id);

            const failedCount = data.compliance_report?.summary?.ai_failed || 0;
            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Script uploaded successfully! (${data.json_script.slides?.length || 0} slides)${failedCount > 0 ? `\n\n⚠️ ${failedCount} compliance issue${failedCount !== 1 ? 's' : ''} found. Check the report for details.` : ' All compliance checks passed!'} You can now generate slides directly.`,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_uploaded',
                complianceReport: data.compliance_report
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong uploading the script."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Convert a DOCX script directly to MediaWiki format.
     */
    const handleScriptToWiki = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Converting script to MediaWiki format: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const data = await apiFormData('/docx_to_mediawiki', formData);

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ ${data.message}`,
                type: 'mediawiki_export',
                mediawikiContent: data.mediawiki_content,
                mediawikiFileUrl: data.mediawiki_file_url,
                slideCount: data.slide_count
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Script to Wiki error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Conversion failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    return {
        handleSendMessage,
        handleUploadScript,
        handleScriptToWiki,
    };
}
