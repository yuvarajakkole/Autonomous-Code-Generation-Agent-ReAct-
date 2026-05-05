import { useState } from 'react'
import { MessageSquare, ArrowRight, Loader2 } from 'lucide-react'
import { api } from '../../lib/api'

interface Props {
  sessionId: string
  questions: string[]
  onStart: () => void
}

export default function ClarificationPanel({ sessionId, questions, onStart }: Props) {
  const [answers, setAnswers] = useState<Record<number, string>>(
    Object.fromEntries(questions.map((_, i) => [i, '']))
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload: Record<string, string> = {}
      questions.forEach((q, i) => { payload[String(i)] = answers[i] || 'Not specified' })
      await api.submitAnswers(sessionId, payload)
      onStart()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit answers')
    } finally {
      setLoading(false)
    }
  }

  function skipAll() {
    const payload: Record<string, string> = {}
    questions.forEach((_, i) => { payload[String(i)] = 'Not specified' })
    setAnswers(Object.fromEntries(questions.map((_, i) => [i, 'Not specified'])))
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-lg bg-accent-yellow/10 border border-accent-yellow/20 flex items-center justify-center">
          <MessageSquare size={16} className="text-accent-yellow" />
        </div>
        <div>
          <h2 className="font-display font-semibold text-base">Clarification Questions</h2>
          <p className="text-xs text-gray-500">
            Answer to get better results, or skip to use defaults
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {questions.map((q, i) => (
          <div key={i} className="space-y-2">
            <label className="flex items-start gap-2">
              <span className="w-5 h-5 rounded bg-accent-blue/10 border border-accent-blue/20 text-accent-blue text-xs font-mono flex items-center justify-center flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span className="text-sm text-gray-200 leading-snug">{q}</span>
            </label>
            <textarea
              value={answers[i] || ''}
              onChange={e => setAnswers(a => ({ ...a, [i]: e.target.value }))}
              rows={2}
              placeholder="Your answer (optional — press skip to use defaults)"
              className="w-full ml-7 bg-agent-surface border border-agent-border rounded-lg px-3 py-2 text-xs text-gray-300 placeholder-gray-600 resize-none focus:outline-none focus:border-accent-blue/40 transition-all font-mono"
            />
          </div>
        ))}

        {error && (
          <div className="text-accent-red text-xs bg-agent-error border border-accent-red/20 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={async () => { skipAll(); setTimeout(() => handleSubmit({ preventDefault: () => {} } as React.FormEvent), 50) }}
            disabled={loading}
            className="flex-1 py-2.5 rounded-lg border border-agent-border text-gray-400 hover:text-gray-200 hover:border-gray-500 text-xs font-medium transition-all"
          >
            Skip All & Start
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 bg-accent-blue hover:bg-accent-blue/90 text-white font-medium py-2.5 rounded-lg transition-all text-xs"
          >
            {loading ? (
              <><Loader2 size={13} className="animate-spin" /> Submitting...</>
            ) : (
              <>Start ReAct Loop <ArrowRight size={13} /></>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
