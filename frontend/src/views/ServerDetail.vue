<template>
  <div class="server-detail">
    <!-- 顶部导航栏 -->
    <nav class="top-nav">
      <router-link to="/" class="back-link">
        <span class="back-arrow">←</span>
        <span>返回仪表盘</span>
      </router-link>
      <div class="server-title">
        <h1>{{ server.name }}</h1>
        <span class="model-badge">{{ server.model }}</span>
      </div>
      <div class="nav-actions">
        <button @click="refreshData" class="refresh-btn">
          <span class="refresh-icon">🔄</span>
          刷新
        </button>
      </div>
    </nav>

    <!-- 错误提示 -->
    <div v-if="error" class="error-banner">
      <span class="error-icon">⚠️</span>
      <span>{{ error }}</span>
      <button @click="error = null" class="close-error">✕</button>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧：监控面板 -->
      <div class="left-panel">
        <!-- 实时监控卡片 -->
        <div class="monitor-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">实时监控</span>
          </div>
          <div class="monitor-content">
            <div class="metric-item">
              <div class="metric-label">CPU温度</div>
              <div class="metric-value">{{ currentTemp }}°C</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">风扇转速</div>
              <div class="metric-value">{{ currentFanSpeed }} RPM</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">控制模式</div>
              <div class="metric-value">{{ controlModeText }}</div>
            </div>
          </div>
        </div>

        <!-- 系统信息卡片 -->
        <div class="info-card">
          <div class="card-header">
            <span class="card-icon">ℹ️</span>
            <span class="card-title">系统信息</span>
          </div>
          <div class="info-content">
            <div class="info-row">
              <span class="info-label">IPMI主机:</span>
              <span class="info-value">{{ server.ipmi_host }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">连接状态:</span>
              <span class="info-value">{{ connectionStatusText }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">最后更新:</span>
              <span class="info-value">{{ lastUpdateTime }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：控制面板 -->
      <div class="right-panel">
        <!-- 模式选择 -->
        <div class="control-card">
          <div class="card-header">
            <span class="card-icon">🎛️</span>
            <span class="card-title">风扇控制模式</span>
          </div>
          <div class="mode-buttons">
            <button 
              @click="switchToAuto" 
              :class="{ active: server.control_mode === 'auto' }"
              class="mode-btn auto-mode"
            >
              <span class="mode-icon">🤖</span>
              自动模式
            </button>
            <button 
              @click="switchToManual" 
              :class="{ active: server.control_mode === 'manual' }"
              class="mode-btn manual-mode"
            >
              <span class="mode-icon">👋</span>
              手动模式
            </button>
          </div>
        </div>

        <!-- 手动控制 -->
        <div v-if="server.control_mode === 'manual'" class="manual-control-card">
          <div class="card-header">
            <span class="card-icon">⚙️</span>
            <span class="card-title">手动控制</span>
          </div>
          <div class="manual-content">
            <div class="speed-display">
              <span class="speed-label">风扇速度</span>
              <span class="speed-value">{{ manualSpeed }}%</span>
            </div>
            <div class="slider-container">
              <input 
                type="range" 
                min="10" 
                max="100" 
                v-model="manualSpeed"
                class="speed-slider"
                @input="updateManualSpeed"
              >
              <div class="slider-labels">
                <span>10%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
            <button @click="applyManualSpeed" class="apply-btn">
              应用设置
            </button>
          </div>
        </div>

        <!-- 自动控制 -->
        <div v-else class="auto-control-card">
          <div class="card-header">
            <span class="card-icon">📈</span>
            <span class="card-title">温控曲线</span>
          </div>
          <div class="curve-chart">
            <v-chart class="chart" :option="chartOption" autoresize />
          </div>
          
          <div class="curve-controls">
            <div class="card-header">
              <span class="card-icon">🔧</span>
              <span class="card-title">控制点设置</span>
            </div>
            <div class="point-count-control">
              <div class="control-group">
                <label class="control-label">控制点数量</label>
                <div class="slider-container">
                  <input
                    type="range"
                    min="3"
                    max="9"
                    v-model="pointCount"
                    class="point-slider"
                    @input="updatePointCount"
                  >
                  <div class="slider-info">
                    <span class="slider-value">{{ pointCount }}</span>
                    <span class="slider-label">个控制点</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="points-grid">
              <div v-for="(point, index) in fanCurve" :key="index" class="point-item">
                <div class="point-header">
                  <span class="point-number">{{ index + 1 }}</span>
                  <span class="point-label">控制点</span>
                </div>
                <div class="point-inputs">
                  <div class="input-group">
                    <label>温度</label>
                    <input
                      type="number"
                      v-model="point.temp"
                      min="0"
                      max="100"
                      @change="updateCurve"
                      class="temp-input"
                    >
                    <span class="unit">°C</span>
                  </div>
                  <div class="input-group">
                    <label>风扇</label>
                    <input
                      type="number"
                      v-model="point.speed"
                      min="0"
                      max="100"
                      @change="updateCurve"
                      class="speed-input"
                    >
                    <span class="unit">%</span>
                  </div>
                </div>
              </div>
            </div>
            <button @click="saveCurve" class="save-btn">
              保存曲线
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { ElNotification } from 'element-plus';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
]);

export default {
  name: 'ServerDetail',
  components: {
    VChart,
  },
  setup() {
    const route = useRoute();
    const serverId = route.params.id;
    
    // 数据状态
    const server = ref({
      name: 'Loading...',
      model: 'Unknown',
      ipmi_host: 'Unknown',
      control_mode: 'auto'
    });
    const currentTemp = ref('N/A');
    const currentFanSpeed = ref('N/A');
    const manualSpeed = ref(50);
    const fanCurve = ref([
      { temp: 30, speed: 10 },
      { temp: 40, speed: 20 },
      { temp: 50, speed: 40 },
      { temp: 60, speed: 60 },
      { temp: 70, speed: 80 },
      { temp: 80, speed: 100 }
    ]);
    const pointCount = ref(6);
    const error = ref(null);
    const lastUpdateTime = ref('从未更新');
    
    let pollInterval;
    let updateTimer;

    // 计算属性
    const controlModeText = computed(() => {
      return server.value.control_mode === 'manual' ? '手动控制' : '自动控制';
    });

    const connectionStatus = computed(() => {
      return currentTemp.value !== 'N/A' ? 'connected' : 'disconnected';
    });

    const connectionStatusText = computed(() => {
      return currentTemp.value !== 'N/A' ? '已连接' : '未连接';
    });

    const chartOption = computed(() => ({
      backgroundColor: 'transparent',
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: '温度 (°C)',
        min: 'dataMin',
        max: 'dataMax',
        axisLine: {
          lineStyle: {
            color: '#a0aec0',
          },
        },
        nameTextStyle: {
          color: '#a0aec0',
        },
      },
      yAxis: {
        type: 'value',
        name: '风扇 (%)',
        min: 'dataMin',
        max: 'dataMax',
        axisLine: {
          lineStyle: {
            color: '#a0aec0',
          },
        },
        nameTextStyle: {
          color: '#a0aec0',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const point = params[0];
          return `温度: ${point.value[0]}°C <br/> 风扇: ${point.value[1]}%`;
        },
      },
      series: [
        {
          data: fanCurve.value.map(p => [p.temp, p.speed]),
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: {
            color: '#e94560',
            width: 3,
          },
          itemStyle: {
            color: '#e94560',
          },
        },
      ],
    }));

    // 方法
    const updateTime = () => {
      const now = new Date();
      lastUpdateTime.value = now.toLocaleTimeString();
    };

    const showNotification = (message, type = 'success', title = '') => {
      const icons = {
        success: '✅',
        warning: '⚠️',
        error: '❌',
        info: 'ℹ️'
      };
      
      ElNotification({
        title: title || (type === 'success' ? '成功' : type === 'error' ? '错误' : '提示'),
        message: message,
        type: type,
        icon: icons[type],
        duration: 3000,
        position: 'top-right'
      });
    };

    const fetchServerData = async () => {
      try {
        // 获取服务器基本信息
        const serverRes = await fetch(`/api/v1/servers/${serverId}`);
        if (serverRes.ok) {
          server.value = await serverRes.json();
          manualSpeed.value = server.value.manual_fan_speed || 50;
          showNotification('服务器信息加载成功', 'success');
        } else {
          throw new Error('获取服务器信息失败');
        }

        // 获取实时状态
        await fetchCurrentStatus();
        
        // 获取风扇配置
        await fetchFanConfig();
        
        updateTime();
        
      } catch (e) {
        error.value = e.message;
        showNotification(e.message, 'error');
      }
    };

    const fetchCurrentStatus = async () => {
      try {
        const [tempRes, fanRes] = await Promise.all([
          fetch(`/api/v1/control/${serverId}/temperature`),
          fetch(`/api/v1/control/${serverId}/fan/speed`)
        ]);

        if (tempRes.ok) {
          const tempData = await tempRes.json();
          currentTemp.value = tempData.temperature;
        }

        if (fanRes.ok) {
          const fanData = await fanRes.json();
          currentFanSpeed.value = fanData.average_speed_rpm;
        }
        
        updateTime();
      } catch (e) {
        console.error('获取实时状态失败:', e);
      }
    };

    const fetchFanConfig = async () => {
      try {
        const configRes = await fetch(`/api/v1/control/${serverId}/fan/config`);
        if (configRes.ok) {
          const config = await configRes.json();
          if (config.curve && config.curve.points) {
            fanCurve.value = config.curve.points;
            // 同步更新控制点数量
            pointCount.value = config.curve.points.length;
          }
        } else {
          throw new Error('获取风扇配置失败');
        }
      } catch (e) {
        console.error('获取风扇配置失败:', e);
        showNotification('获取风扇配置失败', 'warning');
      }
    };

    const switchToAuto = async () => {
      try {
        const response = await fetch(`/api/v1/control/${serverId}/fan/auto`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ points: fanCurve.value })
        });
        
        if (response.ok) {
          server.value.control_mode = 'auto';
          error.value = null;
          showNotification('已切换到自动模式', 'success');
        } else {
          throw new Error('切换到自动模式失败');
        }
      } catch (e) {
        error.value = e.message;
        showNotification(e.message, 'error');
      }
    };

    const switchToManual = async () => {
      try {
        const response = await fetch(`/api/v1/control/${serverId}/fan/manual`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manual_fan_speed: manualSpeed.value })
        });
        
        if (response.ok) {
          server.value.control_mode = 'manual';
          error.value = null;
          showNotification('已切换到手动模式', 'success');
        } else {
          throw new Error('切换到手动模式失败');
        }
      } catch (e) {
        error.value = e.message;
        showNotification(e.message, 'error');
      }
    };

    const applyManualSpeed = async () => {
      if (server.value.control_mode !== 'manual') return;
      
      try {
        const response = await fetch(`/api/v1/control/${serverId}/fan/manual`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ manual_fan_speed: manualSpeed.value })
        });
        
        if (response.ok) {
          error.value = null;
          showNotification(`手动速度已设置为 ${manualSpeed.value}%`, 'success');
        } else {
          throw new Error('应用手动速度失败');
        }
      } catch (e) {
        error.value = e.message;
        showNotification(e.message, 'error');
      }
    };

    const updateManualSpeed = () => {
      // 手动速度更新
    };

    const updateCurve = () => {
      // 验证曲线数据
      fanCurve.value.forEach(point => {
        point.temp = Math.max(0, Math.min(100, parseInt(point.temp) || 0));
        point.speed = Math.max(0, Math.min(100, parseInt(point.speed) || 0));
      });
    };

    const updatePointCount = () => {
      const newCount = parseInt(pointCount.value);
      const currentCount = fanCurve.value.length;
      
      if (newCount > currentCount) {
        // 增加控制点
        for (let i = currentCount; i < newCount; i++) {
          const temp = Math.round(30 + (i * 50) / (newCount - 1));
          const speed = Math.round(10 + (i * 90) / (newCount - 1));
          fanCurve.value.push({ temp, speed });
        }
      } else if (newCount < currentCount) {
        // 减少控制点
        fanCurve.value.splice(newCount);
      }
      
      updateCurve();
    };

    const saveCurve = async () => {
      try {
        const response = await fetch(`/api/v1/control/${serverId}/fan/auto`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ points: fanCurve.value })
        });
        
        if (response.ok) {
          error.value = null;
          showNotification('温控曲线已保存', 'success');
        } else {
          throw new Error('保存曲线失败');
        }
      } catch (e) {
        error.value = e.message;
        showNotification(e.message, 'error');
      }
    };

    const refreshData = () => {
      fetchCurrentStatus();
    };

    // 生命周期
    onMounted(() => {
      fetchServerData();
      // 每5秒刷新一次实时数据
      pollInterval = setInterval(fetchCurrentStatus, 5000);
      // 每秒更新时间显示
      updateTimer = setInterval(updateTime, 1000);
    });

    onUnmounted(() => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
      if (updateTimer) {
        clearInterval(updateTimer);
      }
    });

    return {
      server,
      currentTemp,
      currentFanSpeed,
      manualSpeed,
      fanCurve,
      error,
      lastUpdateTime,
      controlModeText,
      connectionStatus,
      connectionStatusText,
      chartOption,
      switchToAuto,
      switchToManual,
      applyManualSpeed,
      updateManualSpeed,
      updateCurve,
      saveCurve,
      refreshData,
      pointCount,
      updatePointCount
    };
  }
};
</script>

