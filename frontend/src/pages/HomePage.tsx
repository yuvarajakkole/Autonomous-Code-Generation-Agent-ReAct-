import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import RequirementForm from '../components/agent/RequirementForm'
import ClarificationPanel from '../components/agent/ClarificationPanel'

type Stage = 'input' | 'clarify'

export default function HomePage() {
  const [stage, setStage] = useState<Stage>('input')
  const [sessionId, setSessionId] = useState('')
  const [questions, setQuestions] = useState<string[]>([])
  const navigate = useNavigate()

  function handleSession(sid: string, qs: string[]) {
    setSessionId(sid)
    setQuestions(qs)
    setStage('clarify')
  }

  function handleStart() {
    navigate(`/agent/${sessionId}`)
  }

  return (
    <div className="flex items-start justify-center min-h-[70vh] pt-8">
      {stage === 'input' ? (
        <RequirementForm onSession={handleSession} />
      ) : (
        <ClarificationPanel
          sessionId={sessionId}
          questions={questions}
          onStart={handleStart}
        />
      )}
    </div>
  )
}
