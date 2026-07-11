import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authAPI } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const wallet = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Called on app mount — handles both Telegram WebApp and browser dev mode
  async function initSession(refCode = null) {
    isLoading.value = true
    error.value = null

    try {
      const initData = window.Telegram?.WebApp?.initData

      // In browser (dev mode) skip auth, set mock user
      if (!initData) {
        console.warn('[Auth] No Telegram initData — running in dev/browser mode')
        user.value = { id: 'dev', username: 'dev_user', is_admin: true }
        wallet.value = { wallet_id: 'DEV000001', balance_coins: 0, subscription_expires_at: null }
        return
      }

      const data = await authAPI.authenticate(initData)
      user.value = data
      wallet.value = data.wallet
    } catch (err) {
      error.value = err.message
      console.error('[Auth] initSession failed:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function authenticate() {
    return initSession()
  }

  async function fetchMe() {
    isLoading.value = true
    error.value = null
    try {
      const data = await authAPI.getMe()
      user.value = data
      wallet.value = data.wallet
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function clearUser() {
    user.value = null
    wallet.value = null
    error.value = null
  }

  return { user, wallet, isLoading, error, initSession, authenticate, fetchMe, clearUser }
})