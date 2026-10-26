/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        leaf: { 50: '#eef6ee', 100: '#d5ead6', 500: '#2e7d32', 600: '#256a29', 700: '#1b5e20', 900: '#123d16' },
      },
      fontFamily: { sans: ['Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', 'sans-serif'] },
    },
  },
  plugins: [],
};
