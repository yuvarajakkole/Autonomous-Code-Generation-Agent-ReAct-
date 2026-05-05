/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        display: ['"Space Grotesk"', 'sans-serif'],
        sans: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        agent: {
          bg:       '#090c10',
          surface:  '#0d1117',
          border:   '#21262d',
          thought:  '#1f2d3d',
          action:   '#1a2d1a',
          observe:  '#2d2618',
          eval:     '#2d1f2d',
          refine:   '#1f2d2d',
          success:  '#0d2818',
          error:    '#2d0d0d',
        },
        accent: {
          blue:   '#58a6ff',
          green:  '#3fb950',
          yellow: '#d29922',
          purple: '#bc8cff',
          cyan:   '#39c5cf',
          red:    '#f85149',
          orange: '#e3b341',
        },
      },
      animation: {
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':     'fadeIn 0.3s ease-in-out',
        'slide-up':    'slideUp 0.4s ease-out',
        'slide-in':    'slideIn 0.3s ease-out',
        'glow-green':  'glowGreen 2s ease-in-out infinite alternate',
        'typing':      'typing 1.2s steps(3) infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp:   { from: { transform: 'translateY(12px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        slideIn:   { from: { transform: 'translateX(-8px)', opacity: '0' }, to: { transform: 'translateX(0)', opacity: '1' } },
        glowGreen: { from: { boxShadow: '0 0 4px #3fb950' }, to: { boxShadow: '0 0 16px #3fb950, 0 0 32px #3fb95044' } },
        typing:    { '0%,100%': { content: '"."' }, '33%': { content: '".."' }, '66%': { content: '"..."' } },
      },
    },
  },
  plugins: [],
}
