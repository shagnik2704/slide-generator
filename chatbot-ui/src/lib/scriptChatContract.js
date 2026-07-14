import {
  CheckCircle2,
  ClipboardCheck,
  FileCheck2,
  FileText,
  ListChecks,
  SearchCheck,
  Sparkles,
} from 'lucide-react';

export const SCRIPT_CHAT_STAGES = [
  { key: 'ingest', label: 'Parse', icon: FileText },
  { key: 'grounding', label: 'Validate', icon: SearchCheck },
  { key: 'metadata', label: 'Metadata', icon: ClipboardCheck },
  { key: 'generate', label: 'Draft', icon: Sparkles },
  { key: 'review', label: 'Review', icon: ListChecks },
  { key: 'compliance', label: 'Checks', icon: FileCheck2 },
  { key: 'done', label: 'Done', icon: CheckCircle2 },
];

export const SCRIPT_CHAT_TABS = [
  { key: 'validation', label: 'Validation' },
  { key: 'metadata', label: 'Metadata' },
  { key: 'script', label: 'Script' },
  { key: 'compliance', label: 'Compliance' },
];

export const EDITABLE_SCRIPT_FIELDS = ['visual_cue', 'narration'];

export const NODE_STAGE = {
  ingest: 'ingest',
  ground: 'grounding',
  ground_review: 'grounding',
  ground_edit: 'grounding',
  validation_review: 'grounding',
  metadata: 'metadata',
  metadata_review: 'metadata',
  metadata_edit: 'metadata',
  generate: 'generate',
  script_review: 'review',
  edit: 'review',
  compliance: 'compliance',
  compliance_review: 'compliance',
  done: 'done',
  error: 'error',
};

export const INTERRUPT_TAB = {
  validation_review: 'validation',
  metadata_review: 'metadata',
  script_review: 'script',
  compliance_review: 'compliance',
};

export function getStageIndex(stage) {
  return SCRIPT_CHAT_STAGES.findIndex((item) => item.key === stage);
}

export function stageFromNode(node) {
  return NODE_STAGE[node] || node || null;
}

export function tabFromInterrupt(type) {
  return INTERRUPT_TAB[type] || 'validation';
}

export function normalizeScript(rawScript) {
  if (!Array.isArray(rawScript)) return [];
  return rawScript.map((slide, index) => ({
    slide_number: Number(slide.slide_number || index + 1),
    slide_type: slide.slide_type || '',
    visual_cue: slide.visual_cue || '',
    narration: slide.narration || '',
  }));
}
