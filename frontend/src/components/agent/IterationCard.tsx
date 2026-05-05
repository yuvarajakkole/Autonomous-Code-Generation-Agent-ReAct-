import { useState } from 'react'
import {
  Brain, Zap, Eye, BarChart2, RefreshCw,
  ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock
} from 'lucide-react'
import clsx from 'clsx'
import type { IterationData } from '../../hooks/useAgentStream'
import ScoreBar from '../ui/ScoreBar'
import CodeBlock from '../ui/CodeBlock'

interface Props {
  iteration: IterationData
}

const STEP_META: Record<string, { icon: React.ElementType; label: string; color: string; bg: string }> = {
  thought:     { icon: Brain,     label: 'Thought',     color: 'text-accent-blue',   bg: 'bg-agent-thought' },
  action:      { icon: Zap,       label: 'Action',      color: 'text-accent-green',  bg: 'bg-agent-action' },
  observation: { icon: Eye,       label: 'Observation', color: 'text-accent-yellow', bg: 'bg-agent-observe' },
  evaluation:  { icon: BarChart2, label: 'Evaluation',  color: 'text-accent-purple', bg: 'bg-agent-eval' },
  refinement:  { icon: RefreshCw, label: 'Refinement',  color: 'text-accent-cyan',   bg: 'bg-agent-refine' },
}

export default function IterationCard({ iteration }: Props) {
  const [expanded, setExpanded] = useState(iteration.isActive)
  const [showCode, setShowCode] = useState(false)

  const score = iteration.score
  const overall = score?.overall ?? 0
  const passed = iteration.tests ? iteration.steps.some(s => s.stepType === 'evaluation') : false

  return (
    <div
      className={clsx(
        'rounded-xl border transition-all duration-300',
        iteration.isActive
          ? 'border-accent-blue/40 bg-agent-surface active-pulse'
          : 'border-agent-border bg-agent-surface/50'
      )}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          {/* Iteration badge */}
          <div className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono font-bold',
            iteration.isActive
              ? 'bg-accent-blue/15 text-accent-blue border border-accent-blue/30'
              : overall >= 0.8
              ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
              : 'bg-gray-800 text-gray-400 border border-agent-border'
          )}>
            {iteration.number}
          </div>

          <div>
            <div className="text-sm font-medium font-display">
              Iteration {iteration.number}
              {iteration.isActive && (
                <span className="ml-2 text-xs text-accent-blue animate-pulse">● running</span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {iteration.steps.length} steps
              {score && ` · score ${(overall * 100).toFixed(0)}%`}
              {iteration.tests && ` · ${iteration.tests.passed}/${iteration.tests.total} tests`}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {score && (
            <div className="hidden sm:flex items-center gap-2">
              <ScoreBar value={overall} width={80} />
              <span className={clsx(
                'text-xs font-mono font-bold',
                overall >= 0.8 ? 'text-accent-green' : overall >= 0.5 ? 'text-accent-yellow' : 'text-accent-red'
              )}>
                {(overall * 100).toFixed(0)}%
              </span>
            </div>
          )}
          {iteration.execution && (
            iteration.execution.exit_code === 0
              ? <CheckCircle2 size={14} className="text-accent-green" />
              : <XCircle size={14} className="text-accent-red" />
          )}
          {iteration.isActive && <Clock size={13} className="text-accent-blue animate-spin-slow" />}
          {expanded
            ? <ChevronUp size={14} className="text-gray-500" />
            : <ChevronDown size={14} className="text-gray-500" />
          }
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 space-y-3 border-t border-agent-border/50 pt-4 animate-fade-in">
          {/* Steps */}
          {iteration.steps.map(step => {
            const meta = STEP_META[step.stepType] || STEP_META.thought
            const Icon = meta.icon
            return (
              <div key={step.id} className={clsx('rounded-lg p-4 event-enter', meta.bg)}>
                <div className={clsx('flex items-center gap-2 mb-2', meta.color)}>
                  <Icon size={13} />
                  <span className="text-xs font-semibold uppercase tracking-wider">{meta.label}</span>
                  <span className="text-gray-600 text-xs font-mono ml-auto">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {step.content}
                </pre>
              </div>
            )
          })}

          {/* Score breakdown */}
          {score && (
            <div className="rounded-lg border border-agent-border p-4 space-y-2">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Score Breakdown
              </div>
              {[
                ['Correctness',    score.correctness],
                ['Completeness',   score.completeness],
                ['Edge Cases',     score.edge_cases],
                ['Code Quality',   score.code_quality],
                ['Test Pass Rate', score.test_pass_rate],
              ].map(([label, val]) => (
                <div key={label as string} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-28">{label as string}</span>
                  <ScoreBar value={val as number} width={120} />
                  <span className="text-xs font-mono text-gray-300 w-8">
                    {((val as number) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
              {score.feedback && (
                <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-agent-border leading-relaxed">
                  {score.feedback}
                </p>
              )}
            </div>
          )}

          {/* Code toggle */}
          {iteration.code && (
            <div>
              <button
                onClick={() => setShowCode(c => !c)}
                className="text-xs text-accent-blue hover:underline flex items-center gap-1"
              >
                {showCode ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                {showCode ? 'Hide' : 'Show'} generated code
              </button>
              {showCode && (
                <div className="mt-2">
                  <CodeBlock code={iteration.code!} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
