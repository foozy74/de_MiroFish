<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand">MIROFISH</div>
      <div class="nav-links">
        <SignedOut>
          <router-link to="/login" class="login-btn">Anmelden</router-link>
        </SignedOut>
        <SignedIn>
          <div class="user-control">
            <router-link to="/settings" class="settings-link">Einstellungen</router-link>
            <UserButton after-sign-out-url="/" />
          </div>
        </SignedIn>
      </div>
    </nav>

    <div class="main-content">
      <!-- 上半部分：Hero 区域 -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">Universelle Schwarm-Intelligenz-Engine</span>
            <span class="version-text">/ v0.1-Vorschau</span>
          </div>
          
          <h1 class="main-title">
            Beliebigen Bericht hochladen<br>
            <span class="gradient-text">Zukunft sofort simulieren</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              Selbst aus einem einzelnen Textabschnitt kann <span class="highlight-bold">MiroFish</span> vollautomatisch eine Parallelwelt mit bis zu <span class="highlight-orange">einer Million Agenten</span> generieren. Durch gezielte Variableneinspeisung aus der Vogelperspektive wird in komplexen Gruppeninteraktionen ein <span class="highlight-code">"lokales Optimum"</span> im dynamischen Umfeld gesucht.
            </p>
            <p class="slogan-text">
              Die Zukunft in Agent-Schwärmen proben – Entscheidungen nach hundert Schlachten gewinnen<span class="blinking-cursor">_</span>
            </p>
          </div>
           
          <div class="decoration-square"></div>
        </div>
        
        <div class="hero-right">
          <!-- Logo 区域 -->
          <div class="logo-container">
            <img src="../assets/logo/MiroFish_logo_left.jpeg" alt="MiroFish Logo" class="hero-logo" />
          </div>
          
          <button class="scroll-down-btn" @click="scrollToBottom">
            ↓
          </button>
        </div>
      </section>

      <!-- 下半部分：双栏布局 -->
      <section class="dashboard-section">
        <!-- 左栏：状态与步骤 -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> Systemstatus
          </div>
          
          <h2 class="section-title">Bereit</h2>
          <p class="section-desc">
            Prognose-Engine wartet – mehrere unstrukturierte Datendateien hochladen, um die Simulationssequenz zu initialisieren
          </p>
          
          <!-- 数据指标卡片 -->
          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">Günstig</div>
              <div class="metric-label">Ø 5 $ pro Simulation</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">Skalierbar</div>
              <div class="metric-label">Bis zu 1 Mio. Agenten</div>
            </div>
          </div>

          <!-- 项目模拟步骤介绍 (新增区域) -->
          <div class="steps-container">
            <div class="steps-header">
               <span class="diamond-icon">◇</span> Workflow-Sequenz
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">Graphaufbau</div>
                  <div class="step-desc">Realitätskerne extrahieren & Einzel-/Gruppengedächtnis einbinden & GraphRAG aufbauen</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">Umgebungsaufbau</div>
                  <div class="step-desc">Entitätsbeziehungen extrahieren & Personas generieren & Simulationsparameter einbinden</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">Simulation starten</div>
                  <div class="step-desc">Parallelsimulation auf zwei Plattformen & automatische Prognoseanalyse & dynamisches Gedächtnisupdate</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">Bericht generieren</div>
                  <div class="step-desc">ReportAgent mit umfangreichem Werkzeugset interagiert mit der Post-Simulations-Umgebung</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">05</span>
                <div class="step-info">
                  <div class="step-title">Tiefe Interaktion</div>
                  <div class="step-desc">Mit beliebiger Entität der simulierten Welt chatten & mit dem ReportAgent chatten</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右栏：交互控制台 -->
        <div class="right-panel">
          <div class="console-box">
            <!-- 上传区域 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">01 / Realitätskerne</span>
                <span class="console-meta">Unterstützte Formate: PDF, MD, TXT</span>
              </div>
              
              <div 
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />
                
                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">Dateien hierher ziehen</div>
                  <div class="upload-hint">oder klicken zum Durchsuchen</div>
                </div>
                
                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">📄</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 分割线 -->
            <div class="console-divider">
              <span>Parameter eingeben</span>
            </div>

            <!-- 输入区域 -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">>_ 02 / Simulationsanweisung</span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  placeholder="// Simulations- oder Prognoseanforderung in natürlicher Sprache eingeben (z. B.: Wenn Maßnahme X zurückgenommen wird, welche öffentliche Reaktion ist zu erwarten?)"
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">Engine: MiroFish-V1.0</div>
              </div>
            </div>

            <!-- 启动按钮 -->
            <div class="console-section btn-section">
              <button 
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">Engine starten</span>
                <span v-else>Initialisierung...</span>
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 历史项目数据库 -->
      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { SignedIn, SignedOut, UserButton } from '@clerk/vue'

