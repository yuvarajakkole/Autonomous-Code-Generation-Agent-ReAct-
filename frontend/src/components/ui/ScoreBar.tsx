import clsx from 'clsx'

interface Props {
  value: number   // 0 to 1
  width?: number
}

export default function ScoreBar({ value, width = 100 }: Props) {
  const pct = Math.min(Math.max(value * 100, 0), 100)
  const color =
    pct >= 80 ? 'bg-accent-green' :
    pct >= 50 ? 'bg-accent-yellow' :
                'bg-accent-red'

  return (
    <div
      className="rounded-full bg-gray-800 h-1.5 overflow-hidden flex-shrink-0"
      style={{ width }}
    >
      <div
        className={clsx('h-full rounded-full transition-all duration-700 ease-out', color)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
