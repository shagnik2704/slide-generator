import React from 'react';
import { Archive, ArrowLeft, History, Plus, RefreshCw } from 'lucide-react';
import { AssistantPanel } from '../components/script-chat/AssistantPanel';
import { ReviewWorkspace } from '../components/script-chat/ReviewWorkspace';
import { WorkflowRail } from '../components/script-chat/WorkflowRail';
import { useScriptChatWorkflow } from '../hooks/useScriptChatWorkflow';
import './ScriptChatPage.css';

export default function ScriptChatPage() {
  const workflow = useScriptChatWorkflow();

  const archiveCurrentThread = () => {
    if (!workflow.threadId) return;
    if (window.confirm('Archive this saved workflow? You can no longer open it from this list.')) {
      void workflow.archiveSavedThread(workflow.threadId);
    }
  };

  return (
    <div className="script-page">
      <header className="script-topbar">
        <div className="script-topbar-title">
          <a className="script-back-link" href="/create">
            <ArrowLeft size={17} aria-hidden="true" />
            Back
          </a>
          <div>
            <span className="script-eyebrow">Spoken Tutorial Generator</span>
            <h1>Script workflow</h1>
          </div>
        </div>
        <div className="script-thread-controls">
          <History size={17} aria-hidden="true" />
          <select
            aria-label="Open a saved workflow"
            disabled={workflow.isLoadingThreads}
            onChange={(event) => void workflow.openThread(event.target.value)}
            value={workflow.threadId || ''}
          >
            <option value="">Saved workflows</option>
            {workflow.threads.map((thread) => (
              <option key={thread.thread_id} value={thread.thread_id}>
                {thread.title || thread.foss_name || thread.outline_preview || 'Untitled workflow'} · {thread.status}
              </option>
            ))}
          </select>
          <button
            aria-label="Refresh saved workflows"
            className="script-thread-icon-button"
            disabled={workflow.isLoadingThreads}
            onClick={() => void workflow.refreshThreads()}
            title="Refresh saved workflows"
            type="button"
          >
            <RefreshCw className={workflow.isLoadingThreads ? 'script-spin' : ''} size={16} />
          </button>
          <button
            className="script-thread-button"
            onClick={workflow.newThread}
            type="button"
          >
            <Plus size={16} aria-hidden="true" />
            New
          </button>
          {workflow.threadId && (
            <button
              aria-label="Archive current workflow"
              className="script-thread-icon-button"
              onClick={archiveCurrentThread}
              title="Archive current workflow"
              type="button"
            >
              <Archive size={16} aria-hidden="true" />
            </button>
          )}
        </div>
        <WorkflowRail currentStage={workflow.currentStage} isLoading={workflow.isLoading} />
      </header>

      <div className="script-shell">
        <AssistantPanel
          chatLog={workflow.chatLog}
          editInput={workflow.editInput}
          errorMessage={workflow.errorMessage}
          interruptType={workflow.interruptType}
          isLoading={workflow.isLoading}
          onApprove={workflow.approve}
          onEditChange={workflow.setEditInput}
          onStart={workflow.start}
          onSubmitEdit={workflow.submitEditInstruction}
          outline={workflow.outline}
          progressMessage={workflow.progressMessage}
          setOutline={workflow.setOutline}
          threadId={workflow.threadId}
        />

        <ReviewWorkspace
          activeTab={workflow.activeTab}
          checkpoints={workflow.checkpoints}
          complianceResults={workflow.complianceResults}
          fossName={workflow.fossName}
          groundingReport={workflow.groundingReport}
          interruptType={workflow.interruptType}
          isLoading={workflow.isLoading}
          isReverting={workflow.isReverting}
          metadata={workflow.metadata}
          onDownload={workflow.downloadDocx}
          onEditCell={workflow.editCell}
          onJumpToMetadata={workflow.jumpToMetadata}
          onLoadCheckpoints={workflow.loadCheckpoints}
          onRevert={workflow.revertToCheckpoint}
          onSaveOutline={workflow.saveValidatedOutline}
          onTabChange={workflow.setActiveTab}
          script={workflow.script}
          scriptVersion={workflow.scriptVersion}
          threadId={workflow.threadId}
        />
      </div>
    </div>
  );
}