const router = useRouter();

// Formulardaten
const formData = ref({
  simulationRequirement: "",
});

// Dateiliste
const files = ref([]);

// Zustand
const loading = ref(false);
const error = ref("");
const isDragOver = ref(false);

// Referenz auf Datei-Input
const fileInput = ref(null);

// Computed: Kann abgesendet werden?
const canSubmit = computed(() => {
  return (
    formData.value.simulationRequirement.trim() !== "" && files.value.length > 0
  );
});

// 触发文件选择
const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click();
  }
};

// 处理文件选择
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files);
  addFiles(selectedFiles);
};

// 处理拖拽相关
const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true;
  }
};

const handleDragLeave = (e) => {
  isDragOver.value = false;
};

const handleDrop = (e) => {
  isDragOver.value = false;
  if (loading.value) {
    return;
  }

  const droppedFiles = Array.from(e.dataTransfer.files);
  addFiles(droppedFiles);
};

// 添加文件
const addFiles = (newFiles) => {
  const validFiles = newFiles.filter((file) => {
    const ext = file.name.split(".").pop().toLowerCase();
    return ["pdf", "md", "txt"].includes(ext);
  });
  files.value.push(...validFiles);
};

// 移除文件
const removeFile = (index) => {
  files.value.splice(index, 1);
};

// 滚动到底部
const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: "smooth",
  });
};

// 开始模拟 - 立即跳转，API调用在Process页面进行
const startSimulation = () => {
  if (!canSubmit.value || loading.value) {
    return;
  }

  // 存储待上传的数据
  import("../store/pendingUpload.js").then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement);

    // 立即跳转到Process页面（使用特殊标识表示新建项目）
    router.push({
      name: "Process",
      params: { projectId: "new" },
    });
  });
};
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: var(--bg-gradient);
  background-attachment: fixed;
  font-family: 'Inter', sans-serif;
  color: var(--text-primary);
}

/* Top Navigation */
.navbar {
  height: 60px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--glass-border);
  color: var(--text-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.nav-brand {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 20px;
}

.login-btn {
  background: rgba(125, 211, 192, 0.1);
  border: 1px solid rgba(125, 211, 192, 0.3);
  color: var(--accent-teal);
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
}

.login-btn:hover {
  background: rgba(125, 211, 192, 0.2);
  transform: translateY(-1px);
}

.user-control {
  display: flex;
  align-items: center;
  gap: 20px;
}

.settings-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  transition: color 0.2s;
}

.settings-link:hover {
  color: var(--accent-teal);
}

.github-link {
  color: var(--text-primary);
  text-decoration: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: var(--transition);
}

.github-link:hover {
  opacity: 0.8;
}

.arrow {
  font-family: sans-serif;
}

/* 主要内容区 */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Hero 区域 */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.75rem;
}

