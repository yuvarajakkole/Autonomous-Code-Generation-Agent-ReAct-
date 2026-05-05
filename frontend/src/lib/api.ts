const BASE = import.meta.env.VITE_API_URL || '/api/v1'

export interface ClarificationResponse {
  session_id: string
  questions: string[]
}

export interface AgentStatus {
  session_id: string
  phase: string
  iterations: number
  final_score: number | null
  success: boolean
  final_code: string
}

export interface Session {
  session_id: string
  raw_requirement: string
  phase: string
  total_iterations: number
  success: boolean
  created_at: string
  final_score?: { overall: number }
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Start a new agent session (get clarification questions)
  startAgent: (requirement: string) =>
    req<ClarificationResponse>('/agent/start', {
      method: 'POST',
      body: JSON.stringify({ requirement }),
    }),

  // Submit clarification answers
  submitAnswers: (sessionId: string, answers: Record<string, string>) =>
    req<{ status: string; session_id: string }>(`/agent/submit?session_id=${sessionId}`, {
      method: 'POST',
      body: JSON.stringify(answers),
    }),

  // Get status
  getStatus: (sessionId: string) =>
    req<AgentStatus>(`/agent/status/${sessionId}`),

  // List sessions
  listSessions: () =>
    req<{ sessions: Session[] }>('/sessions'),

  // Get session detail
  getSession: (sessionId: string) =>
    req<Record<string, unknown>>(`/sessions/${sessionId}`),

  // Delete session
  deleteSession: (sessionId: string) =>
    req<{ deleted: boolean }>(`/sessions/${sessionId}`, { method: 'DELETE' }),

  // SSE stream URL (not a fetch – used for EventSource)
  streamUrl: (sessionId: string) => `${BASE}/agent/stream/${sessionId}`,
}
