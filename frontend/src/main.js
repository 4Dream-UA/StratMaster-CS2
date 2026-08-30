import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router/index.js'
import App from './App.vue'
import { installGlobalErrorReporting } from './utils/errorReporting.js'

import './assets/style.css'

// TEMP QA HOOK — remove before shipping. Lets the Browser Pane test tool
// simulate a Telegram WebApp session via a localStorage-set initData string.
const __qaInitData = localStorage.getItem('__qa_init_data__')
if (__qaInitData) {
  window.Telegram = { WebApp: { initData: __qaInitData, ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, MainButton:{hide(){},show(){},setText(){},onClick(){}}, themeParams:{}, colorScheme:'dark' } }
}

const app = createApp(App)

installGlobalErrorReporting(app)

app.use(createPinia())
app.use(router)
app.mount('#app')

// Content protection (per spec): block the right-click/long-press context
// menu so strategy screenshots and lineups can't be trivially saved.
document.addEventListener('contextmenu', (e) => e.preventDefault())