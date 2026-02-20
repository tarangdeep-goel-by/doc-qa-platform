/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#f5f0ea',
          light: '#a8a29e',
        },
        cream: {
          DEFAULT: '#0c0a09',
          dark: '#1c1917',
        },
        burgundy: {
          DEFAULT: '#d97706',
          light: '#f59e0b',
          dark: '#b45309',
        },
        cyan: {
          DEFAULT: '#5eead4',
          light: '#99f6e4',
          dark: '#2dd4bf',
        },
        glass: {
          DEFAULT: 'rgba(245,240,234,0.03)',
          hover: 'rgba(245,240,234,0.06)',
          border: 'rgba(245,240,234,0.08)',
          strong: 'rgba(245,240,234,0.10)',
        },
      },
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter Variable', 'sans-serif'],
        body: ['Literata', 'Georgia', 'serif'],
      },
      fontSize: {
        'fluid-xs': 'clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem)',
        'fluid-sm': 'clamp(0.875rem, 0.825rem + 0.25vw, 1rem)',
        'fluid-base': 'clamp(1rem, 0.95rem + 0.25vw, 1.125rem)',
        'fluid-lg': 'clamp(1.125rem, 1.05rem + 0.375vw, 1.375rem)',
        'fluid-xl': 'clamp(1.25rem, 1.15rem + 0.5vw, 1.625rem)',
        'fluid-2xl': 'clamp(1.5rem, 1.35rem + 0.75vw, 2rem)',
        'fluid-3xl': 'clamp(1.875rem, 1.65rem + 1.125vw, 2.625rem)',
      },
      spacing: {
        'fluid-xs': 'clamp(0.5rem, 0.45rem + 0.25vw, 0.625rem)',
        'fluid-sm': 'clamp(0.75rem, 0.675rem + 0.375vw, 1rem)',
        'fluid-md': 'clamp(1rem, 0.9rem + 0.5vw, 1.375rem)',
        'fluid-lg': 'clamp(1.5rem, 1.35rem + 0.75vw, 2rem)',
        'fluid-xl': 'clamp(2rem, 1.8rem + 1vw, 2.75rem)',
        'fluid-2xl': 'clamp(3rem, 2.7rem + 1.5vw, 4.125rem)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.97)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'breathe': {
          '0%, 100%': { opacity: '0.25' },
          '50%': { opacity: '0.8' },
        },
        'check-draw': {
          from: { strokeDashoffset: '24' },
          to: { strokeDashoffset: '0' },
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
        'pop-in': {
          from: { opacity: '0', transform: 'scale(0.85)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-12px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'drift-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'feedback-pop': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(1.25)' },
          '100%': { transform: 'scale(1)' },
        },
        'amber-highlight': {
          '0%': { backgroundColor: 'rgba(217, 119, 6, 0.15)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
      animation: {
        'fade-in': 'fade-in 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scale-in 200ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 250ms cubic-bezier(0.16, 1, 0.3, 1)',
        'breathe': 'breathe 1.6s ease-in-out infinite',
        'check-draw': 'check-draw 350ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'glow-pulse': 'glow-pulse 1.5s ease-in-out 1',
        'pop-in': 'pop-in 200ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in-left': 'slide-in-left 250ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'drift-up': 'drift-up 500ms cubic-bezier(0.16, 1, 0.3, 1)',
        'feedback-pop': 'feedback-pop 250ms cubic-bezier(0.16, 1, 0.3, 1)',
        'amber-highlight': 'amber-highlight 1.5s ease-out forwards',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
  // Override prose defaults for dark theme
  safelist: ['prose-invert'],
}
