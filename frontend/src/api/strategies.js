import apiClient from './client'

export const strategiesAPI = {
  async getMaps() {
    const response = await apiClient.get('/api/maps')
    return response.data
  },

  async getStrategiesCount() {
    const response = await apiClient.get('/api/strategies/count')
    return response.data.count
  },

  // filters: { map_id, side[], plant[], speed[], buy_tags[], is_free, search }
  async getStrategies(filters = {}) {
    // Axios serializes arrays as side[]=... by default.
    // We need side=T_side&side=CT_side (no brackets).
    // Use paramsSerializer to control this.
    const params = {}

    if (filters.map_id != null) params.map_id = filters.map_id
    if (filters.search)          params.search  = filters.search
    if (filters.is_free != null) params.is_free = filters.is_free

    if (filters.side?.length)     params.side     = filters.side
    if (filters.plant?.length)    params.plant    = filters.plant
    if (filters.speed?.length)    params.speed    = filters.speed
    if (filters.buy_tags?.length) params.buy_tags = filters.buy_tags

    const response = await apiClient.get('/api/strategies', {
      params,
      // Serialize arrays as repeated keys: side=T_side&side=CT_side
      paramsSerializer: p => {
        const parts = []
        for (const [key, val] of Object.entries(p)) {
          if (Array.isArray(val)) {
            val.forEach(v => parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(v)}`))
          } else {
            parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(val)}`)
          }
        }
        return parts.join('&')
      },
    })
    return response.data  // { total, strategies }
  },

  async getStrategy(id) {
    const response = await apiClient.get(`/api/strategies/${id}`)
    return response.data
  },
}