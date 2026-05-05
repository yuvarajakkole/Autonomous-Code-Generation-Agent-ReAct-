import { useState } from 'react'
import {
  CheckCircle2, Copy, Check, Trophy, AlertTriangle,
  Download, ExternalLink, FileCode2, Globe, ChevronDown, ChevronUp
} from 'lucide-react'
import clsx from 'clsx'
import CodeBlock from '../ui/CodeBlock'
import ScoreBar from '../ui/ScoreBar'

interface ScoreData {
  overall: number
  correctness: number
  completeness: number
  edge_cases: number
  code_quality: number
  test_pass_rate: number
  feedback: string
}

interface Props {
  code: string
  score: ScoreData | null
  totalIterations: number
  success: boolean
  sessionId: string
}

// Parse project JSON to extract files
function parseProject(code: string): { files: Record<string, string>; entryPoint: string } | null {
  try {
    const cleaned = code.replace(/^```json\n?/, '').replace(/^```\n?/, '').replace(/\n?```$/, '').trim()
    const data = JSON.parse(cleaned)
    if (data.files) return { files: data.files, entryPoint: data.entry_point || 'index.html' }
  } catch {}
  // Single HTML
  if (code.includes('<html') || code.includes('<!DOCTYPE')) {
    return { files: { 'index.html': code }, entryPoint: 'index.html' }
  }
  return null
}

const FILE_ICONS: Record<string, string> = {
  '.html': '🌐',
  '.css':  '🎨',
  '.js':   '⚡',
  '.py':   '🐍',
  '.json': '📋',
  '.md':   '📝',
}

function fileIcon(name: string) {
  const ext = '.' + name.split('.').pop()
  return FILE_ICONS[ext] || '📄'
}

export default function FinalOutputPanel({ code, score, totalIterations, success, sessionId }: Props) {
  const [copied, setCopied] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [showScores, setShowScores] = useState(false)

  const project = parseProject(code)
  const files = project?.files ?? {}
  const entryPoint = project?.entryPoint ?? 'index.html'
  const fileNames = Object.keys(files)

  // Default: show entry point
  const activeFile = selectedFile ?? entryPoint
  const activeContent = files[activeFile] ?? code

  const apiBase = import.meta.env.VITE_API_URL || '/api/v1'
  const previewUrl = `${apiBase}/agent/preview/${sessionId}`
  const downloadUrl = `${apiBase}/agent/output/${sessionId}`

  async function copy() {
    await navigator.clipboard.writeText(activeContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const overall = score?.overall ?? 0

  return (
    <div className="space-y-4 animate-slide-up">

      {/* Status banner */}
      <div className={clsx(
        'rounded-xl border p-4 flex items-center justify-between gap-4',
        success ? 'border-accent-green/30 bg-agent-success' : 'border-accent-yellow/30 bg-agent-observe'
      )}>
        <div className="flex items-center gap-3">
          <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0',
            success ? 'bg-accent-green/10' : 'bg-accent-yellow/10'
          )}>
            {success ? <Trophy size={18} className="text-accent-green" /> : <AlertTriangle size={18} className="text-accent-yellow" />}
          </div>
          <div>
            <h3 className="font-display font-semibold text-sm">
              {success ? 'Quality Threshold Met 🎉' : 'Best Result'}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              {totalIterations} iteration{totalIterations !== 1 ? 's' : ''} ·{' '}
              <span className={clsx('font-mono font-bold',
                overall >= 0.8 ? 'text-accent-green' : 'text-accent-yellow'
              )}>{(overall * 100).toFixed(0)}%</span>
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <a
            href={previewUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent-blue/10 border border-accent-blue/20 text-accent-blue text-xs font-medium hover:bg-accent-blue/20 transition-all"
          >
            <Globe size={12} /> Preview
          </a>
          <a
            href={downloadUrl}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent-green/10 border border-accent-green/20 text-accent-green text-xs font-medium hover:bg-accent-green/20 transition-all"
          >
            <Download size={12} /> Download ZIP
          </a>
        </div>
      </div>

      {/* Score toggle */}
      {score && (
        <div className="rounded-xl border border-agent-border bg-agent-surface overflow-hidden">
          <button
            onClick={() => setShowScores(s => !s)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition-all"
          >
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Quality Scores
            </span>
            {showScores ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
          </button>
          {showScores && (
            <div className="px-4 pb-4 grid grid-cols-2 gap-3 border-t border-agent-border pt-3">
              {([
                ['Correctness',    score.correctness],
                ['Completeness',   score.completeness],
                ['Edge Cases',     score.edge_cases],
                ['Code Quality',   score.code_quality],
                ['Test Pass Rate', score.test_pass_rate],
                ['Overall',        score.overall],
              ] as [string, number][]).map(([label, val]) => (
                <div key={label}>
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className="flex items-center gap-2">
                    <ScoreBar value={val} width={60} />
                    <span className={clsx('text-xs font-mono font-bold',
                      val >= 0.8 ? 'text-accent-green' :
                      val >= 0.5 ? 'text-accent-yellow' : 'text-accent-red'
                    )}>{(val * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
              {score.feedback && (
                <p className="col-span-2 text-xs text-gray-400 mt-1 pt-3 border-t border-agent-border leading-relaxed">
                  {score.feedback}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* File tree + code viewer */}
      <div className="rounded-xl border border-agent-border overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-agent-surface border-b border-agent-border">
          <div className="flex items-center gap-2">
            <FileCode2 size={13} className="text-accent-green" />
            <span className="text-xs font-medium text-gray-300">Generated Files</span>
          </div>
          <button
            onClick={copy}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors px-2 py-1 rounded hover:bg-white/5"
          >
            {copied ? <><Check size={11} className="text-accent-green" /> Copied!</> : <><Copy size={11} /> Copy</>}
          </button>
        </div>

        {/* File tabs */}
        {fileNames.length > 1 && (
          <div className="flex items-center gap-0 border-b border-agent-border bg-agent-bg overflow-x-auto">
            {fileNames.map(fname => (
              <button
                key={fname}
                onClick={() => setSelectedFile(fname)}
                className={clsx(
                  'flex items-center gap-1.5 px-4 py-2 text-xs font-mono border-r border-agent-border whitespace-nowrap transition-all flex-shrink-0',
                  activeFile === fname
                    ? 'bg-agent-surface text-gray-200 border-b-2 border-b-accent-blue'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-agent-surface/50'
                )}
              >
                <span>{fileIcon(fname)}</span>
                {fname}
              </button>
            ))}
          </div>
        )}

        {/* Code content */}
        <CodeBlock code={activeContent} maxHeight="480px" />
      </div>

      {/* How-to-run tip */}
      <div className="rounded-lg border border-agent-border/50 px-4 py-3 bg-agent-surface/30">
        <p className="text-xs text-gray-500">
          <span className="text-accent-blue font-medium">How to run: </span>
          Click <span className="text-accent-blue font-mono">Preview</span> to open in browser, or{' '}
          <span className="text-accent-green font-mono">Download ZIP</span> to get all files.{' '}
          {fileNames.some(f => f.endsWith('.html')) && (
            <>Just open <span className="font-mono text-gray-300">index.html</span> in any browser — no server needed.</>
          )}
        </p>
      </div>
    </div>
  )
}