<style scoped>
/* 滚动条样式 - iOS风格 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  border: none;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

::-webkit-scrollbar-corner {
  background: transparent;
}

/* 右侧面板滚动条 */
.right-panel {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.right-panel::-webkit-scrollbar {
  width: 4px;
}

.right-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}

.server-detail {
  height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #ffffff;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}

/* 顶部导航栏 */
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.back-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e94560;
  text-decoration: none;
  font-weight: 500;
}

.server-title h1 {
  margin: 0;
  font-size: 1.8em;
  color: #ffffff;
}

.model-badge {
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.9em;
  font-weight: 500;
  margin-left: 10px;
}

.refresh-btn {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
  border: 1px solid #e94560;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 错误横幅 */
.error-banner {
  background: rgba(255, 0, 0, 0.2);
  color: #ff6b6b;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255, 0, 0, 0.3);
}

.close-error {
  background: none;
  border: none;
  color: #ff6b6b;
  font-size: 1.2em;
  cursor: pointer;
  margin-left: auto;
}

/* 主要内容区域 */
.main-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  height: calc(100vh - 120px);
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 卡片基础样式 */
.monitor-card, .info-card, .control-card, .manual-control-card, .auto-control-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.card-icon {
  font-size: 1.5em;
}

.card-title {
  color: #ffffff;
  font-weight: 500;
  font-size: 1.2em;
}

/* 监控卡片 */
.monitor-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.metric-label {
  color: #a0aec0;
  font-weight: 500;
}

.metric-value {
  color: #4ade80;
  font-weight: bold;
  font-size: 1.1em;
}

/* 信息卡片 */
.info-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  color: #a0aec0;
}

