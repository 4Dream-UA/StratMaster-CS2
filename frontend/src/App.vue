<template>
  <div id="app">
    <div v-if="isLoading" class="loading">
      Loading...
    </div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <div v-else-if="user" class="content">
      <h1>Welcome, {{ user.username || 'User' }}!</h1>
      <div class="wallet-info">
        <p>Wallet ID: {{ wallet.wallet_id }}</p>
        <p>Balance: {{ wallet.balance_coins }} MasterCoins</p>
      </div>
    </div>
    <div v-else class="auth-prompt">
      <p>Please authenticate...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from './store/user'

const userStore = useUserStore()

const { user, wallet, isLoading, error } = storeToRefs(userStore)
const { authenticate } = userStore

onMounted(async () => {
  try {
    await authenticate()
  } catch (err) {
    console.error('Authentication failed:', err)
  }
})
</script>

<style scoped>
#app {
  min-height: 100vh;
  background-color: #1E1F22;
  color: #D4D4D4;
  font-family: Arial, sans-serif;
}

.loading,
.error,
.auth-prompt {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  font-size: 1.2rem;
}

.error {
  color: #ff6b6b;
}

.content {
  padding: 20px;
}

.wallet-info {
  margin-top: 20px;
  padding: 15px;
  background-color: #2A2D33;
  border-radius: 8px;
  border: 1px solid #FF9A00;
}

.wallet-info p {
  margin: 10px 0;
}
</style>
