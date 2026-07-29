import apiClient from './client'

export const promoAPI = {
  async redeem(code) {
    const response = await apiClient.post('/api/promo/redeem', { code })
    return response.data
  },
}
