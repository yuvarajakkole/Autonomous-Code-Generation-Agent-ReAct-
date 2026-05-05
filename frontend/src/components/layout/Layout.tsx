import { Link, useLocation } from 'react-router-dom'
import { BrainCircuit, History, Zap } from 'lucide-react'
import clsx from 'clsx'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()

  const nav = [
    { to: '/',        label: 'Agent',   icon: Zap },
    { to: '/history', label: 'History', icon: History },
  ]

  return (
    <div className="min-h-screen bg-agent-bg flex flex-col">
      {/* Header */}
      <header className="border-b border-agent-border bg-agent-surface/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
              <BrainCircuit size={16} className="text-white" />
            </div>
            <span className="font-display font-semibold text-sm tracking-tight">
              ReAct<span className="text-accent-blue">Agent</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                  pathname === to
                    ? 'bg-accent-blue/10 text-accent-blue'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                )}
              >
                <Icon size={13} />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-8">
        {children}
      </main>
    </div>
  )
}
