/**
 * Generation handlers for the chat area.
 * Handles: script generation, slides generation, video generation.
 */

import { useCallback } from 'react';
import { apiJson } from '../services/api';

/**
 * Hook for generation-related handlers.
 * @param {Function} setUploadMessages - State setter for upload messages
 * @param {Function} setIsTyping - State setter for typing indicator
 * @param {number|null} currentProjectId - Current project ID
 * @param {Array} uploadMessages - Current upload messages (for finding jsonScript)
 * @returns {Object} Generation handler functions
 */
export function useGenerationHandlers(setUploadMessages, setIsTyping, currentProjectId, uploadMessages) {

    /**
     * Generate a script from an outline.
     */
    const handleGenerateScript = useCallback(async (outline, projectId) => {
        setIsTyping(true);

        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Generating script...`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const data = await apiJson('/generate_script', {
                method: 'POST',
                body: JSON.stringify({
                    outline: outline,
                    title: `Project #${projectId}`,
                    project_id: projectId
                }),
            });

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `I've generated a script for your tutorial. Please review it below.`,
                pdfUrl: data.script_pdf_url,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'script_review'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating script."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Generate slides PDF from a JSON script.
     */
    const handleGenerateSlides = useCallback(async (jsonScript, projectId) => {
        console.log("🚀 handleGenerateSlides called with:", { jsonScript, projectId });
        setIsTyping(true);

        const statusMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Generating slides... (This might take a moment)`
        };
        setUploadMessages(prev => [...prev, statusMessage]);

        try {
            const data = await apiJson('/generate_slides', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: jsonScript,
                    project_id: projectId || currentProjectId,
                    style_mode: "standard"
                }),
            });

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: "Slides PDF generated! Please review the slides below.",
                pdfUrl: data.slides_pdf_url,
                pdfPath: data.pdf_path,
                jsonScript: data.json_script,
                projectId: data.project_id,
                type: 'slides_review'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating slides."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, currentProjectId]);

    /**
     * Create slides from the most recent script in messages.
     */
    const handleCreateSlides = useCallback(async () => {
        // Find the most recent message with a jsonScript
        const scriptMessage = [...uploadMessages].reverse().find(msg => msg.jsonScript);
        const jsonScript = scriptMessage?.jsonScript;
        const tutorialName = jsonScript?.title || jsonScript?.metadata?.title || 'Tutorial Name';

        const generatingMessage = {
            id: Date.now(),
            role: 'assistant',
            content: jsonScript
                ? `🎴 Generating Beamer slides from "${tutorialName}"...`
                : `🎴 Generating Beamer slides template...`
        };
        setUploadMessages(prev => [...prev, generatingMessage]);
        setIsTyping(true);

        try {
            const data = await apiJson('/generate_slides', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: jsonScript || null,
                    tutorial_name: tutorialName
                })
            });

            const resultMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Beamer template generated!\n\n` +
                    `📄 ${data.filename}\n` +
                    `📊 ${data.total_slides} total slides (${data.num_boilerplate_slides} boilerplate + ${data.num_content_slides} content)` +
                    (jsonScript ? `\n✨ Auto-filled from script!` : ''),
                type: 'slides_result',
                slidesData: data
            };
            setUploadMessages(prev => [...prev, resultMessage]);

        } catch (error) {
            console.error("Slides generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Slides generation failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, uploadMessages]);

    /**
     * Approve slides and generate video.
     */
    const handleApprove = useCallback(async (jsonScript, pdfPath, projectId) => {
        setIsTyping(true);

        try {
            const data = await apiJson('/generate_video', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: jsonScript,
                    pdf_path: pdfPath,
                    project_id: projectId || currentProjectId
                }),
            });

            const newBotMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Project #${data.project_id} completed! Video generated successfully! Watch it below.`,
                videoUrl: data.video_url,
                projectId: data.project_id,
                type: 'video_result'
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong generating the video."
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, currentProjectId]);

    return {
        handleGenerateScript,
        handleGenerateSlides,
        handleCreateSlides,
        handleApprove,
    };
}
