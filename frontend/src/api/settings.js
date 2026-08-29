import apiClient from './client'

export const settingsAPI = {
  async get() {
    const response = await apiClient.get('/api/settings')
    return response.data
  },
  async update(logoUrl) {
    const response = await apiClient.patch('/api/admin/settings', { logo_url: logoUrl })
    return response.data
  },
}
