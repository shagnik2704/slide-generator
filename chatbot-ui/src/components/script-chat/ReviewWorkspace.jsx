import { useState } from 'react';
import {
  ArrowLeft,
  Download,
  FileCode,
  History,
  Pencil,
  Save,
  X,
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { SCRIPT_CHAT_TABS } from '../../lib/scriptChatContract';
import { ScriptReviewCard } from './ScriptReviewCard';

function EmptyWorkspace({ threadId }) {
  return (
    <Card className="script-empty-workspace">
      <h2>{threadId ? 'Waiting for the next review' : 'Paste an outline to begin'}</h2>
      <p>
        {threadId
          ? 'Validation reports, metadata, scripts, and compliance checks appear here as the backend reaches each review gate.'
          : 'The generated artifacts will stay in this workspace while the assistant panel handles workflow control.'}
      </p>
    </Card>
  );
}

function TabBar({ activeTab, availableTabs, onChange }) {
  return (
    <Tabs className="script-tabs-wrap" onValueChange={onChange} value={activeTab || ''}>
      <TabsList className="script-tabs" aria-label="Review artifacts">
        {SCRIPT_CHAT_TABS.map((tab) => (
          <TabsTrigger
            disabled={!availableTabs.includes(tab.key)}
            key={tab.key}
            value={tab.key}
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
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

  if (!groundingReport) return <EmptyWorkspace />;

  return (
    <Card className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Validation</span>
          <h2>Grounding report</h2>
        </div>
        <Badge
          className={groundingReport.is_mostly_correct ? 'script-badge success' : 'script-badge warning'}
          variant={groundingReport.is_mostly_correct ? 'success' : 'warning'}
        >
          {groundingReport.is_mostly_correct ? 'Mostly correct' : 'Needs attention'}
        </Badge>
      </div>

      <div className="script-section">
        <div className="script-section-header">
          <h3>Validated outline</h3>
          {interruptType === 'validation_review' && (
            isEditing ? (
              <div className="script-button-row">
                <Button
                  className="script-icon-button"
                  disabled={isLoading}
                  onClick={() => {
                    setDraft(validatedContent);
                    setIsEditing(false);
                  }}
                  size="icon"
                  title="Cancel outline edits"
                  type="button"
                  variant="outline"
                >
                  <X size={16} aria-hidden="true" />
                </Button>
                <Button
                  className="script-icon-button script-icon-button-primary"
                  disabled={isLoading || !draft.trim()}
                  onClick={async () => {
                    await onSaveOutline(draft);
                    setIsEditing(false);
                  }}
                  size="icon"
                  title="Save outline edits"
                  type="button"
                >
                  <Save size={16} aria-hidden="true" />
                </Button>
              </div>
            ) : (
              <Button
                className="script-icon-button"
                disabled={isLoading}
                onClick={() => setIsEditing(true)}
                size="icon"
                title="Edit validated outline"
                type="button"
                variant="outline"
              >
                <Pencil size={16} aria-hidden="true" />
              </Button>
            )
          )}
        </div>

        {isEditing ? (
          <Textarea
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
    </Card>
  );
}

function MetadataTableRow({ label, children }) {
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{children}</td>
    </tr>
  );
}

function MetadataPanel({ fossName, metadata }) {
  if (!metadata) return <EmptyWorkspace />;

  const learningObjectives = metadata.learning_objectives || [];
  const outlineTopics = metadata.outline_topics || [];
  const metaTags = metadata.meta_tags || [];
  const series = fossName || metadata.foss_name || 'Not specified';

  return (
    <Card className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Metadata</span>
          <h2>{metadata.title || 'Untitled tutorial'}</h2>
        </div>
      </div>

      <div className="script-metadata-table-wrap">
        <table className="script-metadata-table">
          <tbody>
            <MetadataTableRow label="Series">
              {series}
            </MetadataTableRow>
            <MetadataTableRow label="Tutorial:">
              {metadata.title || 'Untitled tutorial'}
            </MetadataTableRow>
            <MetadataTableRow label="Learning Objective:">
              <div>At the end of this tutorial learner will be able to</div>
              <ol className="script-metadata-numbered-list">
                {learningObjectives.map((objective) => (
                  <li key={objective}>{objective}</li>
                ))}
              </ol>
            </MetadataTableRow>
            <MetadataTableRow label="Outline">
              <ul className="script-metadata-bullet-list">
                {outlineTopics.map((topic) => (
                  <li key={topic}>{topic}</li>
                ))}
              </ul>
            </MetadataTableRow>
            <MetadataTableRow label="Meta Tags">
              {metaTags.join(', ')}
            </MetadataTableRow>
            <MetadataTableRow label="Pre-requisite Tutorial">
              {metadata.prerequisites || 'None listed'}
            </MetadataTableRow>
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ScriptPanel({
  checkpoints,
  isLoading,
  isReviewing,
  isReverting,
  onDownload,
  onDownloadWiki,
  onEditCell,
  onJumpToMetadata,
  onLoadCheckpoints,
  onRevert,
  script,
  scriptVersion,
}) {
  const [pendingRevertId, setPendingRevertId] = useState(null);
  const pendingCheckpoint = checkpoints.find((checkpoint) => checkpoint.checkpoint_id === pendingRevertId);

  if (!script.length) return <EmptyWorkspace />;

  return (
    <Card className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Script</span>
          <h2>Draft v{scriptVersion}</h2>
        </div>
        <div className="script-toolbar">
          <Badge className="script-badge" variant="secondary">{script.length} slides</Badge>
          <Button
            className="script-icon-button"
            disabled={isLoading}
            onClick={onLoadCheckpoints}
            size="icon"
            title="Load version history"
            type="button"
            variant="outline"
          >
            <History size={16} aria-hidden="true" />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                className="script-icon-button"
                disabled={isLoading}
                size="icon"
                title="Return to metadata review"
                type="button"
                variant="outline"
              >
                <ArrowLeft size={16} aria-hidden="true" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Return to metadata review?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will discard unapproved script changes and move the workflow back to the metadata review gate.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onJumpToMetadata}>Return</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button
            className="script-icon-button"
            disabled={isLoading}
            onClick={onDownloadWiki}
            size="icon"
            title="Download MediaWiki (.wiki)"
            type="button"
            variant="outline"
          >
            <FileCode size={16} aria-hidden="true" />
          </Button>
          <Button
            className="script-icon-button script-icon-button-primary"
            disabled={isLoading}
            onClick={onDownload}
            size="icon"
            title="Download DOCX"
            type="button"
          >
            <Download size={16} aria-hidden="true" />
          </Button>
        </div>
      </div>

      {!!checkpoints.length && (
        <div className="script-version-row">
          <Select
            disabled={isReverting}
            onValueChange={setPendingRevertId}
            value={pendingRevertId || ''}
          >
            <SelectTrigger className="script-version-select">
              <SelectValue placeholder="Revert to version..." />
            </SelectTrigger>
            <SelectContent>
              {checkpoints.map((checkpoint) => (
                <SelectItem key={checkpoint.checkpoint_id} value={checkpoint.checkpoint_id}>
                  Version {checkpoint.version} - {new Date(checkpoint.timestamp).toLocaleTimeString()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <AlertDialog
            open={Boolean(pendingRevertId)}
            onOpenChange={(open) => {
              if (!open) setPendingRevertId(null);
            }}
          >
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Revert script version?</AlertDialogTitle>
                <AlertDialogDescription>
                  {pendingCheckpoint
                    ? `Current script edits will be overwritten by version ${pendingCheckpoint.version}.`
                    : 'Current script edits will be overwritten by the selected checkpoint.'}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => {
                    if (pendingRevertId) onRevert(pendingRevertId);
                    setPendingRevertId(null);
                  }}
                >
                  Revert
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}

      <ScriptReviewCard editable={isReviewing} onEditCell={onEditCell} script={script} />
    </Card>
  );
}

function CompliancePanel({ complianceResults }) {
  if (!complianceResults?.checks) return <EmptyWorkspace />;

  const summary = complianceResults.summary || {};

  return (
    <Card className="script-artifact">
      <div className="script-artifact-header">
        <div>
          <span className="script-eyebrow">Compliance</span>
          <h2>Pedagogy checks</h2>
        </div>
        <div className="script-score-row">
          <Badge className="script-badge success" variant="success">{summary.ai_passed || 0} passed</Badge>
          <Badge className="script-badge danger" variant="danger">{summary.ai_failed || 0} failed</Badge>
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
    </Card>
  );
}

export function ReviewWorkspace({
  activeTab,
  checkpoints,
  complianceResults,
  fossName,
  groundingReport,
  interruptType,
  isLoading,
  isReverting,
  metadata,
  onDownload,
  onDownloadWiki,
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
      {visibleTab === 'metadata' && <MetadataPanel fossName={fossName} metadata={metadata} />}
      {visibleTab === 'script' && (
        <ScriptPanel
          checkpoints={checkpoints}
          isLoading={isLoading}
          isReviewing={interruptType === 'script_review'}
          isReverting={isReverting}
          onDownload={onDownload}
          onDownloadWiki={onDownloadWiki}
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
