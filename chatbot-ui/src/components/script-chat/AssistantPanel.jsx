import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { AlertCircle, ArrowLeft, Check, Download, FileCode, Loader2, MessageSquareText, Pencil, Play, Send, Sparkles, WandSparkles } from 'lucide-react';
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
} from '@/components/ai-elements/conversation';
import { Message, MessageContent, MessageLabel } from '@/components/ai-elements/message';
import {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from '@/components/ai-elements/prompt-input';
import {
  ReviewActions,
  ReviewActionsContent,
  ReviewActionsDescription,
  ReviewActionsTitle,
} from '@/components/ai-elements/review-actions';
import { Button } from '@/components/ui/button';

function Composer({
  disabled,
  editInput,
  interruptType,
  onApprove,
  onEditChange,
  onSubmitEdit,
}) {
  const canEdit = ['validation_review', 'metadata_review', 'script_review', 'compliance_review'].includes(interruptType);

  if (!interruptType) return null;

  const editPlaceholder = interruptType === 'metadata_review'
    ? 'Describe the metadata change...'
    : interruptType === 'validation_review'
      ? 'Describe the outline change...'
      : interruptType === 'compliance_review'
        ? 'Describe how to resolve compliance issues (e.g. shorten row 4, bold terms)...'
        : 'Describe the script change...';

  return (
    <div className="script-composer">
      {canEdit && (
        <PromptInput
          className="script-edit-composer"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmitEdit();
          }}
        >
          <PromptInputTextarea
            disabled={disabled}
            onChange={(event) => onEditChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                if (editInput.trim()) onSubmitEdit();
              }
            }}
            placeholder={editPlaceholder}
            rows={3}
            value={editInput}
          />
          <PromptInputSubmit
            className="script-icon-button script-icon-button-primary"
            disabled={disabled || !editInput.trim()}
            size="icon"
            title="Submit edit request"
          >
            <Send size={18} aria-hidden="true" />
          </PromptInputSubmit>
        </PromptInput>
      )}

      <ReviewActions>
        <ReviewActionsContent>
          <ReviewActionsTitle>
            {interruptType === 'compliance_review' ? 'Compliance review gate' : 'Review gate'}
          </ReviewActionsTitle>
          <ReviewActionsDescription>
            {interruptType === 'compliance_review'
              ? 'Submit an edit instruction to fix compliance issues, or approve to finalize.'
              : 'Request a change, or approve this artifact to continue.'}
          </ReviewActionsDescription>
        </ReviewActionsContent>
        <Button
          className="script-approve-button"
          disabled={disabled}
          onClick={onApprove}
          variant="success"
          type="button"
        >
          <Check size={17} aria-hidden="true" />
          Approve
        </Button>
      </ReviewActions>
    </div>
  );
}

