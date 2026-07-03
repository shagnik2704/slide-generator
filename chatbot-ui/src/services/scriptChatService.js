/**
 * Service layer for the Script Chat flow.
 * Handles SSE streaming, API calls, and event parsing.
 */

const API_URL = import.meta.env.VITE_API_URL || '';
const TOKEN_KEY = 'auth_token';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/**
 * Start a new script chat session.
 * @param {string} outline - The raw outline text
 * @param {string} [fossName] - Optional FOSS name
 * @returns {Promise<{thread_id: string, message: string}>}
 */
export async function startSession(outline, fossName = null) {
  const resp = await fetch(`${API_URL}/script-chat/start`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ outline, foss_name: fossName }),
  });
  if (!resp.ok) throw new Error(`Start failed: ${resp.status}`);
  return resp.json();
}

/**
 * Connect to the SSE stream for a thread.
 * Returns a cleanup function.
 *
 * @param {string} threadId
 * @param {object} handlers - { onProgress, onToken, onInterrupt, onState, onDone, onError }
 * @returns {() => void} cleanup function
 */
export function connectStream(threadId, handlers) {
  const url = `${API_URL}/script-chat/stream/${threadId}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('progress', (e) => {
    handlers.onProgress?.(JSON.parse(e.data));
  });

  eventSource.addEventListener('token', (e) => {
    handlers.onToken?.(JSON.parse(e.data));
  });

  eventSource.addEventListener('interrupt', (e) => {
    handlers.onInterrupt?.(JSON.parse(e.data));
    eventSource.close();
  });

  eventSource.addEventListener('state', (e) => {
    handlers.onState?.(JSON.parse(e.data));
  });

  eventSource.addEventListener('done', (e) => {
    handlers.onDone?.(JSON.parse(e.data));
    eventSource.close();
  });

  eventSource.addEventListener('error', (e) => {
    // SSE spec fires 'error' on connection close too
    if (eventSource.readyState === EventSource.CLOSED) return;
    handlers.onError?.(e);
  });

  // Return cleanup
  return () => eventSource.close();
}

/**
 * Resume from an interrupt (approve / edit).
 * Returns SSE events as an async iterator.
 *
 * @param {string} threadId
 * @param {object} resumeData - { action, instruction?, edited_content?, edited_metadata? }
 * @param {object} handlers - same as connectStream
 */
export async function resumeSession(threadId, resumeData, handlers) {
  const resp = await fetch(`${API_URL}/script-chat/resume/${threadId}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(resumeData),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Resume failed: ${resp.status}`);
  }

  // Parse the SSE response body
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    while (buffer.includes('\n\n')) {
      const [rawEvent, rest] = buffer.split('\n\n', 2);
      buffer = rest;

      const lines = rawEvent.trim().split('\n');
      let eventType = 'message';
      let data = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) eventType = line.slice(7);
        else if (line.startsWith('data: ')) data = line.slice(6);
      }

      if (!data) continue;

      try {
        const parsed = JSON.parse(data);
        switch (eventType) {
          case 'progress': handlers.onProgress?.(parsed); break;
          case 'token': handlers.onToken?.(parsed); break;
          case 'interrupt': handlers.onInterrupt?.(parsed); break;
          case 'state': handlers.onState?.(parsed); break;
          case 'done': handlers.onDone?.(parsed); break;
          case 'error': handlers.onError?.(parsed); break;
        }
      } catch { /* ignore parse errors */ }
    }
  }
}

/**
 * Direct manual edit (zero tokens).
 */
export async function manualEdit(threadId, slideNumber, field, value) {
  const resp = await fetch(`${API_URL}/script-chat/edit/${threadId}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify({ slide_number: slideNumber, field, value }),
  });
  if (!resp.ok) throw new Error(`Edit failed: ${resp.status}`);
  return resp.json();
}

/**
 * Get thread history/state.
 */
export async function getHistory(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/history/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(`History failed: ${resp.status}`);
  return resp.json();
}

/**
 * Get the list of past checkpoints for the thread.
 */
export async function getCheckpoints(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/checkpoints/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(`Checkpoints failed: ${resp.status}`);
  return resp.json();
}

/**
 * Revert the state back to a past checkpoint.
 */
export async function revertState(threadId, checkpointId) {
  const resp = await fetch(`${API_URL}/script-chat/revert/${threadId}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  });
  if (!resp.ok) throw new Error(`Revert failed: ${resp.status}`);
  return resp.json();
}

/**
 * Jump back to a specific stage.
 */
export async function jumpStage(threadId, targetStage) {
  const resp = await fetch(`${API_URL}/script-chat/jump/${threadId}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ target_stage: targetStage }),
  });
  if (!resp.ok) throw new Error(`Jump failed: ${resp.status}`);
  return resp.json();
}

/**
 * Export the script to a DOCX document.
 */
export async function exportDocx(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/export-docx/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(`Export DOCX failed: ${resp.status}`);
  return resp.blob();
}
