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
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'compliance',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: 'Running compliance check', status: 'pending' },
                { label: 'Report ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Running compliance check', status: 'processing' },
                        { label: 'Report ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Run compliance check
            const complianceReport = await apiJson('/check_compliance', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    tutorial_type: parseData.tutorial_type
                }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Running compliance check', status: 'complete' },
                        { label: 'Report ready', status: 'complete' }
                    ],
                    result: {
                        jsonScript: parseData.json_script,
                        projectId: parseData.project_id,
                        complianceReport: complianceReport,
                        hideQualityCheck: true,
                        hideGenerateSlides: true
                    }
                } : msg
            ));

            setOpenReportId(workflowId);

        } catch (error) {
            console.error("Compliance check error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId, setOpenReportId]);

    /**
     * Run Quality Compliance check on a script file.
     */
    const handleSidebarQualityUpload = useCallback(async (file) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'quality',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: 'Reviewing quality with AI', status: 'pending' },
                { label: 'Review ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Reviewing quality with AI', status: 'processing' },
                        { label: 'Review ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Run quality check
            const qualityData = await apiJson('/check_quality', {
                method: 'POST',
                body: JSON.stringify({ json_script: parseData.json_script }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Reviewing quality with AI', status: 'complete' },
                        { label: 'Review ready', status: 'complete' }
                    ],
                    result: {
                        jsonScript: parseData.json_script,
                        projectId: parseData.project_id,
                        complianceReport: null,
                        qualityReport: qualityData,
                        hideQualityCheck: true,
                        hideGenerateSlides: true
                    }
                } : msg
            ));

            setQualityReports(prev => ({ ...prev, [workflowId]: qualityData }));
            setOpenQualityId(workflowId);

        } catch (error) {
            console.error("Quality check error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId, setQualityReports, setOpenQualityId]);

    /**
     * Generate voice audio for a script file.
     * @param {File} file - Script file to generate voice for
     * @param {string} voiceMode - 'combined' for single file, 'rowwise' for per-row files
     */
    const handleSidebarVoiceUpload = useCallback(async (file, voiceMode = 'combined') => {
        const workflowId = Date.now();
        const modeLabel = voiceMode === 'combined' ? '(Full Audio)' : '(Row-wise)';

        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'voice',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: `Generating voice ${modeLabel}`, status: 'pending' },
                { label: 'Voice ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: `Generating voice ${modeLabel}`, status: 'processing' },
                        { label: 'Voice ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Generate voice based on mode
            const endpoint = voiceMode === 'combined'
                ? '/generate_voice_combined'
                : '/generate_voice';

            const voiceData = await apiJson(endpoint, {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id
                }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: `Generating voice ${modeLabel}`, status: 'complete' },
                        { label: 'Voice ready', status: 'complete' }
                    ],
                    result: {
                        voiceData: voiceData,
                        projectId: parseData.project_id,
                        jsonScript: parseData.json_script
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Voice generation error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);


    /**
     * Parse script and enhance image prompts for review.
     */
    const handleSidebarImageUpload = useCallback(async (file) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'images',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: 'Enhancing visual cues', status: 'pending' },
                { label: 'Ready for review', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Enhancing visual cues', status: 'processing' },
                        { label: 'Ready for review', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Enhance prompts
            const enhanceData = await apiJson('/enhance_prompts', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id
                })
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Enhancing visual cues', status: 'complete' },
                        { label: 'Ready for review', status: 'complete' }
                    ],
                    result: {
                        enhancedPrompts: enhanceData.enhanced_prompts,
                        projectId: parseData.project_id,
                        jsonScript: parseData.json_script
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Image generation error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Generate Beamer slides from a script file.
     */
    const handleSlidesUpload = useCallback(async (file) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'slides',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: 'Generating Beamer slides', status: 'pending' },
                { label: 'Template ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the script
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/parse_script', formData);
            setCurrentProjectId(parseData.project_id);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Generating Beamer slides', status: 'processing' },
                        { label: 'Template ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Generate slides
            const data = await apiJson('/generate_slides', {
                method: 'POST',
                body: JSON.stringify({
                    json_script: parseData.json_script,
                    project_id: parseData.project_id
                })
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Generating Beamer slides', status: 'complete' },
                        { label: 'Template ready', status: 'complete' }
                    ],
                    result: {
                        slidesData: data,
                        projectId: parseData.project_id
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Slides generation error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping, setCurrentProjectId]);

    /**
     * Run Batch Compliance check on multiple script files in parallel.
     * @param {File[]} files - Array of files to check
     */
    const handleSidebarBatchComplianceUpload = useCallback(async (files) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'batch_compliance',
            filename: `${files.length} scripts`,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${files.length} scripts`, status: 'processing' },
                { label: 'Running compliance checks', status: 'pending' },
                { label: 'Report ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse all files
            const parsePromises = files.map(async (file) => {
                const formData = new FormData();
                formData.append('file', file);
                const parseData = await apiFormData('/parse_script', formData);
                return {
                    filename: file.name,
                    json_script: parseData.json_script,
                    tutorial_type: parseData.tutorial_type || 'conceptual'
                };
            });

            const parsedScripts = await Promise.all(parsePromises);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${files.length} scripts`, status: 'complete' },
                        { label: 'Running compliance checks', status: 'processing' },
                        { label: 'Report ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Run batch compliance check
            const batchResult = await apiJson('/batch_check_compliance', {
                method: 'POST',
                body: JSON.stringify({
                    scripts: parsedScripts.map(s => s.json_script),
                    tutorial_types: parsedScripts.map(s => s.tutorial_type)
                }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${files.length} scripts`, status: 'complete' },
                        { label: 'Running compliance checks', status: 'complete' },
                        { label: 'Report ready', status: 'complete' }
                    ],
                    result: {
                        batchResults: batchResult.results.map((result, i) => ({
                            filename: parsedScripts[i].filename,
                            ...result
                        })),
                        batchSummary: batchResult.batch_summary
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Batch compliance check error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Handle batch quality check for multiple files (from modal).
     * Parses all files, sends to /batch_check_quality, displays results.
     * @param {File[]} files - Array of files to check
     */
    const handleSidebarBatchQualityUpload = useCallback(async (files) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'batch_quality',
            filename: `${files.length} scripts`,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${files.length} scripts`, status: 'processing' },
                { label: 'Reviewing quality forward & back', status: 'pending' },
                { label: 'Batch review ready', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse all files
            const parsePromises = files.map(async (file) => {
                const formData = new FormData();
                formData.append('file', file);
                const parseData = await apiFormData('/parse_script', formData);
                return {
                    filename: file.name,
                    json_script: parseData.json_script
                };
            });

            const parsedScripts = await Promise.all(parsePromises);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${files.length} scripts`, status: 'complete' },
                        { label: 'Reviewing quality forward & back', status: 'processing' },
                        { label: 'Batch review ready', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Run batch quality check
            const batchResult = await apiJson('/batch_check_quality', {
                method: 'POST',
                body: JSON.stringify({
                    scripts: parsedScripts.map(s => s.json_script),
                    language_code: languageCode
                }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${files.length} scripts`, status: 'complete' },
                        { label: 'Forward & Back translation', status: 'complete' },
                        { label: 'Batch review ready', status: 'complete' }
                    ],
                    result: {
                        batchResults: batchResult.results.map((result, i) => ({
                            filename: parsedScripts[i].filename,
                            ...result
                        })),
                        batchSummary: batchResult.batch_summary
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Batch quality check error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
        } finally {
            setIsTyping(false);
        }
    }, [setUploadMessages, setIsTyping]);

    /**
     * Generate a script from an outline file (using WorkflowCard).
     */
    const handleSidebarScriptGenerate = useCallback(async (file) => {
        const workflowId = Date.now();
        const initialWorkflow = {
            id: workflowId,
            type: 'workflow',
            tool: 'script',
            filename: file.name,
            status: 'processing',
            currentStep: 0,
            steps: [
                { label: `Parsing ${file.name}`, status: 'processing' },
                { label: 'Generating script with AI', status: 'pending' },
                { label: 'Script ready for review', status: 'pending' }
            ],
            role: 'assistant'
        };

        setUploadMessages(prev => [...prev, initialWorkflow]);
        setIsTyping(true);

        try {
            // Step 1: Parse the outline
            const formData = new FormData();
            formData.append('file', file);
            const parseData = await apiFormData('/upload_outline', formData);
            const projectId = Date.now();
            setCurrentProjectId(projectId);

            // Update to Step 2
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    currentStep: 1,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Generating script with AI', status: 'processing' },
                        { label: 'Script ready for review', status: 'pending' }
                    ]
                } : msg
            ));

            // Step 2: Generate the script
            const scriptData = await apiJson('/generate_script', {
                method: 'POST',
                body: JSON.stringify({
                    outline: parseData.outline,
                    title: `Project #${projectId}`,
                    project_id: projectId
                }),
            });

            // Update to Complete
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'complete',
                    currentStep: 3,
                    steps: [
                        { label: `Parsing ${file.name}`, status: 'complete' },
                        { label: 'Generating script with AI', status: 'complete' },
                        { label: 'Script ready for review', status: 'complete' }
                    ],
                    result: {
                        jsonScript: scriptData.json_script,
                        projectId: projectId,
                        outline: parseData.outline
                    }
                } : msg
            ));

        } catch (error) {
            console.error("Script generation error:", error);
            setUploadMessages(prev => prev.map(msg =>
                msg.id === workflowId ? {
                    ...msg,
                    status: 'error',
                    error: error.message
                } : msg
            ));
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
        handleSidebarBatchComplianceUpload,
        handleSidebarBatchQualityUpload,
        handleSidebarScriptGenerate,
    };
}

