import apiClient from './client'

export const casesAPI = {
  async list() {
    const response = await apiClient.get('/api/cases')
    return response.data
  },
  async inventory() {
    const response = await apiClient.get('/api/cases/inventory')
    return response.data
  },
  async buy(caseId, quantity = 1) {
    const response = await apiClient.post(`/api/cases/${caseId}/buy`, { quantity })
    return response.data
  },
  async openInventory(caseId, quantity) {
    const response = await apiClient.post('/api/cases/inventory/open', { case_id: caseId, quantity })
    return response.data
  },
  async history() {
    const response = await apiClient.get('/api/cases/openings/history')
    return response.data.openings
  },
  async gift(receiverWalletId, caseId, quantity) {
    const response = await apiClient.post('/api/cases/gift', {
      receiver_wallet_id: receiverWalletId, case_id: caseId, quantity,
    })
    return response.data
  },
  async sell(receiverWalletId, caseId, quantity, priceCoins) {
    const response = await apiClient.post('/api/cases/sell', {
      receiver_wallet_id: receiverWalletId, case_id: caseId, quantity, price_coins: priceCoins,
    })
    return response.data
  },
  async listOffers(direction) {
    const response = await apiClient.get('/api/cases/offers', { params: { direction } })
    return response.data
  },
  async acceptOffer(id) {
    const response = await apiClient.post(`/api/cases/offers/${id}/accept`)
    return response.data
  },
  async declineOffer(id) {
    const response = await apiClient.post(`/api/cases/offers/${id}/decline`)
    return response.data
  },
  async cancelOffer(id) {
    const response = await apiClient.post(`/api/cases/offers/${id}/cancel`)
    return response.data
  },

  // ── Premium vouchers ────────────────────────────────
  async vouchers() {
    const response = await apiClient.get('/api/cases/vouchers')
    return response.data
  },
  async activateVoucher(id) {
    const response = await apiClient.post(`/api/cases/vouchers/${id}/activate`)
    return response.data
  },
  async giftVoucher(id, receiverWalletId) {
    await apiClient.post(`/api/cases/vouchers/${id}/gift`, { receiver_wallet_id: receiverWalletId })
  },
  async sellVoucher(id, receiverWalletId, priceCoins) {
    const response = await apiClient.post(`/api/cases/vouchers/${id}/sell`, {
      receiver_wallet_id: receiverWalletId, price_coins: priceCoins,
    })
    return response.data
  },
  async listVoucherOffers(direction) {
    const response = await apiClient.get('/api/cases/voucher-offers', { params: { direction } })
    return response.data
  },
  async acceptVoucherOffer(id) {
    const response = await apiClient.post(`/api/cases/voucher-offers/${id}/accept`)
    return response.data
  },
  async declineVoucherOffer(id) {
    const response = await apiClient.post(`/api/cases/voucher-offers/${id}/decline`)
    return response.data
  },
  async cancelVoucherOffer(id) {
    const response = await apiClient.post(`/api/cases/voucher-offers/${id}/cancel`)
    return response.data
  },
}
