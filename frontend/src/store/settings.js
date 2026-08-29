import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsAPI } from '../api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const logoUrl = ref(null)
  const loaded = ref(false)

  async function load() {
    if (loaded.value) return
    try {
      const data = await settingsAPI.get()
      logoUrl.value = data.logo_url
    } catch (e) {
      // Falls back to the bundled static logo — not critical to block on.
    } finally {
      loaded.value = true
    }
  }

  return { logoUrl, load }
})
