<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <img src="/favico.png" alt="Logo" class="login-logo" />
        <h1>Hồng Hà HRMS</h1>
        <p>Hệ thống Quản lý Nhân sự</p>
      </div>

      <form @submit.prevent="onSubmit" class="login-form">
        <div class="field">
          <label for="email">Email</label>
          <InputText
            id="email"
            v-model="email"
            type="email"
            placeholder="Nhập email đăng nhập"
            autocomplete="email"
            fluid
          />
        </div>

        <div class="field">
          <label for="password">Mật khẩu</label>
          <Password
            id="password"
            v-model="password"
            placeholder="Nhập mật khẩu"
            :feedback="false"
            toggleMask
            fluid
          />
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          label="Đăng nhập"
          icon="pi pi-sign-in"
          :loading="loading"
          fluid
        />
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useAuthStore } from '@/stores/auth'
import { isOffline, isNetworkError } from '@/utils/network'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  if (!email.value || !password.value) return
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) ?? '/reports/dashboard'
    router.push(redirect)
  } catch (err) {
    if (isOffline() || isNetworkError(err)) {
      error.value = 'Không có kết nối Internet. Vui lòng kiểm tra mạng và thử lại.'
    } else {
      error.value = 'Sai email hoặc mật khẩu.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #042f2e 0%, #115e59 50%, #0f766e 100%);
  padding: 1rem;
}

.login-card {
  background: var(--p-surface-0);
  border-radius: 12px;
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;

  .login-logo {
    width: 56px;
    height: 56px;
    margin-bottom: 0.75rem;
  }

  h1 {
    margin: 0 0 0.25rem;
    font-size: 1.5rem;
    font-weight: 800;
    color: #0f766e;
  }

  p {
    margin: 0;
    color: var(--p-text-muted-color);
    font-size: 0.875rem;
  }
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;

  label {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--p-text-color);
  }
}
</style>