.info-value {
  color: #ffffff;
  font-weight: 500;
}

/* 右侧面板 */
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

/* 模式按钮 */
.mode-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.mode-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  padding: 15px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
}

.mode-btn.active {
  background: rgba(233, 69, 96, 0.3);
  border-color: #e94560;
}

.mode-icon {
  font-size: 1.5em;
}

/* 手动控制 */
.manual-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.speed-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.speed-label {
  color: #a0aec0;
  font-weight: 500;
}

.speed-value {
  color: #ffffff;
  font-size: 1.5em;
  font-weight: bold;
}

.slider-container {
  margin: 10px 0;
}

.speed-slider {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  outline: none;
  -webkit-appearance: none;
}

.speed-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  background: #e94560;
  border-radius: 50%;
  cursor: pointer;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  color: #a0aec0;
  font-size: 0.8em;
}

.apply-btn {
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  color: white;
  padding: 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 1em;
}

/* 自动控制 */
.curve-chart {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 10px;
  height: 300px;
  margin-bottom: 20px;
}

.chart {
  height: 100%;
  width: 100%;
}

.points-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.point-item {
  background: rgba(255, 255, 255, 0.05);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.point-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.point-number {
  background: #e94560;
  color: white;
  width: 25px;
  height: 25px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9em;
}

.point-label {
  color: #ffffff;
  font-weight: 500;
}

.point-inputs {
  display: flex;
  gap: 10px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-group label {
  color: #a0aec0;
  font-size: 0.8em;
}

.temp-input, .speed-input {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 8px;
  border-radius: 4px;
  width: 60px;
  text-align: center;
}

.unit {
  color: #a0aec0;
  font-size: 0.8em;
  margin-left: 4px;
}

.save-btn {
  background: linear-gradient(45deg, #38a169, #4ade80);
  color: white;
  padding: 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 1em;
}

/* 控制点滑块样式 */
.point-slider {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
  margin: 15px 0;
}

.point-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 24px;
  height: 24px;
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(233, 69, 96, 0.4);
}

.point-slider::-moz-range-thumb {
  width: 24px;
  height: 24px;
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(233, 69, 96, 0.4);
}

.slider-info {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.slider-value {
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 1.1em;
}

.slider-label {
  color: #a0aec0;
  font-size: 0.9em;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .left-panel {
    order: 2;
  }
  
  .right-panel {
    order: 1;
  }
  
  .points-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .top-nav {
    flex-direction: column;
    gap: 15px;
  }
  
  .mode-buttons {
    grid-template-columns: 1fr;
  }
  
  .point-inputs {
    flex-direction: column;
  }
}
</style>