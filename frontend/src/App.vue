<template>
  <router-view />
</template>

<script setup>
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg-color: #0a0f1a;
  --bg-gradient: linear-gradient(135deg, #0a0f1a 0%, #0d1b2a 50%, #1b263b 100%);
  --text-primary: #e8f1f5;
  --text-secondary: #8899a6;
  --accent-blue: #5b9bd5;
  --accent-teal: #7dd3c0;
  --accent-purple: #9b8fb8;
  --glass-bg: rgba(255, 255, 255, 0.05);
  --glass-border: rgba(125, 211, 192, 0.15);
  --card-radius: 16px;
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-primary);
  background: var(--bg-gradient);
  background-attachment: fixed;
  min-height: 100vh;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

::-webkit-scrollbar-thumb {
  background: var(--accent-teal);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent-blue);
}

button {
  font-family: inherit;
}

.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--card-radius);
}

.gradient-text {
  background: linear-gradient(135deg, #ffffff, #7dd3c0, #5b9bd5);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 40px rgba(125, 211, 192, 0.5);
  filter: drop-shadow(0 0 8px rgba(125, 211, 192, 0.3));
}
</style>