function CompletedActions({ onDownloadDocx, onDownloadWiki, onNewThread }) {
  return (
    <div className="script-composer" style={{ padding: '16px', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#18875f', fontWeight: 600 }}>
        <Check size={18} />
        <span>Workflow Complete: Script Finalized</span>
      </div>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.4' }}>
        Your tutorial script is ready. Download your production files:
      </p>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
        <Button onClick={onDownloadDocx} style={{ flex: 1, gap: '6px' }} type="button">
          <Download size={15} /> Download DOCX
        </Button>
        <Button onClick={onDownloadWiki} variant="outline" style={{ flex: 1, gap: '6px' }} type="button">
          <FileCode size={15} /> Download Wiki
        </Button>
      </div>
      {onNewThread && (
        <Button onClick={onNewThread} variant="ghost" style={{ width: '100%', fontSize: '0.82rem' }} type="button">
          + Start Another Tutorial
        </Button>
      )}
    </div>
  );
}

function PausedOrErrorActions({
  currentStage,
  disabled,
  hasMetadata,
  hasOutline,
  hasScript,
  onJumpToMetadata,
  onJumpToScriptReview,
  onJumpToValidation,
  onRunCompliance,
}) {
  const isError = currentStage === 'error';

  return (
    <div className="script-composer" style={{ padding: '16px', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', color: isError ? 'var(--danger, #d23f3f)' : 'var(--text-primary)', fontWeight: 600 }}>
        <AlertCircle size={18} />
        <span>{isError ? 'Workflow Paused / Action Required' : 'Workflow Ready'}</span>
      </div>
      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.4' }}>
        {hasScript
          ? 'Your script draft is ready. You can run compliance checks, resume script review, or return to earlier stages.'
          : hasMetadata
            ? 'Metadata is ready. You can return to metadata review or restart outline validation.'
            : 'You can resume or restart this workflow from an earlier step below.'}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {hasScript && (
          <>
            <Button
              className="script-approve-button"
              disabled={disabled}
              onClick={onRunCompliance}
              style={{ width: '100%', gap: '6px' }}
              type="button"
              variant="success"
            >
              <Play size={16} aria-hidden="true" />
              Run Compliance Checks
            </Button>
            <Button
              disabled={disabled}
              onClick={onJumpToScriptReview}
              style={{ width: '100%', gap: '6px' }}
              type="button"
              variant="outline"
            >
              <Pencil size={15} aria-hidden="true" />
              Resume Script Review
            </Button>
          </>
        )}
        {hasMetadata && (
          <Button
            disabled={disabled}
            onClick={onJumpToMetadata}
            style={{ width: '100%', gap: '6px' }}
            type="button"
            variant="outline"
          >
            <ArrowLeft size={15} aria-hidden="true" />
            Back to Metadata Review
          </Button>
        )}
        {hasOutline && (
          <Button
            disabled={disabled}
            onClick={onJumpToValidation}
            style={{ width: '100%', gap: '6px' }}
            type="button"
            variant="ghost"
          >
            <ArrowLeft size={14} aria-hidden="true" />
            Back to Outline Validation
          </Button>
        )}
      </div>
    </div>
  );
}

export function AssistantPanel({
  chatLog,
  currentStage,
  editInput,
  errorMessage,
  interruptType,
  isLoading,
  metadata,
  onApprove,
  onDownloadDocx,
  onDownloadWiki,
  onEditChange,
  onJumpToMetadata,
  onJumpToScriptReview,
  onJumpToValidation,
  onNewThread,
  onRunCompliance,
  onStart,
  onSubmitEdit,
  outline,
  progressMessage,
  script,
  setOutline,
  threadId,
}) {
  const endRef = useRef(null);
  const showStart = !threadId;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatLog, isLoading]);

  return (
    <aside className="script-assistant-panel">
      <div className="script-panel-heading">
        <div>
          <span className="script-eyebrow">Assistant</span>
          <h2>Script assistant</h2>
        </div>
        {isLoading && <Loader2 className="script-spin" size={18} aria-hidden="true" />}
      </div>

      <Conversation>
        <ConversationContent className="script-chat-log">
          {showStart && (
            <ConversationEmptyState
              description="Paste your course outline below. I will validate it, draft metadata, generate the script, and pause at each review gate."
              icon={<WandSparkles size={22} aria-hidden="true" />}
              title="Ready to build a spoken tutorial"
            />
          )}

          {chatLog.map((message) => (
            <Message
              from={message.role}
              key={`${message.ts}-${message.role}-${message.content.slice(0, 12)}`}
            >
              <MessageLabel>{message.role === 'user' ? 'You' : 'Agent'}</MessageLabel>
              <MessageContent>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </MessageContent>
            </Message>
          ))}

          {isLoading && (
            <Message from="agent">
              <MessageLabel>Agent</MessageLabel>
              <MessageContent>
                <div className="script-inline-status">
                  <Loader2 className="script-spin" size={16} aria-hidden="true" />
                  {progressMessage || 'Working...'}
                </div>
              </MessageContent>
            </Message>
          )}

          {errorMessage && (
            <div className="script-error-banner" role="alert">
              {errorMessage}
            </div>
          )}

          <div ref={endRef} />
        </ConversationContent>
      </Conversation>

      {showStart ? (
        <div className="script-composer script-composer-start">
          <PromptInput
            onSubmit={(event) => {
              event.preventDefault();
              if (!isLoading && outline.trim()) {
                onStart();
              }
            }}
          >
            <PromptInputTextarea
              disabled={isLoading}
              onChange={(event) => setOutline(event.target.value)}
              placeholder="Paste your tutorial outline here..."
              rows={8}
              value={outline}
            />
            <PromptInputFooter>
              <PromptInputTools>
                <Sparkles size={15} aria-hidden="true" />
                <span>Review gates stay under your control</span>
              </PromptInputTools>
              <PromptInputSubmit disabled={isLoading || !outline.trim()}>
                <MessageSquareText size={17} aria-hidden="true" />
                Generate
              </PromptInputSubmit>
            </PromptInputFooter>
          </PromptInput>
        </div>
      ) : currentStage === 'done' ? (
        <CompletedActions
          onDownloadDocx={onDownloadDocx}
          onDownloadWiki={onDownloadWiki}
          onNewThread={onNewThread}
        />
      ) : interruptType ? (
        <Composer
          disabled={isLoading}
          editInput={editInput}
          interruptType={interruptType}
          onApprove={onApprove}
          onEditChange={onEditChange}
          onSubmitEdit={onSubmitEdit}
        />
      ) : (
        <PausedOrErrorActions
          currentStage={currentStage}
          disabled={isLoading}
          hasMetadata={Boolean(metadata)}
          hasOutline={Boolean(outline)}
          hasScript={Boolean(script?.length)}
          onJumpToMetadata={onJumpToMetadata}
          onJumpToScriptReview={onJumpToScriptReview}
          onJumpToValidation={onJumpToValidation}
          onRunCompliance={onRunCompliance}
        />
      )}
    </aside>
  );
}
