import apiClient from './client'

export const favoritesAPI = {
  async list() {
    const response = await apiClient.get('/api/favorites')
    return response.data
  },
  async add(mapId) {
    const response = await apiClient.post(`/api/favorites/${mapId}`)
    return response.data
  },
  async remove(mapId) {
    const response = await apiClient.delete(`/api/favorites/${mapId}`)
    return response.data
  },
}
