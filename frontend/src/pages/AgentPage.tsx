import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, RotateCcw } from 'lucide-react'
import { useAgentStream } from '../hooks/useAgentStream'
import LiveStatusBar from '../components/agent/LiveStatusBar'
import IterationCard from '../components/agent/IterationCard'
import FinalOutputPanel from '../components/agent/FinalOutputPanel'

export default function AgentPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { state, connect, reset } = useAgentStream()

  useEffect(() => {
    if (sessionId && state.phase === 'idle') {
      connect(sessionId)
    }
  }, [sessionId]) // eslint-disable-line

  const lastIter = state.iterations[state.iterations.length - 1]
  const displayScore = state.finalScore ?? lastIter?.score?.overall ?? null
  const finalScoreObj = state.isComplete ? (lastIter?.score ?? null) : null

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors">
          <ArrowLeft size={12} /> New Session
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-600 font-mono">{sessionId?.slice(0, 8)}…</span>
          {(state.isComplete || state.error) && (
            <button onClick={reset} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors">
              <RotateCcw size={11} /> Reset
            </button>
          )}
        </div>
      </div>

      <LiveStatusBar
        phase={state.phase}
        currentIteration={state.currentIteration}
        finalScore={displayScore}
        isRunning={state.isRunning}
        isComplete={state.isComplete}
        success={state.success}
        error={state.error}
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: iteration timeline */}
        <div className="lg:col-span-3 space-y-3">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-1">
            ReAct Loop · {state.iterations.length} iteration{state.iterations.length !== 1 ? 's' : ''}
          </h2>

          {state.iterations.length === 0 && state.isRunning && (
            <div className="rounded-xl border border-agent-border bg-agent-surface/50 px-5 py-10 text-center">
              <div className="text-2xl mb-3">🧠</div>
              <p className="text-sm text-gray-500">Agent is starting…</p>
              <p className="text-xs text-gray-600 mt-1">Thought → Action → Observe → Evaluate → Refine</p>
            </div>
          )}

          {[...state.iterations].reverse().map(iter => (
            <IterationCard key={iter.number} iteration={iter} />
          ))}
        </div>

        {/* Right: final output / progress */}
        <div className="lg:col-span-2 space-y-4">
          {state.isComplete ? (
            <FinalOutputPanel
              code={state.finalCode}
              score={finalScoreObj}
              totalIterations={state.currentIteration}
              success={state.success}
              sessionId={sessionId!}
            />
          ) : (
            <div className="rounded-xl border border-agent-border bg-agent-surface/50 p-5 space-y-4 sticky top-20">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Live Progress</h3>
              <div className="space-y-2">
                {[
                  { label: 'Thought',     icon: '🧠', phase: 'planning'   },
                  { label: 'Action',      icon: '⚡', phase: 'generation' },
                  { label: 'Observation', icon: '👁', phase: 'execution'  },
                  { label: 'Evaluation',  icon: '📊', phase: 'evaluation' },
                  { label: 'Refinement',  icon: '🔄', phase: 'refinement' },
                ].map(({ label, icon, phase }) => (
                  <div key={phase} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-xs transition-all ${
                    state.phase === phase
                      ? 'border-accent-blue/40 bg-accent-blue/5 text-gray-200'
                      : 'border-agent-border text-gray-600'
                  }`}>
                    <span className="text-base leading-none">{icon}</span>
                    <span className="font-medium">{label}</span>
                    {state.phase === phase && (
                      <span className="ml-auto text-accent-blue animate-pulse text-xs">active</span>
                    )}
                  </div>
                ))}
              </div>
              {displayScore !== null && (
                <div className="pt-3 border-t border-agent-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-500">Current Score</span>
                    <span className={`text-xs font-mono font-bold ${
                      displayScore >= 0.8 ? 'text-accent-green' :
                      displayScore >= 0.5 ? 'text-accent-yellow' : 'text-accent-red'
                    }`}>{(displayScore * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-gray-800 overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-700 ${
                      displayScore >= 0.8 ? 'bg-accent-green' :
                      displayScore >= 0.5 ? 'bg-accent-yellow' : 'bg-accent-red'
                    }`} style={{ width: `${Math.min(displayScore * 100, 100)}%` }} />
                  </div>
                  <div className="flex justify-between text-xs text-gray-700 mt-1">
                    <span>0%</span>
                    <span className="text-accent-blue">80% threshold</span>
                    <span>100%</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
