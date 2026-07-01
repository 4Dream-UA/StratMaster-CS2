import apiClient from './client'

export const strategiesAPI = {
  // Fetch active maps
  async getMaps() {
    const response = await apiClient.get('/api/maps')
    return response.data
  },

  // Fetch strategies feed (with optional filters)
  async getStrategies(mapId = null, side = null) {
    const params = {}
    if (mapId) params.map_id = mapId
    if (side) params.side = side

    const response = await apiClient.get('/api/strategies', { params })
    return response.data
  }
}