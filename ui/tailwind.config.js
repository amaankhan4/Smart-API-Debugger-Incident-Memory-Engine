/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#080A0F',
        surface: {
          DEFAULT: '#0E1117',
          raised: '#131822',
          hover: '#181E2A'
        },
        line: {
          DEFAULT: '#1E2534',
          strong: '#2A3345'
        },
        content: {
          DEFAULT: '#E7EBF3',
          muted: '#8B95A9',
          subtle: '#5C6679'
        },
        accent: {
          DEFAULT: '#6E7BFF',
          soft: '#8E98FF',
          dim: 'rgba(110, 123, 255, 0.12)'
        },
        severity: {
          critical: '#FF5C7A',
          high: '#FF9556',
          medium: '#F5C451',
          low: '#5AC8FA'
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace']
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }]
      },
      boxShadow: {
        panel: '0 1px 2px rgba(0,0,0,0.4), 0 8px 24px -12px rgba(0,0,0,0.6)',
        overlay: '0 24px 64px -16px rgba(0,0,0,0.8)'
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' }
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' }
        }
      },
      animation: {
        'fade-in': 'fade-in 150ms ease-out',
        'slide-up': 'slide-up 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        shimmer: 'shimmer 1.6s infinite'
      }
    }
  },
  plugins: []
};
