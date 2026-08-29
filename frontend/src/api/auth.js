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

  async updateAvatar(avatarUrl) {
    const response = await apiClient.patch('/api/me/avatar', { avatar_url: avatarUrl })
    return response.data
  },

  async updateNickname(nickname) {
    const response = await apiClient.patch('/api/me/nickname', { nickname })
    return response.data
  },
}
