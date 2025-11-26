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
          200: '#7DFFFF',
          300: '#42FFFF',
          400: '#14FFFF',
          500: '#00FFFF', // Main cyan
          600: '#00E5E5',
          700: '#00CCCC',
          800: '#00B3B3',
          900: '#009999',
        },
        accent: {
          50: '#E0F9F9',
          100: '#B3F0F0',
          200: '#80E6E6',
          300: '#4DDDDD',
          400: '#26D4D4',
          500: '#00ADB5', // Main accent
          600: '#009CA4',
          700: '#008B93',
          800: '#007A82',
          900: '#006971',
        },
        dark: {
          50: '#404040',
          100: '#333333',
          200: '#262626',
          300: '#1F1F1F',
          400: '#1A1A1A', // Card color
          500: '#0D0D0D', // Main background
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