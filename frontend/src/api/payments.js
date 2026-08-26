import apiClient from './client'

export const paymentsAPI = {
  async createCryptoInvoice({ plan = null, months = null, coins = null } = {}) {
    const response = await apiClient.post('/api/payments/crypto/invoice', { plan, months, coins })
    return response.data
  },

  async getCryptoInvoiceStatus(invoiceId) {
    const response = await apiClient.get(`/api/payments/crypto/invoice/${invoiceId}`)
    return response.data
  },
}
