import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  startSession,
  connectStream,
  resumeSession,
  manualEdit,
  getCheckpoints,
  revertState,
  jumpStage,
  exportDocx
} from '../services/scriptChatService';
import ReactMarkdown from 'react-markdown';

/* ───────────────────── Stage Definitions ───────────────────── */
const STAGES = [
  { key: 'ingest', label: 'Parsing' },
  { key: 'grounding', label: 'Validating' },
  { key: 'metadata', label: 'Metadata' },
  { key: 'generate', label: 'Generating' },
  { key: 'review', label: 'Reviewing' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'done', label: 'Done' },
];

function stageIndex(stage) {
  const map = {
    ingest: 0, grounding: 1, metadata: 2, generate: 3,
    review: 4, edit: 4, compliance: 5, done: 6, error: -1,
  };
  return map[stage] ?? -1;
}

/* ───────────────────── Progress Stepper ───────────────────── */
function ProgressStepper({ currentStage }) {
  const idx = stageIndex(currentStage);
  return (
    <div style={styles.stepper}>
      {STAGES.map((s, i) => {
        const isComplete = i < idx;
        const isActive = i === idx;
        return (
          <React.Fragment key={s.key}>
            <div style={{
              ...styles.stepDot,
              ...(isComplete ? styles.stepComplete : {}),
              ...(isActive ? styles.stepActive : {}),
            }}>
              {isComplete ? '✓' : i + 1}
            </div>
            <span style={{
              ...styles.stepLabel,
              ...(isActive ? { color: 'var(--accent-primary)', fontWeight: 600 } : {}),
              ...(isComplete ? { color: 'var(--text-secondary)' } : {}),
            }}>{s.label}</span>
            {i < STAGES.length - 1 && (
              <div style={{
                ...styles.stepLine,
                ...(isComplete ? { background: 'var(--accent-primary)' } : {}),
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ───────────────────── Formatting Helpers ───────────────────── */
const wikiToHtml = (text) => {
  if (!text) return '';
  let html = text;
  // Convert **text** or '''text''' to bold HTML
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/'''([^']+)'''/g, '<strong>$1</strong>');
  // Convert newlines to <br>
  html = html.replace(/\n/g, '<br>');
  return html;
};

const htmlToWiki = (html) => {
  if (!html) return '';
  let text = html;
  // Convert bold tags to markdown style bold
  text = text.replace(/<strong>([^<]+)<\/strong>/gi, '**$1**');
  text = text.replace(/<b>([^<]+)<\/b>/gi, '**$1**');
  // Convert <br> to newlines
  text = text.replace(/<br\s*\/?>/gi, '\n');
  // Remove remaining HTML tags
  text = text.replace(/<[^>]+>/g, '');
  // Decode HTML entities
  const textarea = document.createElement('textarea');
  textarea.innerHTML = text;
  return textarea.value;
};

/* ───────────────────── Editable Table Cell ───────────────────── */
function EditableCell({ value, onChange, editable, style }) {
  const cellRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);

  // Sync state changes with contentEditable innerHTML when blurred
  useEffect(() => {
    if (cellRef.current && !isFocused) {
      cellRef.current.innerHTML = wikiToHtml(value);
    }
  }, [value, isFocused]);

  const handleBlur = () => {
    setIsFocused(false);
    if (cellRef.current) {
      const newValue = htmlToWiki(cellRef.current.innerHTML);
      if (newValue !== value) {
        onChange(newValue);
      }
    }
  };

  const handleKeyDown = (e) => {
    // Command/Ctrl + B shortcut for bolding text
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      document.execCommand('bold', false, null);
    }
  };

  return (
    <td
      ref={cellRef}
      contentEditable={editable}
      suppressContentEditableWarning
      onFocus={() => setIsFocused(true)}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      style={{
        ...style,
        outline: isFocused ? '2px solid var(--accent-primary)' : 'none',
        outlineOffset: '-2px',
        cursor: editable ? 'text' : 'default',
      }}
    />
  );
}

/* ───────────────────── Script Table ───────────────────── */
function ScriptTable({ script, onEditCell, editable }) {
  if (!script || script.length === 0) return null;
  return (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={{ ...styles.th, width: '40px' }}>#</th>
            <th style={{ ...styles.th, width: '120px' }}>Type</th>
            <th style={styles.th}>Visual Cue</th>
            <th style={styles.th}>Narration</th>
          </tr>
        </thead>
        <tbody>
          {script.map((slide) => (
            <tr key={slide.slide_number} style={styles.tr}>
              <td style={styles.td}>{slide.slide_number}</td>
              <td style={{ ...styles.td, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {slide.slide_type}
              </td>
              <EditableCell
                value={slide.visual_cue}
                onChange={(val) => onEditCell(slide.slide_number, 'visual_cue', val)}
                editable={editable}
                style={styles.tdEditable}
              />
              <EditableCell
                value={slide.narration}
                onChange={(val) => onEditCell(slide.slide_number, 'narration', val)}
                editable={editable}
                style={styles.tdEditable}
              />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ───────────────────── Compliance Report ───────────────────── */
function ComplianceReport({ results }) {
  if (!results || !results.checks) return null;
  const { checks, summary } = results;
  return (
    <div style={styles.complianceWrap}>
      <div style={styles.complianceSummary}>
        <span style={{ color: '#22c55e', fontWeight: 700 }}>✅ {summary.ai_passed}</span>
        <span style={{ color: '#ef4444', fontWeight: 700 }}>❌ {summary.ai_failed}</span>
        <span style={{ color: 'var(--text-secondary)' }}> / {summary.total} checks</span>
      </div>
      <div style={styles.checksList}>
        {checks.map((c) => (
          <div key={c.id} style={{
            ...styles.checkRow,
            borderLeft: `3px solid ${c.ai_review ? '#22c55e' : '#ef4444'}`,
          }}>
            <div style={styles.checkCriteria}>
              {c.ai_review ? '✅' : '❌'} {c.criteria}
            </div>
            {c.ai_notes && (
              <div style={styles.checkNotes}>{c.ai_notes}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────── Main Page ───────────────────── */
export default function ScriptChatPage() {
  // State
  const [threadId, setThreadId] = useState(null);
  const [outline, setOutline] = useState('');
  const [currentStage, setCurrentStage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');

  // HITL review data
  const [interruptData, setInterruptData] = useState(null);
  const [interruptType, setInterruptType] = useState(null);

  // Script & compliance
  const [script, setScript] = useState(null);
  const [scriptVersion, setScriptVersion] = useState(0);
  const [complianceResults, setComplianceResults] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [groundingReport, setGroundingReport] = useState(null);

  // Edit instruction
  const [editInput, setEditInput] = useState('');

  // Chat log
  const [chatLog, setChatLog] = useState([]);
  const [activeTab, setActiveTab] = useState('validation');
  
  // Time Travel
  const [checkpoints, setCheckpoints] = useState([]);
  const [isReverting, setIsReverting] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatLog]);

  const addChat = useCallback((role, content) => {
    setChatLog((prev) => [...prev, { role, content, ts: Date.now() }]);
  }, []);

  /* ─── SSE Handlers ─── */
  const sseHandlers = useCallback(() => ({
    onProgress: (data) => {
      setProgressMsg(data.status || '');
    },
    onState: (data) => {
      const nodeToStage = {
        ingest: 'ingest', ground: 'grounding', ground_review: 'grounding',
        metadata: 'metadata', metadata_review: 'metadata',
        generate: 'generate', script_review: 'review',
        edit: 'review', compliance: 'compliance', compliance_review: 'compliance',
      };
      const stage = nodeToStage[data.node] || data.node;
      setCurrentStage(stage);
    },
    onInterrupt: (data) => {
      setIsLoading(false);
      setProgressMsg('');
      setInterruptType(data.type);
      setInterruptData(data);

      if (data.type === 'validation_review') {
        setGroundingReport(data.report);
        setCurrentStage('grounding');
        setActiveTab('validation');
        addChat('agent', `✅ Validation complete. ${data.report?.corrections_made?.length || 0} corrections found.`);
      } else if (data.type === 'metadata_review') {
        setMetadata(data.metadata);
        setCurrentStage('metadata');
        setActiveTab('metadata');
        addChat('agent', `📋 Metadata extracted: "${data.metadata?.title}"`);
      } else if (data.type === 'script_review') {
        setScript(data.script);
        setScriptVersion((v) => v + 1);
        setCurrentStage('review');
        setActiveTab('script');
        
        const fallbackMsg = `📝 Script generated with ${data.script?.length || 0} slides (v${scriptVersion + 1})`;
        addChat('agent', data.message || fallbackMsg);
      } else if (data.type === 'compliance_review') {
        setComplianceResults(data.results);
        setCurrentStage('compliance');
        setActiveTab('compliance');
        const s = data.summary || {};
        addChat('agent', `🔍 Compliance: ${s.ai_passed}/${s.total} checks passed`);
      }
    },
    onDone: (data) => {
      setIsLoading(false);
      setCurrentStage('done');
      addChat('agent', '🎉 Workflow complete!');
    },
    onError: (err) => {
      setIsLoading(false);
      addChat('agent', `❌ Error: ${err?.message || 'Connection lost'}`);
    },
  }), [addChat, scriptVersion]);

  /* ─── Start Session ─── */
  const handleStart = async () => {
    if (!outline.trim()) return;
    setIsLoading(true);
    setCurrentStage('ingest');
    addChat('user', outline);
    addChat('agent', '🚀 Starting script generation...');

    try {
      const { thread_id } = await startSession(outline);
      setThreadId(thread_id);
      connectStream(thread_id, sseHandlers());
    } catch (err) {
      setIsLoading(false);
      addChat('agent', `❌ Failed to start: ${err.message}`);
    }
  };

  /* ─── Resume (Approve / Edit) ─── */
  const handleResume = async (action, instruction = '') => {
    if (!threadId) return;
    setIsLoading(true);
    setInterruptData(null);
    setInterruptType(null);

    const resumeData = { action };
    if (action === 'edit' && instruction) {
      resumeData.instruction = instruction;
      addChat('user', `✏️ Edit: ${instruction}`);
    } else if (action === 'approve') {
      addChat('user', '✅ Approved');
    }

    try {
      await resumeSession(threadId, resumeData, sseHandlers());
    } catch (err) {
      setIsLoading(false);
      addChat('agent', `❌ Resume failed: ${err.message}`);
    }
  };

  /* ─── Manual Cell Edit ─── */
  const handleCellEdit = async (slideNumber, field, value) => {
    if (!threadId) return;
    try {
      await manualEdit(threadId, slideNumber, field, value);
      // Update local state
      setScript((prev) =>
        prev.map((s) =>
          s.slide_number === slideNumber ? { ...s, [field]: value } : s
        )
      );
    } catch (err) {
      addChat('agent', `⚠️ Manual edit failed: ${err.message}`);
    }
  };

  /* ─── Render ─── */
  const isReviewing = interruptType === 'script_review';
  const showStartScreen = !threadId;

  return (
    <div style={styles.page}>
      {/* ── Header ── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <a href="/create" style={styles.backLink}>← Back</a>
          <h1 style={styles.title}>Script Chat</h1>
        </div>
        {currentStage && <ProgressStepper currentStage={currentStage} />}
      </header>

      {/* ── Main Content ── */}
      <div style={styles.main}>
        {/* ── Left: Chat Panel ── */}
        <div style={styles.chatPanel}>
          {/* Chat messages */}
          <div style={styles.chatMessages}>
            {showStartScreen && (
              <div style={styles.welcome}>
                <h2 style={styles.welcomeTitle}>📝 Create a Spoken Tutorial Script</h2>
                <p style={styles.welcomeDesc}>
                  Paste your outline below. The agent will validate it against the latest docs,
                  extract metadata, and generate a pedagogically aligned script.
                </p>
              </div>
            )}
            {chatLog.map((msg, i) => (
              <div key={i} style={{
                ...styles.chatBubble,
                ...(msg.role === 'user' ? styles.chatUser : styles.chatAgent),
              }}>
                <span style={styles.chatRole}>{msg.role === 'user' ? 'You' : 'Agent'}</span>
                <div style={styles.chatContent}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            {isLoading && (
              <div style={styles.chatBubble}>
                <div style={styles.loadingDots}>
                  <span style={styles.dot} /><span style={styles.dot} /><span style={styles.dot} />
                </div>
                {progressMsg && <span style={styles.progressText}>{progressMsg}</span>}
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* ── Input Area ── */}
          {showStartScreen ? (
            <div style={styles.inputArea}>
              <textarea
                value={outline}
                onChange={(e) => setOutline(e.target.value)}
                placeholder="Paste your tutorial outline here..."
                style={styles.textarea}
                rows={6}
              />
              <button onClick={handleStart} style={styles.primaryBtn} disabled={!outline.trim()}>
                🚀 Generate Script
              </button>
            </div>
          ) : interruptData ? (
            <div style={styles.inputArea}>
              <div style={styles.hitlBar}>
                {(interruptType === 'script_review' || interruptType === 'metadata_review') && (
                  <div style={styles.editRow}>
                    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '8px' }}>
                      {interruptType === 'script_review' && (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
                          <button
                            style={styles.historyBtn}
                            onClick={async () => {
                              try {
                                const res = await getCheckpoints(threadId);
                                setCheckpoints(res.checkpoints);
                              } catch (err) {
                                alert("Failed to load checkpoints: " + err.message);
                              }
                            }}
                          >
                            🔄 Version History
                          </button>
                          
                          {checkpoints.length > 0 && (
                            <select 
                              style={styles.historySelect}
                              onChange={async (e) => {
                                if(!e.target.value) return;
                                if(!confirm("Revert to this version? Your current edits will be overwritten.")) {
                                  e.target.value = "";
                                  return;
                                }
                                setIsReverting(true);
                                try {
                                  await revertState(threadId, e.target.value);
                                  setCheckpoints([]);
                                  const handlers = sseHandlers();
                                  connectStream(threadId, handlers);
                                } catch (err) {
                                  alert(err.message);
                                }
                                setIsReverting(false);
                              }}
                            >
                              <option value="">Select version to revert...</option>
                              {checkpoints.map(cp => (
                                <option key={cp.checkpoint_id} value={cp.checkpoint_id}>
                                  Version {cp.version} ({new Date(cp.timestamp).toLocaleTimeString()})
                                </option>
                              ))}
                            </select>
                          )}
                          
                          <button
                            style={styles.jumpBtn}
                            onClick={async () => {
                              if (!confirm("Jump back to Metadata Review? This will discard unapproved script changes.")) return;
                              setIsLoading(true);
                              try {
                                await jumpStage(threadId, 'metadata_review');
                                const handlers = sseHandlers();
                                connectStream(threadId, handlers);
                              } catch (err) {
                                alert(err.message);
                              }
                              setIsLoading(false);
                            }}
                            disabled={isLoading}
                          >
                            ⬅ Back to Metadata
                          </button>
                        </div>
                      )}
                      
                      <div style={{ display: 'flex', width: '100%', gap: '8px' }}>
                        <textarea
                      value={editInput}
                      onChange={(e) => setEditInput(e.target.value)}
                      placeholder={
                        interruptType === 'metadata_review'
                          ? "Describe metadata edit (e.g., 'Change title to...')..."
                          : "Describe script edit (e.g., 'Split slide 5 into two')..."
                      }
                      style={styles.editInput}
                      rows={2}
                      onKeyDown={(e) => {
                        // Enter without modifiers submits the form
                        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                          e.preventDefault();
                          if (editInput.trim()) {
                            handleResume('edit', editInput);
                            setEditInput('');
                          }
                        }
                        // Cmd + Shift or Ctrl + Shift or Shift + Enter inserts a newline (default textarea behavior for modifiers)
                      }}
                    />
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        if (editInput.trim()) {
                          handleResume('edit', editInput);
                          setEditInput('');
                        }
                      }}
                      style={styles.editBtn}
                      disabled={!editInput.trim()}
                    >
                      ✏️ Edit
                      </button>
                    </div>
                  </div>
                </div>
                )}
                <div style={styles.actionBtns}>
                  <button onClick={() => handleResume('approve')} style={styles.approveBtn}>
                    ✅ Approve
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* ── Right: Script / Review Panel ── */}
        <div style={styles.reviewPanel}>
          {/* Tab buttons */}
          {threadId && (
            <div style={styles.tabContainer}>
              <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
                <button

                style={{
                  ...styles.tabBtn,
                  ...(activeTab === 'validation' ? styles.activeTabBtn : {}),
                }}
                onClick={() => setActiveTab('validation')}
              >
                🔍 Validation
              </button>
              <button
                style={{
                  ...styles.tabBtn,
                  ...(!metadata ? styles.disabledTabBtn : {}),
                  ...(activeTab === 'metadata' ? styles.activeTabBtn : {}),
                }}
                onClick={() => metadata && setActiveTab('metadata')}
                disabled={!metadata}
              >
                📋 Metadata
              </button>
              <button
                style={{
                  ...styles.tabBtn,
                  ...(!script ? styles.disabledTabBtn : {}),
                  ...(activeTab === 'script' ? styles.activeTabBtn : {}),
                }}
                onClick={() => script && setActiveTab('script')}
                disabled={!script}
              >
                📝 Script
              </button>
              <button
                style={{
                  ...styles.tabBtn,
                  ...(!complianceResults ? styles.disabledTabBtn : {}),
                  ...(activeTab === 'compliance' ? styles.activeTabBtn : {}),
                }}
                onClick={() => complianceResults && setActiveTab('compliance')}
                disabled={!complianceResults}
              >
                ✅ Compliance
              </button>
              </div>

              {activeTab === 'script' && (
                <button
                  style={styles.downloadBtn}
                  onClick={async () => {
                    try {
                      setIsLoading(true);
                      const blob = await exportDocx(threadId);
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      const titleSlug = (metadata?.title || 'script').toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
                      a.download = `${titleSlug}_script.docx`;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      window.URL.revokeObjectURL(url);
                    } catch (err) {
                      alert("Export failed: " + err.message);
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  disabled={isLoading}
                >
                  📥 Download DOCX
                </button>
              )}
            </div>
          )}

          {/* Right Panel Content */}
          {activeTab === 'validation' && groundingReport && (
            <div style={styles.reviewCard}>
              <h3 style={styles.reviewTitle}>🔍 Grounding Report</h3>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
                <p style={{
                  ...styles.badge,
                  background: groundingReport.is_mostly_correct ? '#dcfce7' : '#fee2e2',
                  color: groundingReport.is_mostly_correct ? '#166534' : '#991b1b',
                  margin: 0,
                }}>
                  {groundingReport.is_mostly_correct ? '✅ Mostly Correct' : '⚠️ Issues Found'}
                </p>
              </div>

              {/* Show the actual validated content outline */}
              {groundingReport.validated_content && (
                <div style={{ ...styles.section, marginBottom: '20px' }}>
                  <h4 style={styles.sectionTitle}>Validated Outline Content</h4>
                  <pre style={styles.validatedOutlinePre}>{groundingReport.validated_content}</pre>
                </div>
              )}

              {groundingReport.corrections_made?.length > 0 && (
                <div style={styles.section}>
                  <h4 style={styles.sectionTitle}>Corrections</h4>
                  <ul style={styles.list}>
                    {groundingReport.corrections_made.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              )}
              {groundingReport.warnings?.length > 0 && (
                <div style={styles.section}>
                  <h4 style={styles.sectionTitle}>Warnings</h4>
                  <ul style={styles.list}>
                    {groundingReport.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === 'metadata' && metadata && (
            <div style={styles.reviewCard}>
              <h3 style={styles.reviewTitle}>📋 Extracted Metadata</h3>
              <div style={styles.metaGrid}>
                <div><strong>Title:</strong> {metadata.title}</div>
                <div><strong>Prerequisites:</strong> {metadata.prerequisites}</div>
                <div><strong>Objectives:</strong>
                  <ul style={styles.list}>
                    {metadata.learning_objectives?.map((o, i) => <li key={i}>{o}</li>)}
                  </ul>
                </div>
                <div><strong>Tags:</strong> {metadata.meta_tags?.join(', ')}</div>
              </div>
            </div>
          )}

          {activeTab === 'script' && script && (
            <div style={styles.reviewCard}>
              <div style={styles.scriptHeader}>
                <h3 style={styles.reviewTitle}>📝 Script (v{scriptVersion})</h3>
                <span style={styles.slideCount}>{script.length} slides</span>
              </div>
              <ScriptTable
                script={script}
                onEditCell={handleCellEdit}
                editable={isReviewing}
              />
            </div>
          )}

          {activeTab === 'compliance' && complianceResults && (
            <div style={styles.reviewCard}>
              <h3 style={styles.reviewTitle}>🔍 Compliance Report</h3>
              <ComplianceReport results={complianceResults} />
            </div>
          )}

          {!interruptData && !script && (
            <div style={styles.emptyPanel}>
              <span style={styles.emptyIcon}>📄</span>
              <p>Your generated script and reports will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ───────────────────── Styles ───────────────────── */
const styles = {
  page: {
    display: 'flex', flexDirection: 'column', height: '100vh',
    background: 'var(--bg-primary)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-sans)',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '12px 24px', borderBottom: '1px solid var(--border-color)',
    background: 'var(--bg-secondary)',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '16px' },
  backLink: {
    color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.875rem',
    transition: 'color 0.2s',
  },
  title: { fontSize: '1.25rem', fontWeight: 700, margin: 0 },

  /* Stepper */
  stepper: {
    display: 'flex', alignItems: 'center', gap: '6px',
  },
  stepDot: {
    width: 24, height: 24, borderRadius: '50%', display: 'flex',
    alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem',
    fontWeight: 600, background: 'var(--bg-tertiary)', color: 'var(--text-secondary)',
    transition: 'all 0.3s ease',
  },
  stepComplete: {
    background: 'var(--accent-primary)', color: '#fff',
  },
  stepActive: {
    background: 'var(--accent-secondary)', color: '#fff',
    boxShadow: '0 0 12px var(--accent-glow)',
    animation: 'pulse 2s infinite',
  },
  stepLabel: { fontSize: '0.7rem', color: 'var(--text-secondary)' },
  stepLine: {
    width: 20, height: 2, background: 'var(--border-color)',
    borderRadius: 1, transition: 'background 0.3s',
  },

  /* Main layout */
  main: {
    display: 'flex', flex: 1, overflow: 'hidden',
  },

  /* Chat panel */
  chatPanel: {
    width: '40%', minWidth: 340, display: 'flex', flexDirection: 'column',
    borderRight: '1px solid var(--border-color)',
  },
  chatMessages: {
    flex: 1, overflowY: 'auto', padding: '20px',
    display: 'flex', flexDirection: 'column', gap: '12px',
  },
  chatBubble: {
    padding: '12px 16px', borderRadius: '12px',
    background: 'var(--bg-secondary)', maxWidth: '90%',
    animation: 'fadeIn 0.2s ease',
  },
  chatUser: {
    alignSelf: 'flex-end', background: 'var(--accent-primary)', color: '#fff',
    borderBottomRightRadius: 4,
  },
  chatAgent: {
    alignSelf: 'flex-start', borderBottomLeftRadius: 4,
  },
  chatRole: {
    fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase',
    opacity: 0.6, display: 'block', marginBottom: 4,
  },
  chatContent: { fontSize: '0.875rem', lineHeight: 1.5, whiteSpace: 'pre-wrap' },

  /* Loading */
  loadingDots: { display: 'flex', gap: 4, padding: '4px 0' },
  dot: {
    width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-primary)',
    animation: 'bounce 1.4s infinite ease-in-out',
  },
  progressText: {
    fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4,
    display: 'block',
  },

  /* Input area */
  inputArea: { padding: '16px 20px', borderTop: '1px solid var(--border-color)' },
  textarea: {
    width: '100%', padding: '12px', borderRadius: 8, border: '1px solid var(--border-color)',
    background: 'var(--bg-secondary)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-sans)', fontSize: '0.875rem', resize: 'vertical',
    outline: 'none', transition: 'border-color 0.2s',
  },
  primaryBtn: {
    marginTop: 12, width: '100%', padding: '12px', borderRadius: 8,
    background: 'var(--accent-primary)', color: '#fff', border: 'none',
    fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer',
    transition: 'transform 0.15s, box-shadow 0.15s',
    fontFamily: 'var(--font-sans)',
  },

  /* HITL bar */
  hitlBar: { display: 'flex', flexDirection: 'column', gap: 10 },
  editRow: { display: 'flex', gap: 8 },
  editInput: {
    flex: 1, padding: '10px 12px', borderRadius: 8,
    border: '1px solid var(--border-color)', background: 'var(--bg-secondary)',
    color: 'var(--text-primary)', fontFamily: 'var(--font-sans)', fontSize: '0.875rem',
    outline: 'none', resize: 'vertical', minHeight: '60px',
  },
  editBtn: {
    padding: '10px 18px', borderRadius: 8, background: 'var(--accent-secondary)',
    color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer',
    fontFamily: 'var(--font-sans)', whiteSpace: 'nowrap',
  },
  actionBtns: { display: 'flex', gap: 8 },
  approveBtn: {
    flex: 1, padding: '12px', borderRadius: 8,
    background: '#22c55e', color: '#fff', border: 'none',
    fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer',
    fontFamily: 'var(--font-sans)', transition: 'transform 0.15s',
  },

  /* Review panel */
  reviewPanel: {
    flex: 1, overflowY: 'auto', padding: '20px',
    display: 'flex', flexDirection: 'column', gap: '16px',
  },
  reviewCard: {
    background: 'var(--bg-secondary)', borderRadius: 12, padding: '20px',
    border: '1px solid var(--border-color)', boxShadow: 'var(--shadow-sm)',
  },
  reviewTitle: { fontSize: '1rem', fontWeight: 700, marginBottom: 12 },
  scriptHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
  },
  slideCount: {
    fontSize: '0.75rem', background: 'var(--accent-primary)', color: '#fff',
    padding: '2px 10px', borderRadius: 99,
  },

  /* Metadata */
  metaGrid: { display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.875rem' },
  badge: {
    display: 'inline-block', padding: '4px 12px', borderRadius: 99,
    fontSize: '0.8rem', fontWeight: 600, marginBottom: 12,
  },
  section: { marginTop: 12 },
  sectionTitle: { fontSize: '0.85rem', fontWeight: 600, marginBottom: 6 },
  list: { paddingLeft: 20, fontSize: '0.85rem', lineHeight: 1.7 },

  /* Script table */
  tableWrap: { overflowX: 'auto', maxHeight: 500, overflowY: 'auto' },
  table: {
    width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem',
  },
  th: {
    textAlign: 'left', padding: '8px 10px', fontWeight: 600,
    borderBottom: '2px solid var(--border-color)',
    position: 'sticky', top: 0, background: 'var(--bg-secondary)', zIndex: 1,
    fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)',
  },
  tr: { borderBottom: '1px solid var(--border-color)' },
  td: { padding: '8px 10px', verticalAlign: 'top' },
  tdEditable: {
    padding: '8px 10px', verticalAlign: 'top',
    outline: 'none', cursor: 'text', borderRadius: 4,
    transition: 'background 0.2s',
  },

  /* Compliance */
  complianceWrap: {},
  complianceSummary: {
    display: 'flex', gap: 12, marginBottom: 16, fontSize: '1rem',
  },
  checksList: { display: 'flex', flexDirection: 'column', gap: 6 },
  checkRow: {
    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: 6,
  },
  checkCriteria: { fontSize: '0.8rem', fontWeight: 500 },
  checkNotes: { fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 },

  /* Welcome */
  welcome: { textAlign: 'center', padding: '60px 20px' },
  welcomeTitle: { fontSize: '1.5rem', fontWeight: 700, marginBottom: 12 },
  welcomeDesc: { color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: 450, margin: '0 auto' },

  /* Empty panel */
  emptyPanel: {
    flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', color: 'var(--text-secondary)',
  },
  emptyIcon: { fontSize: '3rem', opacity: 0.3, marginBottom: 12 },

  /* Tab system */
  tabContainer: {
    display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)',
    paddingBottom: '12px', marginBottom: '16px',
  },
  tabBtn: {
    padding: '8px 16px', borderRadius: '6px', border: 'none',
    background: 'var(--bg-tertiary)', color: 'var(--text-secondary)',
    fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
    fontFamily: 'var(--font-sans)', transition: 'all 0.2s ease',
  },
  activeTabBtn: {
    background: 'var(--accent-primary)', color: '#fff',
  },
  disabledTabBtn: {
    opacity: 0.4, cursor: 'not-allowed',
  },
  validatedOutlinePre: {
    whiteSpace: 'pre-wrap', fontFamily: 'var(--font-sans)', fontSize: '0.85rem',
    background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px',
    border: '1px solid var(--border-color)', lineHeight: 1.5,
    maxHeight: '300px', overflowY: 'auto', margin: 0,
  },
  jumpBtn: {
    padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border-color)',
    background: 'var(--bg-tertiary)', color: 'var(--accent-primary)',
    fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
    fontFamily: 'var(--font-sans)', transition: 'all 0.2s ease',
  },
  historyBtn: {
    padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border-color)',
    background: 'var(--bg-tertiary)', color: 'var(--text-secondary)',
    fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
    fontFamily: 'var(--font-sans)', transition: 'all 0.2s ease',
  },
  historySelect: {
    padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)',
    background: 'var(--bg-primary)', color: 'var(--text-primary)',
    fontWeight: 500, fontSize: '0.85rem', cursor: 'pointer', outline: 'none',
    fontFamily: 'var(--font-sans)',
  },
  downloadBtn: {
    padding: '8px 16px', borderRadius: '6px', border: 'none',
    background: 'var(--accent-primary)', color: '#fff',
    fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
    fontFamily: 'var(--font-sans)', transition: 'all 0.2s ease',
  },
};
