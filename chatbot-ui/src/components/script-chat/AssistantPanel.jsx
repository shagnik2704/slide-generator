import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Check, Loader2, MessageSquareText, Send, WandSparkles } from 'lucide-react';

function Composer({
  disabled,
  editInput,
  interruptType,
  onApprove,
  onEditChange,
  onSubmitEdit,
}) {
  const canEdit = ['validation_review', 'metadata_review', 'script_review'].includes(interruptType);

  if (!interruptType) return null;

  return (
    <div className="script-composer">
      {canEdit && (
        <div className="script-edit-composer">
          <textarea
            className="script-input script-input-compact"
            disabled={disabled}
            onChange={(event) => onEditChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                onSubmitEdit();
              }
            }}
            placeholder={
              interruptType === 'metadata_review'
                ? 'Describe the metadata change...'
                : interruptType === 'validation_review'
                  ? 'Describe the outline change...'
                  : 'Describe the script change...'
            }
            rows={3}
            value={editInput}
          />
          <button
            className="script-icon-button script-icon-button-primary"
            disabled={disabled || !editInput.trim()}
            onClick={onSubmitEdit}
            title="Submit edit request"
            type="button"
          >
            <Send size={18} aria-hidden="true" />
          </button>
        </div>
      )}

      <button
        className="script-button script-button-success"
        disabled={disabled}
        onClick={onApprove}
        type="button"
      >
        <Check size={18} aria-hidden="true" />
        Approve
      </button>
    </div>
  );
}

export function AssistantPanel({
  chatLog,
  editInput,
  errorMessage,
  interruptType,
  isLoading,
  onApprove,
  onEditChange,
  onStart,
  onSubmitEdit,
  outline,
  progressMessage,
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
          <h2>Run control</h2>
        </div>
        {isLoading && <Loader2 className="script-spin" size={18} aria-hidden="true" />}
      </div>

      <div className="script-chat-log">
        {showStart && (
          <div className="script-start-card">
            <WandSparkles size={24} aria-hidden="true" />
            <h3>Create a spoken tutorial script</h3>
            <p>Paste an outline, then review each generated artifact before the workflow advances.</p>
          </div>
        )}

        {chatLog.map((message) => (
          <div
            className={`script-message script-message-${message.role}`}
            key={`${message.ts}-${message.role}-${message.content.slice(0, 12)}`}
          >
            <span>{message.role === 'user' ? 'You' : 'Agent'}</span>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ))}

        {isLoading && (
          <div className="script-message script-message-agent">
            <span>Agent</span>
            <div className="script-inline-status">
              <Loader2 className="script-spin" size={16} aria-hidden="true" />
              {progressMessage || 'Working...'}
            </div>
          </div>
        )}

        {errorMessage && (
          <div className="script-error-banner" role="alert">
            {errorMessage}
          </div>
        )}

        <div ref={endRef} />
      </div>

      {showStart ? (
        <div className="script-composer">
          <textarea
            className="script-input"
            disabled={isLoading}
            onChange={(event) => setOutline(event.target.value)}
            placeholder="Paste your tutorial outline here..."
            rows={8}
            value={outline}
          />
          <button
            className="script-button script-button-primary"
            disabled={isLoading || !outline.trim()}
            onClick={onStart}
            type="button"
          >
            <MessageSquareText size={18} aria-hidden="true" />
            Generate Script
          </button>
        </div>
      ) : (
        <Composer
          disabled={isLoading}
          editInput={editInput}
          interruptType={interruptType}
          onApprove={onApprove}
          onEditChange={onEditChange}
          onSubmitEdit={onSubmitEdit}
        />
      )}
    </aside>
  );
}
