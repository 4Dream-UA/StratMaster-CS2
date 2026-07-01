import apiClient from './client'

export const authAPI = {
  async authenticate(initData) {
    const response = await apiClient.post('/api/auth', { init_data: initData })
    return response.data
  },

  async getMe() {
    const response = await apiClient.get('/api/me')
    return response.data
  },
}
