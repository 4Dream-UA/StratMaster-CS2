import apiClient from './client'

export const settingsAPI = {
  async get() {
    const response = await apiClient.get('/api/settings')
    return response.data
  },
  // Fields left undefined are not sent, and the backend leaves those alone —
  // so saving a logo can't silently flip the AI assistant back on, and vice
  // versa.
  async update(patch) {
    const response = await apiClient.patch('/api/admin/settings', patch)
    return response.data
  },
}
