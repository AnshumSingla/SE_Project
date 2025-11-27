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
          50: '#E0FFFF',
          100: '#B8FFFF',
          200: '#8AFFFF',
          300: '#5CFFFF',
          400: '#2EFFFF',
          500: '#00FFFF', // Cyan
          600: '#00E6E6',
          700: '#00CCCC',
          800: '#00B3B3',
          900: '#009999',
        },
        accent: {
          50: '#E0F7F8',
          100: '#B8EEEF',
          200: '#8AE4E6',
          300: '#5CDADD',
          400: '#2EC4C7',
          500: '#00ADB5', // Teal
          600: '#009BA3',
          700: '#008991',
          800: '#00777F',
          900: '#00656D',
        },
        dark: {
          50: '#595959',
          100: '#4D4D4D',
          200: '#404040',
          300: '#262626',
          400: '#1A1A1A', // Card background
          500: '#0D0D0D', // Dark background
          600: '#0A0A0A',
          700: '#080808',
          800: '#050505',
          900: '#030303',
        },
        text: {
          primary: '#E0E0E0',
          secondary: '#B3B3B3',
          muted: '#808080',
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
            boxShadow: '0 0 5px #00FFFF, 0 0 10px #00FFFF, 0 0 15px #00FFFF',
          },
          'to': { 
            boxShadow: '0 0 10px #00FFFF, 0 0 20px #00FFFF, 0 0 30px #00FFFF',
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