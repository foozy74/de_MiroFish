import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { clerkPlugin } from '@clerk/vue'

const app = createApp(App)

// MiroFish Clerk Design-Konfiguration (Dark Mode + Glassmorphism)
const miroFishTheme = {
  variables: {
    colorPrimary: '#7dd3c0', // MiroFish Teal
    colorBackground: '#0f172a', // Dunkler Hintergrund
    colorText: '#f8fafc',
    colorTextSecondary: '#94a3b8',
    colorInputBackground: 'rgba(255, 255, 255, 0.05)',
    colorInputText: '#f8fafc',
    borderRadius: '12px',
    fontFamily: "'Inter', sans-serif",
  },
  elements: {
    card: {
      backgroundColor: 'rgba(15, 23, 42, 0.8)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    },
    headerTitle: {
      fontSize: '24px',
      fontWeight: '700',
    },
    socialButtonsBlockButton: {
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      '&:hover': {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
      }
    }
  }
}

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
  appearance: miroFishTheme
})

app.use(router)

app.mount('#app')
