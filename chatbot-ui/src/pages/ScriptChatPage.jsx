import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { AssistantPanel } from '../components/script-chat/AssistantPanel';
import { ReviewWorkspace } from '../components/script-chat/ReviewWorkspace';
import { WorkflowRail } from '../components/script-chat/WorkflowRail';
import { useScriptChatWorkflow } from '../hooks/useScriptChatWorkflow';
import './ScriptChatPage.css';

export default function ScriptChatPage() {
  const workflow = useScriptChatWorkflow();

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
