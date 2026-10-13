import { useRef, useState } from 'react';
import { useRecorder } from '../hooks/useRecorder';
import { deleteAudio, streamChat, synthesize, transcribe } from '../lib/api';
import type { ChatMessage, SessionMessage } from '../types/interview';

interface VoiceTurnProps {
  sessionId: string;
  history: SessionMessage[];
  onTurnComplete: () => void;
}

function toChatRole(sender: string): 'user' | 'assistant' {
  return sender === 'interviewer' ? 'assistant' : 'user';
}

/** One voice turn: record → transcribe → stream reply → play audio. */
export default function VoiceTurn({ sessionId, history, onTurnComplete }: VoiceTurnProps): React.JSX.Element {
  const { recording, error: recError, start, stop } = useRecorder();
  const [phase, setPhase] = useState<'idle' | 'transcribing' | 'thinking' | 'speaking'>('idle');
  const [transcript, setTranscript] = useState('');
  const [reply, setReply] = useState('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastAudioRef = useRef<string | null>(null);

  async function takeTurn(): Promise<void> {
    if (recording) {
      setError(null);
      setPhase('transcribing');
      try {
        const blob = await stop();
        const { transcript: text } = await transcribe(blob);
        setTranscript(text);

        setPhase('thinking');
        const messages: ChatMessage[] = [
          ...history.map((m) => ({ role: toChatRole(m.sender), content: m.transcript }) as ChatMessage),
          { role: 'user', content: text } as ChatMessage,
        ];
        let full = '';
        for await (const chunk of streamChat(messages, sessionId)) {
          full += chunk;
          setReply(full);
        }
        if (!full.trim()) throw new Error('Empty reply from interviewer');

        setPhase('speaking');
        if (lastAudioRef.current) {
          await deleteAudio(lastAudioRef.current).catch(() => undefined);
        }
        const { audio_url } = await synthesize(full);
        lastAudioRef.current = audio_url.split('/').pop() ?? null;
        setAudioUrl(audio_url);
        onTurnComplete();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Turn failed');
      } finally {
        setPhase('idle');
      }
    } else {
      await start();
    }
  }

  const busy = phase !== 'idle';
  const err = error ?? recError;

  return (
    <section>
      <h3>Voice turn</h3>
      <button type="button" onClick={takeTurn} disabled={busy && !recording}>
        {recording ? 'Stop & send' : phase === 'idle' ? 'Record answer' : `${phase}…`}
      </button>
      {transcript && (
        <p>
          <strong>You:</strong> {transcript}
        </p>
      )}
      {reply && (
        <p>
          <strong>Interviewer:</strong> {reply}
        </p>
      )}
      {audioUrl && <audio key={audioUrl} src={audioUrl} controls autoPlay />}
      {err && <p>Error: {err}</p>}
    </section>
  );
}
