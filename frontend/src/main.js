import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Initialize Telegram WebApp
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.ready()
  window.Telegram.WebApp.expand()
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
