import apiClient from './client'

export const referralAPI = {
  async getStats() {
    const response = await apiClient.get('/api/referral/stats')
    return response.data
  },
  async applyCode(code) {
    const response = await apiClient.post('/api/referral/apply', { code })
    return response.data
  },
}