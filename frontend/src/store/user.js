import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authAPI } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const wallet = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  async function authenticate() {
    isLoading.value = true
    error.value = null
    
    try {
      const initData = window.Telegram?.WebApp?.initData
      if (!initData) {
        throw new Error('Telegram WebApp not available')
      }

      const data = await authAPI.authenticate(initData)
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

  return {
    user,
    wallet,
    isLoading,
    error,
    authenticate,
    fetchMe,
    clearUser,
  }
})
