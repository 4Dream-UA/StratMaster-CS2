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

  async updateProfileInfo(profileInfo) {
    const response = await apiClient.patch('/api/me/profile-info', profileInfo)
    return response.data
  },

  async updateForumPrivacy(hideUsernameOnForum) {
    const response = await apiClient.patch('/api/me/forum-privacy', { hide_username_on_forum: hideUsernameOnForum })
    return response.data
  },

  async searchUsers(q) {
    const response = await apiClient.get('/api/users/search', { params: { q } })
    return response.data
  },

  async getPublicProfile(userId) {
    const response = await apiClient.get(`/api/users/${userId}/public-profile`)
    return response.data
  },
}
