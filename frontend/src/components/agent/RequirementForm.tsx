import { useState } from 'react'
import { Sparkles, ChevronRight, Loader2 } from 'lucide-react'
import { api } from '../../lib/api'

interface Props {
  onSession: (sessionId: string, questions: string[]) => void
}

const EXAMPLES = [
  'Build a login API with JWT authentication and refresh tokens',
  'Create a rate limiter middleware for FastAPI',
  'Implement a task queue with priority scheduling',
  'Build a file upload API with validation and virus scanning',
]

export default function RequirementForm({ onSession }: Props) {
  const [requirement, setRequirement] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!requirement.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await api.startAgent(requirement.trim())
      onSession(res.session_id, res.questions)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start agent')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent-blue/30 bg-accent-blue/5 text-accent-blue text-xs font-medium mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          ReAct Architecture · Thought → Action → Observe → Evaluate → Refine
        </div>
        <h1 className="font-display text-4xl font-bold tracking-tight mb-3">
          Autonomous Code Refinement
        </h1>
        <p className="text-gray-400 text-base leading-relaxed max-w-xl mx-auto">
          Describe what you want to build. The agent will clarify requirements,
          generate code, run tests, score quality, and iterate until production-ready.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            value={requirement}
            onChange={e => setRequirement(e.target.value)}
            placeholder="Describe your requirement in plain English…&#10;&#10;e.g. Build a login API with email/password authentication, JWT tokens, and rate limiting"
            rows={5}
            className="w-full bg-agent-surface border border-agent-border rounded-xl px-5 py-4 text-sm text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-accent-blue/50 focus:ring-1 focus:ring-accent-blue/20 transition-all font-mono leading-relaxed"
          />
          <div className="absolute bottom-3 right-3 text-xs text-gray-600 font-mono">
            {requirement.length} chars
          </div>
        </div>

        {error && (
          <div className="text-accent-red text-xs bg-agent-error border border-accent-red/20 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !requirement.trim()}
          className="w-full flex items-center justify-center gap-2 bg-accent-blue hover:bg-accent-blue/90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-3 rounded-xl transition-all text-sm"
        >
          {loading ? (
            <><Loader2 size={15} className="animate-spin" /> Analysing requirement...</>
          ) : (
            <><Sparkles size={15} /> Start Agent</>
          )}
        </button>
      </form>

      {/* Examples */}
      <div className="mt-8">
        <p className="text-xs text-gray-600 mb-3 uppercase tracking-wider font-medium">Try an example</p>
        <div className="grid grid-cols-1 gap-2">
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setRequirement(ex)}
              className="group flex items-center gap-3 text-left px-4 py-3 rounded-lg border border-agent-border hover:border-accent-blue/30 hover:bg-agent-surface/60 transition-all"
            >
              <ChevronRight size={12} className="text-gray-600 group-hover:text-accent-blue flex-shrink-0 transition-colors" />
              <span className="text-xs text-gray-400 group-hover:text-gray-200 transition-colors font-mono">
                {ex}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
