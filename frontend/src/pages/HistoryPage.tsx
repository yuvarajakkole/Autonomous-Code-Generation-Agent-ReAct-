import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Clock, CheckCircle2, XCircle, Trash2, ChevronRight, Loader2 } from 'lucide-react'
import { api, type Session } from '../lib/api'
import clsx from 'clsx'

export default function HistoryPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)

  useEffect(() => {
    api.listSessions()
      .then(r => setSessions(r.sessions))
      .finally(() => setLoading(false))
  }, [])

  async function deleteSession(id: string) {
    setDeleting(id)
    try {
      await api.deleteSession(id)
      setSessions(s => s.filter(x => x.session_id !== id))
    } finally {
      setDeleting(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={20} className="animate-spin text-gray-500" />
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-24">
        <div className="text-4xl mb-4">📭</div>
        <h2 className="font-display font-semibold text-lg mb-2">No sessions yet</h2>
        <p className="text-sm text-gray-500 mb-6">Start your first agent session to see history here.</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 bg-accent-blue hover:bg-accent-blue/90 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-all"
        >
          Start Agent
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-xl">Session History</h1>
        <span className="text-xs text-gray-500">{sessions.length} sessions</span>
      </div>

      {sessions.map(s => {
        const overall = s.final_score?.overall
        const date = new Date(s.created_at)
        return (
          <div
            key={s.session_id}
            className="rounded-xl border border-agent-border bg-agent-surface hover:border-gray-600 transition-all group"
          >
            <div className="px-5 py-4 flex items-center gap-4">
              {/* Status icon */}
              <div className="flex-shrink-0">
                {s.success
                  ? <CheckCircle2 size={16} className="text-accent-green" />
                  : s.phase === 'failed'
                  ? <XCircle size={16} className="text-accent-red" />
                  : <Clock size={16} className="text-accent-yellow" />
                }
              </div>

              {/* Requirement */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate font-mono">
                  {s.raw_requirement}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-gray-600">
                    {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="text-xs text-gray-600">·</span>
                  <span className="text-xs text-gray-600">{s.total_iterations} iterations</span>
                  {overall != null && (
                    <>
                      <span className="text-xs text-gray-600">·</span>
                      <span className={clsx(
                        'text-xs font-mono font-bold',
                        overall >= 0.8 ? 'text-accent-green' :
                        overall >= 0.5 ? 'text-accent-yellow' : 'text-accent-red'
                      )}>
                        {(overall * 100).toFixed(0)}%
                      </span>
                    </>
                  )}
                  <span className={clsx(
                    'text-xs px-2 py-0.5 rounded-full border',
                    s.phase === 'completed'
                      ? 'border-accent-green/20 text-accent-green bg-accent-green/5'
                      : s.phase === 'failed'
                      ? 'border-accent-red/20 text-accent-red bg-accent-red/5'
                      : 'border-accent-yellow/20 text-accent-yellow bg-accent-yellow/5'
                  )}>
                    {s.phase}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => deleteSession(s.session_id)}
                  disabled={deleting === s.session_id}
                  className="p-1.5 rounded-md text-gray-600 hover:text-accent-red hover:bg-accent-red/5 transition-all opacity-0 group-hover:opacity-100"
                >
                  {deleting === s.session_id
                    ? <Loader2 size={13} className="animate-spin" />
                    : <Trash2 size={13} />
                  }
                </button>
                <Link
                  to={`/agent/${s.session_id}`}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-200 transition-colors px-2 py-1.5 rounded-md hover:bg-white/5"
                >
                  View <ChevronRight size={12} />
                </Link>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
