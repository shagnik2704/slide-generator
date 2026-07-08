import { useCallback, useEffect, useRef, useState } from 'react';
import {
  connectStream,
  exportDocx,
  getCheckpoints,
  jumpStage,
  manualEdit,
  resumeSession,
  revertState,
  startSession,
} from '../services/scriptChatService';
import {
  normalizeScript,
  stageFromNode,
  tabFromInterrupt,
} from '../lib/scriptChatContract';

function makeMessage(role, content) {
  return { role, content, ts: Date.now() };
}

function summarizeInterrupt(type, data, version) {
  if (type === 'validation_review') {
    const count = data.report?.corrections_made?.length || 0;
    return `Validation is ready. ${count} correction${count === 1 ? '' : 's'} found.`;
  }
  if (type === 'metadata_review') {
    return `Metadata is ready: ${data.metadata?.title || 'Untitled tutorial'}.`;
  }
  if (type === 'script_review') {
    return data.message || `Script draft is ready with ${data.script?.length || 0} slides (v${version}).`;
  }
  if (type === 'compliance_review') {
    const summary = data.summary || {};
    return `Compliance is ready: ${summary.ai_passed || 0}/${summary.total || 0} checks passed.`;
  }
  return 'Review is ready.';
}

export function useScriptChatWorkflow() {
  const [threadId, setThreadId] = useState(null);
  const [outline, setOutline] = useState('');
  const [currentStage, setCurrentStage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [interruptData, setInterruptData] = useState(null);
  const [interruptType, setInterruptType] = useState(null);
  const [script, setScript] = useState([]);
  const [scriptVersion, setScriptVersion] = useState(0);
  const [metadata, setMetadata] = useState(null);
  const [fossName, setFossName] = useState(null);
  const [groundingReport, setGroundingReport] = useState(null);
  const [complianceResults, setComplianceResults] = useState(null);
  const [activeTab, setActiveTab] = useState('validation');
  const [editInput, setEditInput] = useState('');
  const [chatLog, setChatLog] = useState([]);
  const [checkpoints, setCheckpoints] = useState([]);
  const [isReverting, setIsReverting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const streamCleanupRef = useRef(null);

  const addChat = useCallback((role, content) => {
    setChatLog((prev) => [...prev, makeMessage(role, content)]);
  }, []);

  const stopStream = useCallback(() => {
    streamCleanupRef.current?.();
    streamCleanupRef.current = null;
  }, []);

  useEffect(() => stopStream, [stopStream]);

  const makeHandlers = useCallback(() => ({
    onProgress: (data) => {
      setProgressMessage(data.status || '');
    },
    onState: (data) => {
      setCurrentStage(stageFromNode(data.node));
    },
    onInterrupt: (data) => {
      setIsLoading(false);
      setProgressMessage('');
      setErrorMessage('');
      setInterruptType(data.type);
      setInterruptData(data);
      setActiveTab(tabFromInterrupt(data.type));
      setCurrentStage(stageFromNode(data.type));

      if (data.type === 'validation_review') {
        setGroundingReport(data.report);
      }
      if (data.type === 'metadata_review') {
        setMetadata(data.metadata);
        setFossName(data.foss_name || null);
      }
      if (data.type === 'script_review') {
        const normalizedScript = normalizeScript(data.script);
        setScript(normalizedScript);
        setScriptVersion((previous) => {
          const nextVersion = previous + 1;
          addChat('agent', summarizeInterrupt(data.type, data, nextVersion));
          return nextVersion;
        });
        return;
      }
      if (data.type === 'compliance_review') {
        setComplianceResults(data.results);
      }

      addChat('agent', summarizeInterrupt(data.type, data, scriptVersion));
    },
    onDone: () => {
      setIsLoading(false);
      setProgressMessage('');
      setCurrentStage('done');
      setInterruptData(null);
      setInterruptType(null);
      addChat('agent', 'Workflow complete.');
    },
    onError: (err) => {
      const message = err?.message || 'Connection lost.';
      setIsLoading(false);
      setProgressMessage('');
      setErrorMessage(message);
      addChat('agent', `Error: ${message}`);
    },
  }), [addChat, scriptVersion]);

  const connectToThread = useCallback((nextThreadId) => {
    stopStream();
    streamCleanupRef.current = connectStream(nextThreadId, makeHandlers());
  }, [makeHandlers, stopStream]);

  const start = useCallback(async () => {
    if (!outline.trim()) return;
    setIsLoading(true);
    setErrorMessage('');
    setCurrentStage('ingest');
    setChatLog([makeMessage('user', outline), makeMessage('agent', 'Starting script workflow.')]);
    setInterruptData(null);
    setInterruptType(null);
    setScript([]);
    setScriptVersion(0);
    setMetadata(null);
    setFossName(null);
    setGroundingReport(null);
    setComplianceResults(null);
    setCheckpoints([]);
    setActiveTab('validation');

    try {
      const { thread_id } = await startSession(outline);
      setThreadId(thread_id);
      connectToThread(thread_id);
    } catch (err) {
      setIsLoading(false);
      setErrorMessage(err.message);
      addChat('agent', `Failed to start: ${err.message}`);
    }
  }, [addChat, connectToThread, outline]);

  const resume = useCallback(async (action, payload = {}) => {
    if (!threadId) return;
    setIsLoading(true);
    setErrorMessage('');
    setInterruptData(null);
    setInterruptType(null);

    if (action === 'approve') {
      addChat('user', 'Approved.');
    } else if (payload.instruction) {
      addChat('user', `Edit request: ${payload.instruction}`);
    } else if (payload.edited_content) {
      addChat('user', 'Updated the validated outline.');
    }

    try {
      await resumeSession(threadId, { action, ...payload }, makeHandlers());
    } catch (err) {
      setIsLoading(false);
      setErrorMessage(err.message);
      addChat('agent', `Resume failed: ${err.message}`);
    }
  }, [addChat, makeHandlers, threadId]);

  const submitEditInstruction = useCallback(async () => {
    const instruction = editInput.trim();
    if (!instruction) return;
    setEditInput('');
    await resume('edit', { instruction });
  }, [editInput, resume]);

  const saveValidatedOutline = useCallback(async (editedContent) => {
    if (!editedContent.trim()) return;
    await resume('edit', { edited_content: editedContent });
  }, [resume]);

  const approve = useCallback(() => resume('approve'), [resume]);

  const editCell = useCallback(async (slideNumber, field, value) => {
    if (!threadId) return;
    setScript((previous) =>
      previous.map((slide) =>
        slide.slide_number === slideNumber ? { ...slide, [field]: value } : slide
      )
    );

    try {
      await manualEdit(threadId, slideNumber, field, value);
    } catch (err) {
      setErrorMessage(err.message);
      addChat('agent', `Manual edit failed: ${err.message}`);
    }
  }, [addChat, threadId]);

  const loadCheckpoints = useCallback(async () => {
    if (!threadId) return;
    try {
      const response = await getCheckpoints(threadId);
      setCheckpoints(response.checkpoints || []);
    } catch (err) {
      setErrorMessage(err.message);
    }
  }, [threadId]);

  const revertToCheckpoint = useCallback(async (checkpointId) => {
    if (!threadId || !checkpointId) return;
    setIsReverting(true);
    setIsLoading(true);
    setErrorMessage('');
    try {
      await revertState(threadId, checkpointId);
      setCheckpoints([]);
      connectToThread(threadId);
    } catch (err) {
      setErrorMessage(err.message);
      setIsLoading(false);
    } finally {
      setIsReverting(false);
    }
  }, [connectToThread, threadId]);

  const jumpToMetadata = useCallback(async () => {
    if (!threadId) return;
    setIsLoading(true);
    setErrorMessage('');
    try {
      await jumpStage(threadId, 'metadata_review');
      connectToThread(threadId);
    } catch (err) {
      setErrorMessage(err.message);
      setIsLoading(false);
    }
  }, [connectToThread, threadId]);

  const downloadDocx = useCallback(async () => {
    if (!threadId) return;
    setIsLoading(true);
    setErrorMessage('');
    try {
      const blob = await exportDocx(threadId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      const titleSlug = (metadata?.title || 'script')
        .toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_]/g, '');
      link.href = url;
      link.download = `${titleSlug}_script.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [metadata?.title, threadId]);

  return {
    activeTab,
    approve,
    chatLog,
    checkpoints,
    complianceResults,
    currentStage,
    downloadDocx,
    editCell,
    editInput,
    errorMessage,
    fossName,
    groundingReport,
    interruptData,
    interruptType,
    isLoading,
    isReverting,
    jumpToMetadata,
    loadCheckpoints,
    metadata,
    outline,
    progressMessage,
    revertToCheckpoint,
    saveValidatedOutline,
    script,
    scriptVersion,
    setActiveTab,
    setEditInput,
    setOutline,
    start,
    submitEditInstruction,
    threadId,
  };
}
