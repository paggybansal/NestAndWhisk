/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './templates/**/*.html',
    './apps/**/*.html',
    './static_src/js/**/*.js',
    './static_src/css/**/*.css'
  ],
  theme: {
    extend: {
      colors: {
        vanilla: '#FFF8F0',
        cream: '#FFF8F0',
        beige: '#F3E4D3',
        'warm-beige': '#F3E4D3',
        cocoa: '#4A2E2A',
        caramel: '#C98A44',
        chocolate: '#2B1B18',
        espresso: '#2B1B18',
        rose: '#C97C88',
        'dusty-rose': '#C97C88',
        sage: '#A4B39B',
        'sage-ink': '#5F6E5A'
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'serif'],
        serif: ['Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      boxShadow: {
        card: '0 20px 45px -24px rgba(43, 27, 24, 0.25)',
        soft: '0 24px 60px -28px rgba(74, 46, 42, 0.28)'
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem'
      }
    }
  },
  plugins: [import('@tailwindcss/forms')]
};
