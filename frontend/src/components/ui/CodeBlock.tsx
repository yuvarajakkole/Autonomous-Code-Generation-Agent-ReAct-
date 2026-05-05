interface Props {
  code: string
  maxHeight?: string
}

// Minimal keyword highlighter (no external deps)
function highlight(code: string): string {
  const keywords = /\b(def|class|import|from|return|if|else|elif|for|while|try|except|finally|with|as|and|or|not|in|is|None|True|False|async|await|yield|lambda|pass|break|continue|raise|del|global|nonlocal|assert)\b/g
  const strings  = /("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"\n]*"|'[^'\n]*')/g
  const comments = /(#.*$)/gm
  const numbers  = /\b(\d+\.?\d*)\b/g
  const decorators = /(@\w+)/g
  const builtins = /\b(print|len|range|list|dict|set|tuple|str|int|float|bool|type|isinstance|hasattr|getattr|setattr|open|super|property|staticmethod|classmethod)\b/g

  return code
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // order matters
    .replace(strings,    '<span style="color:#a5d6ff">$1</span>')
    .replace(comments,   '<span style="color:#8b949e;font-style:italic">$1</span>')
    .replace(decorators, '<span style="color:#ffa657">$1</span>')
    .replace(keywords,   '<span style="color:#ff7b72">$1</span>')
    .replace(builtins,   '<span style="color:#d2a8ff">$1</span>')
    .replace(numbers,    '<span style="color:#79c0ff">$1</span>')
}

export default function CodeBlock({ code, maxHeight = '400px' }: Props) {
  return (
    <div
      className="overflow-auto bg-[#0d1117] text-[#e6edf3]"
      style={{ maxHeight }}
    >
      <pre className="p-4 text-xs leading-relaxed font-mono">
        <code dangerouslySetInnerHTML={{ __html: highlight(code) }} />
      </pre>
    </div>
  )
}
