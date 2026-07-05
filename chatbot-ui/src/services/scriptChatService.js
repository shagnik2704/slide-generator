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

async function getErrorMessage(resp, fallback) {
  const body = await resp.json().catch(() => null);
  return body?.detail || body?.message || fallback;
}

function dispatchSseEvent(eventType, rawData, handlers) {
  if (!rawData) return;
  try {
    const parsed = JSON.parse(rawData);
    switch (eventType) {
      case 'progress': handlers.onProgress?.(parsed); break;
      case 'token': handlers.onToken?.(parsed); break;
      case 'interrupt': handlers.onInterrupt?.(parsed); break;
      case 'state': handlers.onState?.(parsed); break;
      case 'done': handlers.onDone?.(parsed); break;
      case 'error': handlers.onError?.(parsed); break;
    }
  } catch {
    handlers.onError?.({ message: `Failed to parse ${eventType} event` });
  }
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
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Start failed: ${resp.status}`));
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
    dispatchSseEvent('progress', e.data, handlers);
  });

  eventSource.addEventListener('token', (e) => {
    dispatchSseEvent('token', e.data, handlers);
  });

  eventSource.addEventListener('interrupt', (e) => {
    dispatchSseEvent('interrupt', e.data, handlers);
    eventSource.close();
  });

  eventSource.addEventListener('state', (e) => {
    dispatchSseEvent('state', e.data, handlers);
  });

  eventSource.addEventListener('done', (e) => {
    dispatchSseEvent('done', e.data, handlers);
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
    throw new Error(await getErrorMessage(resp, `Resume failed: ${resp.status}`));
  }

  // Parse the SSE response body
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  let currentEvent = { type: 'message', data: '' };

  const processLine = (line) => {
    line = line.trim();
    if (!line) {
      dispatchSseEvent(currentEvent.type, currentEvent.data, handlers);
      currentEvent = { type: 'message', data: '' };
      return;
    }

    if (line.startsWith('event: ')) {
      currentEvent.type = line.slice(7);
    } else if (line.startsWith('data: ')) {
      currentEvent.data = currentEvent.data 
        ? currentEvent.data + '\n' + line.slice(6)
        : line.slice(6);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    
    const decoded = decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer += decoded;

    buffer = buffer.replace(/\r\n/g, '\n');
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      processLine(line);
    }

    if (done) {
      if (buffer.trim()) {
        processLine(buffer);
      }
      processLine('');
      break;
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
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Edit failed: ${resp.status}`));
  return resp.json();
}

/**
 * Get thread history/state.
 */
export async function getHistory(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/history/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `History failed: ${resp.status}`));
  return resp.json();
}

/**
 * Get the list of past checkpoints for the thread.
 */
export async function getCheckpoints(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/checkpoints/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Checkpoints failed: ${resp.status}`));
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
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Revert failed: ${resp.status}`));
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
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Jump failed: ${resp.status}`));
  return resp.json();
}

/**
 * Export the script to a DOCX document.
 */
export async function exportDocx(threadId) {
  const resp = await fetch(`${API_URL}/script-chat/export-docx/${threadId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) throw new Error(await getErrorMessage(resp, `Export DOCX failed: ${resp.status}`));
  return resp.blob();
}