.version-text {
  color: #999;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 700;
  margin: 0 0 40px 0;
  letter-spacing: -2px;
  color: var(--text-primary);
  font-family: 'Outfit', sans-serif;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text-secondary);
  max-width: 640px;
  margin-bottom: 50px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-bold {
  color: var(--text-primary);
  font-weight: 700;
}

.highlight-orange {
  color: var(--orange);
  font-weight: 700;
  font-family: var(--font-mono);
}

.highlight-code {
  background: rgba(91, 155, 213, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9em;
  color: var(--accent-teal);
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 1px;
  border-left: 3px solid var(--accent-teal);
  padding-left: 15px;
  margin-top: 20px;
  font-family: 'Outfit', sans-serif;
}

.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
}

.hero-right {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  padding-right: 40px;
}

.hero-logo {
  max-width: 500px;
  width: 100%;
  filter: drop-shadow(0 0 30px rgba(125, 211, 192, 0.4)) drop-shadow(0 0 60px rgba(91, 155, 213, 0.3));
  transition: filter 0.3s ease;
}

.hero-logo:hover {
  filter: drop-shadow(0 0 40px rgba(125, 211, 192, 0.6)) drop-shadow(0 0 80px rgba(91, 155, 213, 0.4));
}

.scroll-down-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--orange);
  font-size: 1.2rem;
  transition: all 0.2s;
}

.scroll-down-btn:hover {
  border-color: var(--orange);
}

/* Dashboard 双栏布局 */
.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid var(--border);
  padding-top: 60px;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

/* 左侧面板 */
.left-panel {
  flex: 0.8;
}

.panel-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--accent-teal);
  font-size: 0.8rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
}

.section-desc {
  color: var(--text-secondary);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--card-radius);
  padding: 20px 30px;
  min-width: 150px;
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 5px;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.metric-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* 项目模拟步骤介绍 */
.steps-container {
  border: 1px solid var(--border);
  padding: 30px;
  position: relative;
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--accent-teal);
  opacity: 1;
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* 右侧交互控制台 */
.right-panel {
  flex: 1.2;
}

/* Right Panel Console */
.console-box {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--card-radius);
  padding: 8px;
}

.console-section {
  padding: 20px;
}

.console-section.btn-section {
  padding-top: 0;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.upload-zone {
  border: 1px dashed var(--glass-border);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--transition);
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone:hover {
  background: rgba(91, 155, 213, 0.1);
  border-color: var(--accent-blue);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  border: 1px solid var(--glass-border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  color: var(--accent-teal);
}

.upload-title {
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 5px;
  color: var(--text-primary);
}

.upload-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.file-list {
  width: 100%;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-item {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: var(--text-primary);
}

.file-name {
  flex: 1;
  margin: 0 10px;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: var(--accent-teal);
  transition: var(--transition);
}

.remove-btn:hover {
  color: var(--accent-blue);
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--glass-border);
}

.console-divider span {
  padding: 0 15px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid var(--glass-border);
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
  color: var(--text-primary);
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--accent-teal);
}

.start-engine-btn {
  width: 100%;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  color: #0a0f1a;
  border: none;
  padding: 20px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: var(--transition);
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
}

/* Hover state (not disabled) */
.start-engine-btn:not(:disabled) {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  border: none;
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 40px rgba(125, 211, 192, 0.4), 0 0 60px rgba(91, 155, 213, 0.3);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  cursor: not-allowed;
  transform: none;
  border: 1px solid var(--glass-border);
}

/* 可点击状态（非禁用） */
.start-engine-btn:not(:disabled) {
  background: var(--black);
  border: 1px solid var(--black);
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--orange);
  border-color: var(--orange);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
  transform: none;
  border: 1px solid #E5E5E5;
}

/* 引导动画：微妙的边框脉冲 */
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }
  
  .hero-section {
    flex-direction: column;
  }
  
  .hero-left {
    padding-right: 0;
    margin-bottom: 40px;
  }
  
  .hero-logo {
    max-width: 200px;
    margin-bottom: 20px;
  }
}
</style>
