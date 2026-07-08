import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

function markdownToInlineHtml(text) {
  if (!text) return '';
  return text
    .replace(/'''([^']+)'''/g, '<strong>$1</strong>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function htmlToMarkdown(html) {
  if (!html) return '';
  const textarea = document.createElement('textarea');
  let text = html
    .replace(/<strong>([^<]+)<\/strong>/gi, '**$1**')
    .replace(/<b>([^<]+)<\/b>/gi, '**$1**')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/div><div>/gi, '\n')
    .replace(/<\/p><p>/gi, '\n')
    .replace(/<[^>]+>/g, '');
  textarea.innerHTML = text;
  return textarea.value;
}

function ScriptMarkdown({ children }) {
  return (
    <div className="script-markdown">
      <ReactMarkdown>{children || ''}</ReactMarkdown>
    </div>
  );
}

function InlineEditableCell({ editable, field, onEditCell, slide }) {
  const cellRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);
  const value = slide[field] || '';

  useEffect(() => {
    if (cellRef.current && !isFocused) {
      cellRef.current.innerHTML = markdownToInlineHtml(value);
    }
  }, [isFocused, value]);

  if (!editable) {
    return (
      <TableCell className="script-card-cell">
        <ScriptMarkdown>{slide[field]}</ScriptMarkdown>
      </TableCell>
    );
  }

  return (
    <TableCell
      className="script-card-cell script-card-cell-editable"
      contentEditable
      onBlur={() => {
        setIsFocused(false);
        const nextValue = htmlToMarkdown(cellRef.current?.innerHTML || '');
        if (nextValue !== value) {
          onEditCell(slide.slide_number, field, nextValue);
        }
      }}
      onFocus={() => setIsFocused(true)}
      onKeyDown={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
          event.preventDefault();
          document.execCommand('bold', false, null);
        }
      }}
      ref={cellRef}
      suppressContentEditableWarning
    />
  );
}

export function ScriptReviewCard({ editable, onEditCell, script }) {
  return (
    <div className="script-review-card-table-wrap">
      <Table className="script-review-card-table">
        <TableHeader>
          <TableRow>
            <TableHead className="script-review-card-number">#</TableHead>
            <TableHead>Visual Cue</TableHead>
            <TableHead>Narration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {script.map((slide) => (
            <TableRow key={slide.slide_number}>
              <TableCell className="script-review-card-number">
                <span>{slide.slide_number}</span>
                {slide.slide_type && <small>{slide.slide_type}</small>}
              </TableCell>
              <InlineEditableCell
                editable={editable}
                field="visual_cue"
                key={`visual-${slide.slide_number}-${slide.visual_cue}`}
                onEditCell={onEditCell}
                slide={slide}
              />
              <InlineEditableCell
                editable={editable}
                field="narration"
                key={`narration-${slide.slide_number}-${slide.narration}`}
                onEditCell={onEditCell}
                slide={slide}
              />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
