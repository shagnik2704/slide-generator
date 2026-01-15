/**
 * Outline chat handlers for the chat area.
 * Handles: outline chat conversation, confirmation, and field editing.
 */

import { useState, useCallback } from 'react';
import { apiJson, apiFormData } from '../services/api';

// Default outline message
const DEFAULT_OUTLINE_MESSAGE = {
    id: 2,
    role: 'assistant',
    content: 'Hi! 😊 I\'m here to help you create a Spoken Tutorial course outline, step by step.\n\nTo start, could you tell me what kind of course this is: **FOSS**, **ICT**, or **Other**?\n\nJust reply with `FOSS`, `ICT`, or `Other` (you can add a short note if you pick Other). Then I\'ll gently walk you through a few short questions.',
};

/**
 * Hook for outline chat logic.
 * @param {string} mode - Current mode ('upload' | 'outline_chat')
 * @param {Function} setIsTyping - State setter for typing indicator
 * @returns {Object} Outline chat state and handlers
 */
export function useOutlineChat(mode, setIsTyping) {
    const [outlineMessages, setOutlineMessages] = useState([DEFAULT_OUTLINE_MESSAGE]);
    const [outlineSession, setOutlineSession] = useState({
        projectId: null,
        outlineData: null,
        phase: null
    });

    /**
     * Send a text message in outline chat mode.
     */
    const handleSendChatText = useCallback(async (text) => {
        if (mode !== 'outline_chat') return;

        const userMessage = { id: Date.now(), role: 'user', content: text };
        const conversationForApi = [...outlineMessages, userMessage].map(({ role, content }) => ({ role, content }));
        setOutlineMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const data = await apiJson('/outline_chat', {
                method: 'POST',
                body: JSON.stringify({
                    conversation: conversationForApi,
                    outline_data: outlineSession.outlineData || null,
                    project_id: outlineSession.projectId,
                    phase: outlineSession.phase || null,
                }),
            });

            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            // Update the user message with the field_name that was answered
            if (data.answered_field) {
                setOutlineMessages(prev => prev.map(msg =>
                    msg.id === userMessage.id
                        ? { ...msg, fieldName: data.answered_field, wasEdited: false }
                        : msg
                ));
            }

            let assistantContent = data.assistant_message || 'Here is the updated outline.';

            if (data.validation_errors && data.validation_errors.length > 0) {
                assistantContent += '\n\n⚠️ Issues to address:\n' + data.validation_errors.map(e => `- ${e}`).join('\n');
            }

            if (data.is_draft_ready && data.pedagogy_compliance) {
                const pc = data.pedagogy_compliance;
                assistantContent += '\n\n**Pedagogy Compliance:**\n';
                assistantContent += `- Core Example: ${pc.core_example ? '✓' : '✗'}\n`;
                assistantContent += `- Demo Content: ${pc.demo_percentage?.toFixed(1) || 0}% ${pc.demo_percentage >= 75 ? '✓' : '⚠️'}\n`;
                assistantContent += `- Menu-free: ${pc.menu_free ? '✓' : '⚠️'}\n`;
                assistantContent += `- Time checks: ${pc.time_checks ? '✓' : '⚠️'}\n`;
                assistantContent += `- No repetition: ${pc.no_repetition ? '✓' : '⚠️'}\n`;
            }

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: assistantContent,
                outlineData: data.outline_data,
                isDraftReady: data.is_draft_ready,
                isApproved: data.is_approved,
                phase: data.phase,
                needsConfirmation: data.needs_confirmation || false,
                confirmationField: data.confirmation_field,
                confirmationValue: data.confirmation_value
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);

            if (data.is_approved) {
                const exportMessage = {
                    id: Date.now() + 3,
                    role: 'assistant',
                    content: `✅ Outline approved! You can export it using:\n\`GET /outline_chat/${data.project_id}/export?format=json\``,
                    type: 'outline_approved',
                    projectId: data.project_id
                };
                setOutlineMessages(prev => [...prev, exportMessage]);
            }
        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 3,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong in outline chat."
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineMessages, outlineSession, setIsTyping]);

    /**
     * Handle confirmation (yes/no) in outline chat.
     */
    const handleConfirmation = useCallback(async (confirmed) => {
        if (mode !== 'outline_chat') return;

        const confirmationText = confirmed ? 'yes' : 'no';
        const userMessage = { id: Date.now(), role: 'user', content: confirmationText };
        const conversationForApi = [...outlineMessages, userMessage].map(({ role, content }) => ({ role, content }));
        setOutlineMessages(prev => [...prev, userMessage]);
        setIsTyping(true);

        try {
            const data = await apiJson('/outline_chat', {
                method: 'POST',
                body: JSON.stringify({
                    conversation: conversationForApi,
                    outline_data: outlineSession.outlineData || null,
                    project_id: outlineSession.projectId,
                    phase: outlineSession.phase || null,
                }),
            });

            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: data.assistant_message || 'Here is the updated outline.',
                outlineData: data.outline_data,
                isDraftReady: data.is_draft_ready,
                isApproved: data.is_approved,
                phase: data.phase,
                needsConfirmation: data.needs_confirmation || false,
                confirmationField: data.confirmation_field,
                confirmationValue: data.confirmation_value
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: error.message || "Sorry, something went wrong in outline chat."
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineMessages, outlineSession, setIsTyping]);

    /**
     * Edit a previously answered field in the outline.
     */
    const handleEditAnswer = useCallback(async (messageId, fieldName, newValue, tutorialNumber = null) => {
        if (mode !== 'outline_chat') return;

        if (!outlineSession.projectId) {
            console.error('No project ID available for editing');
            return;
        }

        setIsTyping(true);

        try {
            const requestBody = {
                field_name: fieldName,
                new_value: newValue,
            };

            if (tutorialNumber !== null) {
                requestBody.tutorial_number = tutorialNumber;
            }

            const data = await apiJson(`/outline_chat/${outlineSession.projectId}/edit`, {
                method: 'POST',
                body: JSON.stringify(requestBody),
            });

            // Update session with new outline data
            setOutlineSession({
                projectId: data.project_id || outlineSession.projectId,
                outlineData: data.outline_data || outlineSession.outlineData,
                phase: data.phase || outlineSession.phase
            });

            // Update the edited message
            setOutlineMessages(prev => prev.map(msg => {
                if (msg.id === messageId) {
                    return {
                        ...msg,
                        content: newValue,
                        wasEdited: true,
                        editedAt: Date.now()
                    };
                }
                return msg;
            }));

            // Add assistant response about the update
            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: data.assistant_message || 'Answer updated successfully.',
                outlineData: data.outline_data,
                phase: data.phase,
                isDraftReady: data.is_draft_ready,
            };

            setOutlineMessages(prev => [...prev, assistantMessage]);

        } catch (error) {
            console.error("Edit error:", error);
            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: `❌ Failed to update answer: ${error.message}`
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
        }
    }, [mode, outlineSession, setIsTyping]);

    /**
     * Check compliance for an outline.
     */
    const handleCheckCompliance = useCallback(async (outlineData, messageId) => {
        if (mode !== 'outline_chat' || !outlineData) return;

        setIsTyping(true);

        try {
            const complianceReport = await apiJson('/check_outline_compliance', {
                method: 'POST',
                body: JSON.stringify({
                    outline_data: outlineData
                }),
            });

            // Update the message with compliance report
            setOutlineMessages(prev => prev.map(msg =>
                msg.id === messageId
                    ? { ...msg, complianceReport: complianceReport }
                    : msg
            ));

            return complianceReport;
        } catch (error) {
            console.error("Compliance check error:", error);
            throw error;
        } finally {
            setIsTyping(false);
        }
    }, [mode, setIsTyping]);

    /**
     * Update compliance report in a message.
     */
    const handleUpdateComplianceReport = useCallback((messageId, updatedReport) => {
        setOutlineMessages(prev => prev.map(msg =>
            msg.id === messageId ? { ...msg, complianceReport: updatedReport } : msg
        ));
    }, []);

    /**
     * Upload outline file and check compliance.
     */
    const handleUploadOutlineCompliance = useCallback(async (file) => {
        if (mode !== 'outline_chat' || !file) return;

        setIsTyping(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const result = await apiFormData('/upload_outline_for_compliance', formData);

            if (result.compliance_report) {
                const messageId = Date.now();
                const passed = result.compliance_report.summary?.ai_passed || 0;
                const failed = result.compliance_report.summary?.ai_failed || 0;
                const total = passed + failed;
                
                const newMessage = {
                    id: messageId,
                    role: 'assistant',
                    content: `✅ Outline Compliance Check Complete\n\n` +
                        `**File:** ${file.name}\n` +
                        `**Summary:** ${passed}/${total} checks passed, ${failed} failed\n\n` +
                        `Click "View Report" below to see detailed compliance results.`,
                    outlineData: result.outline_data,
                    complianceReport: result.compliance_report,
                    type: 'outline_compliance_result'
                };

                setOutlineMessages(prev => [...prev, newMessage]);
                return result.compliance_report;
            }
        } catch (error) {
            console.error("Outline compliance upload error:", error);
            const errorMessage = {
                id: Date.now(),
                role: 'assistant',
                content: `❌ Outline compliance check failed: ${error.message}`
            };
            setOutlineMessages(prev => [...prev, errorMessage]);
            throw error;
        } finally {
            setIsTyping(false);
        }
    }, [mode, setIsTyping]);

    return {
        outlineMessages,
        setOutlineMessages,
        outlineSession,
        setOutlineSession,
        handleSendChatText,
        handleConfirmation,
        handleEditAnswer,
        handleCheckCompliance,
        handleUpdateComplianceReport,
        handleUploadOutlineCompliance,
    };
}
