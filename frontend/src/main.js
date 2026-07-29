import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router/index.js'
import App from './App.vue'

import './assets/style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')

// Content protection (per spec): block the right-click/long-press context
// menu so strategy screenshots and lineups can't be trivially saved.
document.addEventListener('contextmenu', (e) => e.preventDefault())