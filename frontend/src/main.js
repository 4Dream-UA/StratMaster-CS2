import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router/index.js'
import App from './App.vue'
import { installGlobalErrorReporting } from './utils/errorReporting.js'

import './assets/style.css'

const app = createApp(App)

installGlobalErrorReporting(app)

app.use(createPinia())
app.use(router)
app.mount('#app')

// Content protection (per spec): block the right-click/long-press context
// menu so strategy screenshots and lineups can't be trivially saved.
document.addEventListener('contextmenu', (e) => e.preventDefault())