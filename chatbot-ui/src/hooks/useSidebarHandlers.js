/**
 * Sidebar-triggered handlers for the chat area.
 * Handles: compliance check, quality check, voice generation, image generation, slides generation.
 */

import { useCallback } from 'react';
import { apiFormData, apiJson } from '../services/api';

/**
 * Hook for sidebar-triggered handlers.
 * @param {Function} setUploadMessages - State setter for upload messages
 * @param {Function} setIsTyping - State setter for typing indicator
 * @param {Function} setCurrentProjectId - State setter for project ID
 * @param {Function} setQualityReports - State setter for quality reports
 * @param {Function} setOpenReportId - State setter for open report ID
 * @param {Function} setOpenQualityId - State setter for open quality ID
 * @returns {Object} Sidebar handler functions
 */
export function useSidebarHandlers(
    setUploadMessages,
    setIsTyping,
    setCurrentProjectId,
    setQualityReports,
    setOpenReportId,
    setOpenQualityId
) {

    /**
     * Run Admin Compliance check on a script file.
     */
    const handleSidebarComplianceUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Running Admin Compliance check on: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Step 2: Run compliance check
            const complianceReport = await apiJson('/check_compliance', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    tutorial_type: parseData.tutorial_type
                }),
            });

            const messageId = Date.now() + 1;
            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `Admin Compliance Check Complete\n\n` +
                    `Checked: ${file.name}\n` +
                    `Rows: ${parseData.json_script.slides?.length || 0}`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'script_uploaded',
                complianceReport: complianceReport,
                hideQualityCheck: true,
                hideGenerateSlides: true
            };
            setUploadMessages(prev => [...prev, newBotMessage]);
            setOpenReportId(messageId);

        } catch (error) {
            console.error("Compliance check error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Compliance check failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId, setOpenReportId]);

    /**
     * Run Quality Compliance check on a script file.
     */
    const handleSidebarQualityUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Running Quality Compliance on: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Step 2: Run quality check
            const qualityData = await apiJson('/check_quality', {
                method: 'POST',
                body: JSON.stringify({ json_script: parseData.json_script }),
            });

            const messageId = Date.now() + 1;
            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `Quality Compliance Check Complete\n\n` +
                    `Checked: ${file.name}\n` +
                    `Rows: ${parseData.json_script.slides?.length || 0}`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'script_uploaded',
                complianceReport: null,
                qualityReport: qualityData,
                hideQualityCheck: true,
                hideGenerateSlides: true
            };
            setUploadMessages(prev => [...prev, newBotMessage]);
            setQualityReports(prev => ({ ...prev, [messageId]: qualityData }));
            setOpenQualityId(messageId);

        } catch (error) {
            console.error("Quality check error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `Quality check failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId, setQualityReports, setOpenQualityId]);

    /**
     * Generate voice audio for a script file.
     */
    const handleSidebarVoiceUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `🎤 Generating voice for: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Step 2: Generate voice
            const voiceData = await apiJson('/generate_voice', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id,
                    target_audience: 'general'
                }),
            });

            const messageId = Date.now() + 1;
            const newBotMessage = {
                id: messageId,
                role: 'assistant',
                content: `🎤 Voice Generation Complete!\n\n` +
                    `File: ${file.name}\n` +
                    `Generated: ${voiceData.generated_slides}/${voiceData.total_slides} slides`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'voice_preview',
                voiceData: voiceData
            };
            setUploadMessages(prev => [...prev, newBotMessage]);

        } catch (error) {
            console.error("Voice generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Voice generation failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Parse script and enhance image prompts for review.
     */
    const handleSidebarImageUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `Parsing script for image generation: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update message to show enhancing
            const enhancingMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✨ Enhancing visual cues with AI...`
            };
            setUploadMessages(prev => [...prev, enhancingMessage]);

            // Step 2: Enhance prompts
            const enhanceData = await apiJson('/enhance_prompts', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id
                })
            });

            const messageId = Date.now() + 2;
            const reviewMessage = {
                id: messageId,
                role: 'assistant',
                content: `Review and edit the prompts below, then click Generate.`,
                jsonScript: parseData.json_script,
                projectId: parseData.project_id,
                type: 'image_prompt_review',
                enhancedPrompts: enhanceData.enhanced_prompts
            };
            setUploadMessages(prev => [...prev, reviewMessage]);

        } catch (error) {
            console.error("Image generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Generate Beamer slides from a script file.
     */
    const handleSlidesUpload = useCallback(async (file) => {
        const uploadMessage = {
            id: Date.now(),
            role: 'assistant',
            content: `🎴 Generating slides from: ${file.name}...`
        };
        setUploadMessages(prev => [...prev, uploadMessage]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Step 2: Generate slides
            const data = await apiJson('/generate_slides', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    tutorial_name: parseData.json_script?.title || file.name.replace(/\.[^/.]+$/, '')
                })
            });

            const resultMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `✅ Beamer template generated from "${file.name}"!\n\n` +
                    `📄 ${data.filename}\n` +
                    `📊 ${data.total_slides} total slides (${data.num_boilerplate_slides} boilerplate + ${data.num_content_slides} content)\n` +
                    `✨ Auto-filled from script!`,
                type: 'slides_result',
                slidesData: data
            };
            setUploadMessages(prev => [...prev, resultMessage]);

        } catch (error) {
            console.error("Slides generation error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed: ${error.message}`
            };
            setUploadMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    return {
        handleSidebarComplianceUpload,
        handleSidebarQualityUpload,
        handleSidebarVoiceUpload,
        handleSidebarImageUpload,
        handleSlidesUpload,
    };
}
