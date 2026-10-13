export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface InterviewSession {
  id: string;
  user_id: string;
  role_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SessionMessage {
  id: string;
  interview_id: string;
  sender: 'candidate' | 'interviewer';
  transcript: string;
  audio_path: string | null;
  created_at: string;
}

export interface HealthStatus {
  status: 'ok' | 'degraded';
  system: string;
  services: Record<string, string>;
}
