import { useState } from 'react';
import {
  ArrowLeft,
  Download,
  History,
  Pencil,
  Save,
  X,
} from 'lucide-react';
import { SCRIPT_CHAT_TABS } from '../../lib/scriptChatContract';
import { ScriptReviewCard } from './ScriptReviewCard';

function EmptyWorkspace({ threadId }) {
  return (
    <div className="script-empty-workspace">
      <h2>{threadId ? 'Waiting for the next review' : 'Paste an outline to begin'}</h2>
      <p>
        {threadId
          ? 'Validation reports, metadata, scripts, and compliance checks appear here as the backend reaches each review gate.'
          : 'The generated artifacts will stay in this workspace while the assistant panel handles workflow control.'}
      </p>
    </div>
  );
}

function TabBar({ activeTab, availableTabs, onChange }) {
  return (
    <div className="script-tabs" role="tablist" aria-label="Review artifacts">
      {SCRIPT_CHAT_TABS.map((tab) => (
        <button
          className={activeTab === tab.key ? 'is-active' : ''}
          disabled={!availableTabs.includes(tab.key)}
          key={tab.key}
          onClick={() => onChange(tab.key)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function ValidationPanel({
  groundingReport,
  interruptType,
  isLoading,
  onSaveOutline,
}) {
  const validatedContent = groundingReport?.validated_content || '';
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(validatedContent);

  if (!groundingReport) return <EmptyWorkspace threadId />;

  return (
    <section className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Validation</span>
          <h2>Grounding report</h2>
        </div>
        <span className={groundingReport.is_mostly_correct ? 'script-badge success' : 'script-badge warning'}>
          {groundingReport.is_mostly_correct ? 'Mostly correct' : 'Needs attention'}
        </span>
      </div>

      <div className="script-section">
        <div className="script-section-header">
          <h3>Validated outline</h3>
          {interruptType === 'validation_review' && (
            isEditing ? (
              <div className="script-button-row">
                <button
                  className="script-icon-button"
                  disabled={isLoading}
                  onClick={() => {
                    setDraft(validatedContent);
                    setIsEditing(false);
                  }}
                  title="Cancel outline edits"
                  type="button"
                >
                  <X size={16} aria-hidden="true" />
                </button>
                <button
                  className="script-icon-button script-icon-button-primary"
                  disabled={isLoading || !draft.trim()}
                  onClick={async () => {
                    await onSaveOutline(draft);
                    setIsEditing(false);
                  }}
                  title="Save outline edits"
                  type="button"
                >
                  <Save size={16} aria-hidden="true" />
                </button>
              </div>
            ) : (
              <button
                className="script-icon-button"
                disabled={isLoading}
                onClick={() => setIsEditing(true)}
                title="Edit validated outline"
                type="button"
              >
                <Pencil size={16} aria-hidden="true" />
              </button>
            )
          )}
        </div>

        {isEditing ? (
          <textarea
            className="script-outline-editor"
            onChange={(event) => setDraft(event.target.value)}
            value={draft}
          />
        ) : (
          <pre className="script-outline-preview">{draft || validatedContent}</pre>
        )}
      </div>

      {!!groundingReport.corrections_made?.length && (
        <div className="script-section">
          <h3>Corrections</h3>
          <ul className="script-list">
            {groundingReport.corrections_made.map((correction) => (
              <li key={correction}>{correction}</li>
            ))}
          </ul>
        </div>
      )}

      {!!groundingReport.warnings?.length && (
        <div className="script-section">
          <h3>Warnings</h3>
          <ul className="script-list">
            {groundingReport.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function MetadataPanel({ metadata }) {
  if (!metadata) return <EmptyWorkspace threadId />;

  return (
    <section className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Metadata</span>
          <h2>{metadata.title || 'Untitled tutorial'}</h2>
        </div>
      </div>

      <dl className="script-metadata-grid">
        <div>
          <dt>Prerequisites</dt>
          <dd>{metadata.prerequisites || 'None listed'}</dd>
        </div>
        <div>
          <dt>Learning objectives</dt>
          <dd>
            <ul className="script-list">
              {(metadata.learning_objectives || []).map((objective) => (
                <li key={objective}>{objective}</li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt>Tags</dt>
          <dd className="script-tag-row">
            {(metadata.meta_tags || []).map((tag) => (
              <span className="script-tag" key={tag}>{tag}</span>
            ))}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function ScriptPanel({
  checkpoints,
  isLoading,
  isReviewing,
  isReverting,
  onDownload,
  onEditCell,
  onJumpToMetadata,
  onLoadCheckpoints,
  onRevert,
  script,
  scriptVersion,
}) {
  if (!script.length) return <EmptyWorkspace threadId />;

  return (
    <section className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Script</span>
          <h2>Draft v{scriptVersion}</h2>
        </div>
        <div className="script-toolbar">
          <span className="script-badge">{script.length} slides</span>
          <button
            className="script-icon-button"
            disabled={isLoading}
            onClick={onLoadCheckpoints}
            title="Load version history"
            type="button"
          >
            <History size={16} aria-hidden="true" />
          </button>
          <button
            className="script-icon-button"
            disabled={isLoading}
            onClick={() => {
              if (window.confirm('Jump back to Metadata Review? This will discard unapproved script changes.')) {
                onJumpToMetadata();
              }
            }}
            title="Return to metadata review"
            type="button"
          >
            <ArrowLeft size={16} aria-hidden="true" />
          </button>
          <button
            className="script-icon-button script-icon-button-primary"
            disabled={isLoading}
            onClick={onDownload}
            title="Download DOCX"
            type="button"
          >
            <Download size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      {!!checkpoints.length && (
        <div className="script-version-row">
          <select
            disabled={isReverting}
            onChange={(event) => {
              if (!event.target.value) return;
              if (window.confirm('Revert to this version? Current script edits will be overwritten.')) {
                onRevert(event.target.value);
              }
              event.target.value = '';
            }}
          >
            <option value="">Revert to version...</option>
            {checkpoints.map((checkpoint) => (
              <option key={checkpoint.checkpoint_id} value={checkpoint.checkpoint_id}>
                Version {checkpoint.version} · {new Date(checkpoint.timestamp).toLocaleTimeString()}
              </option>
            ))}
          </select>
        </div>
      )}

      <ScriptReviewCard editable={isReviewing} onEditCell={onEditCell} script={script} />
    </section>
  );
}

function CompliancePanel({ complianceResults }) {
  if (!complianceResults?.checks) return <EmptyWorkspace threadId />;

  const summary = complianceResults.summary || {};

  return (
    <section className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Compliance</span>
          <h2>Pedagogy checks</h2>
        </div>
        <div className="script-score-row">
          <span className="script-badge success">{summary.ai_passed || 0} passed</span>
          <span className="script-badge danger">{summary.ai_failed || 0} failed</span>
        </div>
      </div>

      <div className="script-check-list">
        {complianceResults.checks.map((check) => (
          <article
            className={check.ai_review ? 'script-check-row success' : 'script-check-row danger'}
            key={check.id}
          >
            <strong>{check.criteria}</strong>
            {check.ai_notes && <p>{check.ai_notes}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}

export function ReviewWorkspace({
  activeTab,
  checkpoints,
  complianceResults,
  groundingReport,
  interruptType,
  isLoading,
  isReverting,
  metadata,
  onDownload,
  onEditCell,
  onJumpToMetadata,
  onLoadCheckpoints,
  onRevert,
  onSaveOutline,
  onTabChange,
  script,
  scriptVersion,
  threadId,
}) {
  const availableTabs = [
    groundingReport ? 'validation' : null,
    metadata ? 'metadata' : null,
    script.length ? 'script' : null,
    complianceResults ? 'compliance' : null,
  ].filter(Boolean);

  const visibleTab = availableTabs.includes(activeTab) ? activeTab : availableTabs[0];

  return (
    <main className="script-review-workspace">
      {threadId && (
        <TabBar activeTab={visibleTab} availableTabs={availableTabs} onChange={onTabChange} />
      )}

      {!availableTabs.length && <EmptyWorkspace threadId={threadId} />}

      {visibleTab === 'validation' && (
        <ValidationPanel
          groundingReport={groundingReport}
          interruptType={interruptType}
          isLoading={isLoading}
          key={groundingReport?.validated_content || 'validation'}
          onSaveOutline={onSaveOutline}
        />
      )}
      {visibleTab === 'metadata' && <MetadataPanel metadata={metadata} />}
      {visibleTab === 'script' && (
        <ScriptPanel
          checkpoints={checkpoints}
          isLoading={isLoading}
          isReviewing={interruptType === 'script_review'}
          isReverting={isReverting}
          onDownload={onDownload}
          onEditCell={onEditCell}
          onJumpToMetadata={onJumpToMetadata}
          onLoadCheckpoints={onLoadCheckpoints}
          onRevert={onRevert}
          script={script}
          scriptVersion={scriptVersion}
        />
      )}
      {visibleTab === 'compliance' && <CompliancePanel complianceResults={complianceResults} />}
    </main>
  );
}
