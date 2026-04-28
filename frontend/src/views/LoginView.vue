<template>
  <div class="auth-page">
    <nav class="auth-nav">
      <router-link to="/" class="nav-brand">MIROFISH</router-link>
    </nav>
    <div class="auth-container">
      <SignIn />
    </div>
  </div>
</template>

<script setup>
import { SignIn } from '@clerk/vue'
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: var(--bg-gradient);
  display: flex;
  flex-direction: column;
}

.auth-nav {
  padding: 20px 40px;
}

.nav-brand {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.5rem;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-decoration: none;
}

.auth-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}
</style>
