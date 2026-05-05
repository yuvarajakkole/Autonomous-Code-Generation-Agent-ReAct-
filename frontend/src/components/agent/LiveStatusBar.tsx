import { Activity, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  phase: string
  currentIteration: number
  finalScore: number | null
  isRunning: boolean
  isComplete: boolean
  success: boolean
  error: string | null
}

const PHASE_LABELS: Record<string, string> = {
  idle:         'Idle',
  starting:     'Starting…',
  running:      'Running ReAct Loop',
  planning:     '🧠 Planning',
  generation:   '⚡ Generating Code',
  execution:    '🐳 Executing Sandbox',
  evaluation:   '📊 Evaluating',
  refinement:   '🔄 Refining',
  completed:    'Completed',
  failed:       'Failed',
}

export default function LiveStatusBar({
  phase, currentIteration, finalScore, isRunning, isComplete, success, error
}: Props) {
  const phaseLabel = PHASE_LABELS[phase] || phase

  return (
    <div className={clsx(
      'rounded-xl border px-5 py-3.5 flex items-center justify-between gap-4 transition-all',
      isComplete && success ? 'border-accent-green/30 bg-agent-success' :
      isComplete && !success ? 'border-accent-yellow/30 bg-agent-observe' :
      error ? 'border-accent-red/30 bg-agent-error' :
      isRunning ? 'border-accent-blue/30 bg-agent-thought' :
      'border-agent-border bg-agent-surface'
    )}>
      <div className="flex items-center gap-3">
        {isRunning && <Loader2 size={14} className="text-accent-blue animate-spin flex-shrink-0" />}
        {isComplete && success && <CheckCircle2 size={14} className="text-accent-green flex-shrink-0" />}
        {isComplete && !success && <Activity size={14} className="text-accent-yellow flex-shrink-0" />}
        {error && <XCircle size={14} className="text-accent-red flex-shrink-0" />}
        {!isRunning && !isComplete && !error && (
          <Activity size={14} className="text-gray-500 flex-shrink-0" />
        )}

        <div>
          <span className="text-sm font-medium">{phaseLabel}</span>
          {error && <p className="text-xs text-accent-red mt-0.5">{error}</p>}
          {isComplete && (
            <p className="text-xs text-gray-400 mt-0.5">
              {success ? `Quality threshold met` : `Max iterations reached`}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-500 flex-shrink-0">
        {currentIteration > 0 && (
          <span className="font-mono">
            iter <span className="text-gray-300">{currentIteration}</span>
          </span>
        )}
        {finalScore !== null && (
          <span className={clsx(
            'font-mono font-bold',
            finalScore >= 0.8 ? 'text-accent-green' : finalScore >= 0.5 ? 'text-accent-yellow' : 'text-accent-red'
          )}>
            {(finalScore * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  )
}
