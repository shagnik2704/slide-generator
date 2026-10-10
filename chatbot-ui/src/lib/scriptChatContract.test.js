import { describe, it, expect } from 'vitest';
import {
  SCRIPT_CHAT_STAGES,
  SCRIPT_CHAT_TABS,
  EDITABLE_SCRIPT_FIELDS,
  getStageIndex,
  stageFromNode,
  tabFromInterrupt,
  normalizeScript,
} from './scriptChatContract';

describe('scriptChatContract', () => {
  describe('Constants and definitions', () => {
    it('defines the required script chat stages in correct order', () => {
      const keys = SCRIPT_CHAT_STAGES.map((s) => s.key);
      expect(keys).toEqual([
        'ingest',
        'grounding',
        'metadata',
        'generate',
        'review',
        'compliance',
        'done',
      ]);
    });

    it('defines script chat review tabs', () => {
      const tabs = SCRIPT_CHAT_TABS.map((t) => t.key);
      expect(tabs).toContain('validation');
      expect(tabs).toContain('metadata');
      expect(tabs).toContain('script');
      expect(tabs).toContain('compliance');
    });

    it('defines allowed editable fields for zero-token slide edits', () => {
      expect(EDITABLE_SCRIPT_FIELDS).toEqual(['visual_cue', 'narration']);
    });
  });

  describe('getStageIndex', () => {
    it('returns the correct index for valid stages', () => {
      expect(getStageIndex('ingest')).toBe(0);
      expect(getStageIndex('grounding')).toBe(1);
      expect(getStageIndex('generate')).toBe(3);
      expect(getStageIndex('done')).toBe(6);
    });

    it('returns -1 for unknown stage', () => {
      expect(getStageIndex('unknown_stage')).toBe(-1);
      expect(getStageIndex(null)).toBe(-1);
    });
  });

  describe('stageFromNode', () => {
    it('maps LangGraph node names to user-facing stages', () => {
      expect(stageFromNode('ingest')).toBe('ingest');
      expect(stageFromNode('ground')).toBe('grounding');
      expect(stageFromNode('ground_review')).toBe('grounding');
      expect(stageFromNode('metadata_review')).toBe('metadata');
      expect(stageFromNode('generate')).toBe('generate');
      expect(stageFromNode('script_review')).toBe('review');
      expect(stageFromNode('edit')).toBe('review');
      expect(stageFromNode('compliance_review')).toBe('compliance');
      expect(stageFromNode('done')).toBe('done');
      expect(stageFromNode('error')).toBe('error');
    });

    it('falls back to node name or null if unmapped', () => {
      expect(stageFromNode('custom_node')).toBe('custom_node');
      expect(stageFromNode(null)).toBeNull();
    });
  });

  describe('tabFromInterrupt', () => {
    it('maps interrupt types to the corresponding UI tab', () => {
      expect(tabFromInterrupt('validation_review')).toBe('validation');
      expect(tabFromInterrupt('metadata_review')).toBe('metadata');
      expect(tabFromInterrupt('script_review')).toBe('script');
      expect(tabFromInterrupt('compliance_review')).toBe('compliance');
    });

    it('falls back to validation tab for unknown interrupts', () => {
      expect(tabFromInterrupt('unrecognized_interrupt')).toBe('validation');
      expect(tabFromInterrupt(null)).toBe('validation');
    });
  });

  describe('normalizeScript', () => {
    it('returns empty array when rawScript is invalid or non-array', () => {
      expect(normalizeScript(null)).toEqual([]);
      expect(normalizeScript(undefined)).toEqual([]);
      expect(normalizeScript('not an array')).toEqual([]);
      expect(normalizeScript({})).toEqual([]);
    });

    it('normalizes slide items with numeric slide_number and string fallbacks', () => {
      const raw = [
        {
          slide_number: '1',
          slide_type: 'title',
          visual_cue: 'Title text',
          narration: 'Hello world',
        },
        {
          slide_number: null,
          visual_cue: 'Demo visual',
        },
      ];

      const normalized = normalizeScript(raw);
      expect(normalized).toEqual([
        {
          slide_number: 1,
          slide_type: 'title',
          visual_cue: 'Title text',
          narration: 'Hello world',
        },
        {
          slide_number: 2, // falls back to index + 1
          slide_type: '',
          visual_cue: 'Demo visual',
          narration: '',
        },
      ]);
    });
  });
});
