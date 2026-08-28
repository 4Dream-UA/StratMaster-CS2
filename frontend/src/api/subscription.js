import apiClient from './client'

export const subscriptionAPI = {
  async purchase(plan, months = null) {
    const response = await apiClient.post('/api/subscription/purchase', { plan, months })
    return response.data
  },

  async setAutoRenew(enabled, method = 'mastercoins') {
    const response = await apiClient.patch('/api/subscription/auto-renew', { enabled, method })
    return response.data
  },
}
