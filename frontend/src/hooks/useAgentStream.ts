import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

export type StepType = 'thought' | 'action' | 'observation' | 'evaluation' | 'refinement' | 'system'

export interface AgentStep {
  id: string
  stepType: StepType
  content: string
  metadata?: Record<string, unknown>
  timestamp: string
}

export interface IterationData {
  number: number
  steps: AgentStep[]
  score?: {
    overall: number
    correctness: number
    completeness: number
    edge_cases: number
    code_quality: number
    test_pass_rate: number
    feedback: string
  }
  code?: string
  tests?: {
    passed: number
    failed: number
    total: number
  }
  execution?: {
    exit_code: number
    stdout: string
    stderr: string
    duration_ms: number
    timed_out: boolean
  }
  refinementNotes?: string
  isActive: boolean
}

export interface AgentState {
  phase: string
  iterations: IterationData[]
  currentIteration: number
  finalCode: string
  finalScore: number | null
  success: boolean
  isRunning: boolean
  isComplete: boolean
  error: string | null
  clarificationQuestions: string[]
  sessionId: string | null
}

const initialState = (): AgentState => ({
  phase: 'idle',
  iterations: [],
  currentIteration: 0,
  finalCode: '',
  finalScore: null,
  success: false,
  isRunning: false,
  isComplete: false,
  error: null,
  clarificationQuestions: [],
  sessionId: null,
})

let _stepCounter = 0
const nextId = () => `step-${++_stepCounter}`

export function useAgentStream() {
  const [state, setState] = useState<AgentState>(initialState())
  const esRef = useRef<EventSource | null>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
  }, [])

  const connect = useCallback((sessionId: string) => {
    disconnect()
    setState(s => ({ ...s, isRunning: true, sessionId, phase: 'starting' }))

    const es = new EventSource(api.streamUrl(sessionId))
    esRef.current = es

    es.onmessage = (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data)
        if (payload.event === 'stream_end') { disconnect(); return }
        handleEvent(payload.event, payload.data, payload.timestamp)
      } catch { /* ignore parse errors */ }
    }

    es.onerror = () => {
      setState(s => ({
        ...s,
        isRunning: false,
        error: s.isComplete ? null : 'Connection lost. The agent may still be running.',
      }))
      disconnect()
    }
  }, [disconnect])

  function handleEvent(event: string, data: Record<string, unknown>, timestamp: string) {
    setState(prev => {
      const next = { ...prev }

      const addStep = (iterNum: number, step: AgentStep) => {
        const iters = [...next.iterations]
        const idx = iters.findIndex(i => i.number === iterNum)
        if (idx >= 0) {
          iters[idx] = { ...iters[idx], steps: [...iters[idx].steps, step] }
        }
        next.iterations = iters
      }

      switch (event) {
        case 'agent_started':
          next.phase = 'running'
          break

        case 'iteration_start': {
          const num = data.iteration as number
          next.currentIteration = num
          // Mark previous as inactive
          const iters = next.iterations.map(i => ({ ...i, isActive: false }))
          iters.push({ number: num, steps: [], isActive: true })
          next.iterations = iters
          break
        }

        case 'thought': {
          const num = data.iteration as number
          addStep(num, {
            id: nextId(), stepType: 'thought',
            content: data.content as string,
            metadata: data.raw as Record<string, unknown>,
            timestamp,
          })
          break
        }

        case 'action': {
          const num = data.iteration as number
          addStep(num, {
            id: nextId(), stepType: 'action',
            content: `${data.action}\n\n${data.code_preview}`,
            metadata: { changes_made: data.changes_made, full_code: data.full_code },
            timestamp,
          })
          const iters = next.iterations.map(i =>
            i.number === num ? { ...i, code: data.full_code as string } : i
          )
          next.iterations = iters
          break
        }

        case 'observation': {
          const num = data.iteration as number
          addStep(num, {
            id: nextId(), stepType: 'observation',
            content: data.content as string,
            metadata: { execution: data.execution, tests: data.tests },
            timestamp,
          })
          const iters = next.iterations.map(i =>
            i.number === num
              ? {
                  ...i,
                  execution: data.execution as IterationData['execution'],
                  tests: data.tests as IterationData['tests'],
                }
              : i
          )
          next.iterations = iters
          break
        }

        case 'evaluation': {
          const num = data.iteration as number
          const score = data.score as IterationData['score']
          addStep(num, {
            id: nextId(), stepType: 'evaluation',
            content: `Overall: ${((score?.overall ?? 0) * 100).toFixed(0)}% | Feedback: ${score?.feedback}`,
            metadata: { score },
            timestamp,
          })
          const iters = next.iterations.map(i =>
            i.number === num ? { ...i, score } : i
          )
          next.iterations = iters
          break
        }

        case 'refinement': {
          const num = data.iteration as number
          addStep(num, {
            id: nextId(), stepType: 'refinement',
            content: data.notes as string,
            metadata: data.plan as Record<string, unknown>,
            timestamp,
          })
          const iters = next.iterations.map(i =>
            i.number === num ? { ...i, refinementNotes: data.notes as string } : i
          )
          next.iterations = iters
          break
        }

        case 'phase_change':
          next.phase = (data.phase as string) || next.phase
          break

        case 'completed':
          next.finalCode = data.final_code as string
          next.finalScore = data.final_score as number
          next.success = data.success as boolean
          next.isComplete = true
          next.isRunning = false
          next.phase = 'completed'
          next.iterations = next.iterations.map(i => ({ ...i, isActive: false }))
          break

        case 'error':
          next.error = data.message as string
          next.isRunning = false
          next.phase = 'failed'
          break

        default:
          break
      }

      return next
    })
  }

  useEffect(() => () => disconnect(), [disconnect])

  const reset = useCallback(() => {
    disconnect()
    setState(initialState())
  }, [disconnect])

  return { state, connect, reset }
}
