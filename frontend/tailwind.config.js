/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#FFF5E6',
          100: '#FFE8C2',
          200: '#FFD699',
          300: '#FFC570',
          400: '#FFB347',
          500: '#FF9500', // Main orange
          600: '#E68600',
          700: '#CC7700',
          800: '#B36800',
          900: '#995900',
        },
        accent: {
          50: '#FFF0E0',
          100: '#FFD9B8',
          200: '#FFC28A',
          300: '#FFAB5C',
          400: '#FF9938',
          500: '#FF8714', // Bright orange accent
          600: '#F07B12',
          700: '#E06D0F',
          800: '#D15F0D',
          900: '#C24608',
        },
        dark: {
          50: '#5C4A3A',
          100: '#4A3B2E',
          200: '#3A2F24',
          300: '#2D231A',
          400: '#1F1710', // Card color
          500: '#120D08', // Main background
          600: '#0F0A06',
          700: '#0C0805',
          800: '#090603',
          900: '#060402',
        },
        text: {
          primary: '#F5E6D3',
          secondary: '#C9B29A',
          muted: '#8C7A68',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Poppins', 'system-ui', 'sans-serif'],
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        glow: {
          'from': { 
            boxShadow: '0 0 5px #FF9500, 0 0 10px #FF9500, 0 0 15px #FF9500',
          },
          'to': { 
            boxShadow: '0 0 10px #FF9500, 0 0 20px #FF9500, 0 0 30px #FF9500',
          },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      },
      backdropFilter: {
        'glass': 'blur(10px) saturate(180%)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'starfield': 'radial-gradient(2px 2px at 20px 30px, #eee, transparent), radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.1), transparent)',
      }
    },
  },
  plugins: [],
}