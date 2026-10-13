import { useCallback, useEffect, useState } from 'react';
import VoiceTurn from '../components/VoiceTurn';
import { completeSession, createSession, evaluate, getHealth, getHistory, greet } from '../lib/api';
import type { ChatMessage, HealthStatus, InterviewSession, SessionMessage } from '../types/interview';

export default function InterviewPage(): React.JSX.Element {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [roleInput, setRoleInput] = useState('');
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [greeting, setGreeting] = useState<{ text: string; audio_url: string } | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch((err: unknown) => {
      setHealthError(err instanceof Error ? err.message : 'Unreachable');
    });
  }, []);

  const refreshHistory = useCallback(async () => {
    if (!session) return;
    setMessages(await getHistory(session.id));
  }, [session]);

  useEffect(() => {
    refreshHistory().catch(() => undefined);
  }, [refreshHistory]);

  async function newSession(): Promise<void> {
    setBusy(true);
    try {
      const created = await createSession(roleInput.trim() || undefined);
      setSession(created);
      setMessages([]);
      setGreeting(null);
      setReport(null);
      const hello = await greet(created.id);
      setGreeting(hello);
      setMessages(await getHistory(created.id));
    } finally {
      setBusy(false);
    }
  }

  async function finish(): Promise<void> {
    if (!session) return;
    setSession(await completeSession(session.id));
  }

  async function runEvaluation(): Promise<void> {
    if (!session) return;
    setBusy(true);
    try {
      const chat: ChatMessage[] = messages.map((m) => ({
        role: m.sender === 'interviewer' ? 'assistant' : 'user',
        content: m.transcript,
      }));
      setReport((await evaluate(chat)).evaluation);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ fontFamily: 'system-ui', padding: 24, maxWidth: 680 }}>
      <h1>Local AI Interviewer</h1>
      <section>
        <h2>Backend</h2>
        {healthError ? (
          <p>Unreachable: {healthError} (is uvicorn running on :8000?)</p>
        ) : health ? (
          <p>
            {health.status} — llm: {health.services.llm}, db: {health.services.db}
          </p>
        ) : (
          <p>Checking…</p>
        )}
      </section>
      <section>
        <h2>Session</h2>
        {session ? (
          <p>
            {session.id} · {session.role_type} · {session.status}{' '}
            <button type="button" onClick={finish} disabled={busy}>
              Complete
            </button>{' '}
            <button type="button" onClick={runEvaluation} disabled={busy || messages.length === 0}>
              Evaluate
            </button>
          </p>
        ) : (
          <div>
            <label>
              Role (leave blank and the interviewer will ask you):{' '}
              <input
                type="text"
                value={roleInput}
                onChange={(e) => setRoleInput(e.target.value)}
                placeholder="e.g. Data Scientist"
                list="role-suggestions"
              />
            </label>
            <datalist id="role-suggestions">
              <option value="Senior Backend Engineer" />
              <option value="Frontend Engineer" />
              <option value="Data Scientist" />
              <option value="DevOps Engineer" />
            </datalist>{' '}
            <button type="button" onClick={newSession} disabled={busy}>
              New session
            </button>
          </div>
        )}
      </section>
      {session && (
        <section>
          <h2>Transcript</h2>
          {greeting && (
            <div>
              <audio key={greeting.audio_url} src={greeting.audio_url} controls autoPlay />
            </div>
          )}
          {messages.length === 0 ? (
            <p>No turns yet — record your first answer below.</p>
          ) : (
            messages.map((m) => (
              <p key={m.id}>
                <strong>{m.sender}:</strong> {m.transcript}
              </p>
            ))
          )}
          {session.status === 'in_progress' ? (
            <VoiceTurn sessionId={session.id} history={messages} onTurnComplete={refreshHistory} />
          ) : (
            <p>Session completed.</p>
          )}
        </section>
      )}
      {report && (
        <section>
          <h2>Evaluation</h2>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{report}</pre>
        </section>
      )}
    </main>
  );
}
