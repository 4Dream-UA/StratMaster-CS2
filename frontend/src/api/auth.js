import apiClient from './client'

export const authAPI = {
  async authenticate(initData, refWalletId = null) {
    const response = await apiClient.post('/api/auth', {
      init_data: initData,
      ref_wallet_id: refWalletId,
    })
    return response.data
  },

  async getMe() {
    const response = await apiClient.get('/api/me')
    return response.data
  },
}
