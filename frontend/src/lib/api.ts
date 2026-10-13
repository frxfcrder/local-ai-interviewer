import type {
  ChatMessage,
  HealthStatus,
  InterviewSession,
  SessionMessage,
} from '../types/interview';

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthStatus> {
  return fetch('/health').then(json<HealthStatus>);
}

export function createSession(roleType: string, userId?: string): Promise<InterviewSession> {
  return fetch('/api/interview/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role_type: roleType, ...(userId ? { user_id: userId } : {}) }),
  }).then(json<InterviewSession>);
}

export function getSession(id: string): Promise<InterviewSession> {
  return fetch(`/api/interview/sessions/${id}`).then(json<InterviewSession>);
}

export function getHistory(id: string): Promise<SessionMessage[]> {
  return fetch(`/api/interview/sessions/${id}/history`).then(json<SessionMessage[]>);
}

export function completeSession(id: string): Promise<InterviewSession> {
  return fetch(`/api/interview/sessions/${id}/complete`, { method: 'POST' }).then(
    json<InterviewSession>,
  );
}

/** Streams an SSE chat reply, yielding content chunks. Stops at `data: [DONE]`. */
export async function* streamChat(
  messages: ChatMessage[],
  interviewId?: string,
): AsyncGenerator<string> {
  const res = await fetch('/api/interview/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      ...(interviewId ? { interview_id: interviewId } : {}),
    }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const payload = line.slice('data:'.length).trim();
      if (payload === '[DONE]') return;
      yield (JSON.parse(payload) as { content: string }).content;
    }
  }
}

export function transcribe(blob: Blob, filename = 'turn.webm'): Promise<{ transcript: string }> {
  const form = new FormData();
  form.append('file', blob, filename);
  return fetch('/api/interview/transcribe', { method: 'POST', body: form }).then(
    json<{ transcript: string }>,
  );
}

export function synthesize(text: string, outputFilename?: string): Promise<{ audio_url: string }> {
  return fetch('/api/interview/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      ...(outputFilename ? { output_filename: outputFilename } : {}),
    }),
  }).then(json<{ audio_url: string }>);
}

export function deleteAudio(filename: string): Promise<void> {
  return fetch(`/api/interview/audio/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  }).then(async (res) => {
    if (![200, 204, 404].includes(res.status)) {
      throw new Error(`delete audio failed: ${res.status}`);
    }
  });
}

export function evaluate(chatHistory: ChatMessage[]): Promise<{ evaluation: string }> {
  return fetch('/api/interview/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_history: chatHistory }),
  }).then(json<{ evaluation: string }>);
}

export function greet(sessionId: string): Promise<{ text: string; audio_url: string }> {
  return fetch(`/api/interview/sessions/${sessionId}/greet`, { method: 'POST' }).then(
    json<{ text: string; audio_url: string }>,
  );
}
