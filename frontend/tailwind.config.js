/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        leaf: { 50: '#eef6ee', 100: '#d5ead6', 500: '#2e7d32', 600: '#256a29', 700: '#1b5e20', 900: '#123d16' },
      },
      // REQ-N-06 본문 16px 이상: text-sm을 16px로, 보조 설명(text-xs)은 14px로 올린다
      fontSize: {
        xs: ['0.875rem', { lineHeight: '1.25rem' }],
        sm: ['1rem', { lineHeight: '1.5rem' }],
      },
      fontFamily: { sans: ['Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', 'sans-serif'] },
    },
  },
  plugins: [],
};
