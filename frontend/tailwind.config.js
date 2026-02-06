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
          DEFAULT: '#E4E4E4',
          light: '#C0C0C0',
        },
        cream: {
          DEFAULT: '#2C2C2C',
          dark: '#363636',
        },
        burgundy: {
          DEFAULT: '#B39CD0',
          light: '#C4B3DD',
          dark: '#9A82B8',
        },
        cyan: {
          DEFAULT: '#A8DADC',
          light: '#BDE4E6',
          dark: '#8ECACD',
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
    },
  },
  plugins: [],
}
