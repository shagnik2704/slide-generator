import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Check, Loader2, MessageSquareText, Send, Sparkles, WandSparkles } from 'lucide-react';
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
  const canEdit = ['validation_review', 'metadata_review', 'script_review'].includes(interruptType);

  if (!interruptType) return null;

  const editPlaceholder = interruptType === 'metadata_review'
    ? 'Describe the metadata change...'
    : interruptType === 'validation_review'
      ? 'Describe the outline change...'
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
          <ReviewActionsTitle>Review gate</ReviewActionsTitle>
          <ReviewActionsDescription>
            Request a change, or approve this artifact to continue.
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
