<template>
  <div class="server-detail">
    <!-- 顶部导航栏 - 玻璃拟态风格 -->
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

    <!-- 主要内容区域 - 重新设计的布局 -->
    <div class="main-content">
      <!-- 顶部状态区域 -->
      <div class="status-grid">
        <!-- 服务器状态卡片 -->
        <div class="status-card">
          <div class="card-header">
            <span class="card-icon">🖥️</span>
            <span class="card-title">服务器状态</span>
          </div>
          <div class="status-content">
            <div class="status-item">
              <div class="status-label">IPMI主机</div>
              <div class="status-value">{{ server.ipmi_host }}</div>
            </div>
            <div class="status-item">
              <div class="status-label">连接状态</div>
              <div class="status-value" :class="connectionStatus">
                {{ connectionStatusText }}
              </div>
            </div>
            <div class="status-item">
              <div class="status-label">最后更新</div>
              <div class="status-value">{{ lastUpdateTime }}</div>
            </div>
          </div>
        </div>

        <!-- 实时监控卡片 -->
        <div class="realtime-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">实时监控</span>
          </div>
          <div class="realtime-content">
            <div class="metric-large">
              <div class="metric-icon">🌡️</div>
              <div class="metric-data">
                <div class="metric-value-large">{{ currentTemp }}°C</div>
                <div class="metric-label">CPU温度</div>
              </div>
            </div>
            <div class="metric-large">
              <div class="metric-icon">🌀</div>
              <div class="metric-data">
                <div class="metric-value-large">{{ currentFanSpeed }}</div>
                <div class="metric-label">风扇转速 RPM</div>
              </div>
            </div>
            <div class="metric-large">
              <div class="metric-icon">🎛️</div>
              <div class="metric-data">
                <div class="metric-value-large">{{ controlModeText }}</div>
                <div class="metric-label">控制模式</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史趋势区域 -->
      <div class="history-section">
        <div class="section-header">
          <div class="section-title">
            <span class="section-icon">📈</span>
            <h2>历史趋势</h2>
            <span class="section-subtitle">最近3小时温度与风扇转速变化</span>
          </div>
        </div>
        <div class="history-chart-container">
          <v-chart class="chart" :option="historyChartOption" autoresize />
        </div>
      </div>

      <!-- 控制区域 -->
      <div class="control-grid">
        <!-- 模式选择和手动控制 -->
        <div class="control-left">
          <div class="control-card">
            <div class="card-header">
              <span class="card-icon">🎛️</span>
              <span class="card-title">控制模式</span>
            </div>
            <div class="mode-buttons">
              <button @click="switchToAuto" :class="{ active: server.control_mode === 'auto' }"
                class="mode-btn auto-mode">
                <span class="mode-icon">🤖</span>
                自动模式
              </button>
              <button @click="switchToManual" :class="{ active: server.control_mode === 'manual' }"
                class="mode-btn manual-mode">
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
                <input type="range" min="10" max="100" v-model="manualSpeed" class="speed-slider"
                  @input="updateManualSpeed">
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
        </div>

        <!-- 温控曲线和控制点 -->
        <div class="control-right" v-if="server.control_mode === 'auto'">
          <div class="curve-card">
            <div class="card-header">
              <span class="card-icon">📊</span>
              <span class="card-title">温控曲线</span>
            </div>
            <div class="curve-chart-container">
              <v-chart class="chart" :option="chartOption" autoresize />
            </div>
          </div>

          <div class="points-card">
            <div class="card-header">
              <span class="card-icon">🔧</span>
              <span class="card-title">控制点设置</span>
            </div>
            <div class="point-count-control">
              <div class="control-group">
                <label class="control-label">控制点数量</label>
                <div class="slider-container">
                  <input type="range" min="3" max="9" v-model="pointCount" class="point-slider" @input="updatePointCount">
                  <div class="slider-info">
                    <span class="slider-value">{{ pointCount }}</span>
                    <span class="slider-label">个控制点</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="points-grid-compact">
              <div v-for="(point, index) in fanCurve" :key="index" class="point-item-compact">
                <div class="point-header-compact">
                  <span class="point-number-compact">{{ index + 1 }}</span>
                </div>
                <div class="point-inputs-compact">
                  <div class="input-group-compact">
                    <label>温度</label>
                    <input type="number" v-model="point.temp" min="0" max="100" @change="updateCurve" class="temp-input-compact">
                    <span class="unit">°C</span>
                  </div>
                  <div class="input-group-compact">
                    <label>风扇</label>
                    <input type="number" v-model="point.speed" min="0" max="100" @change="updateCurve"
                      class="speed-input-compact">
                    <span class="unit">%</span>
                  </div>
                </div>
              </div>
            </div>
            <button @click="saveCurve" class="save-btn-compact">
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
    const temperatureHistory = ref([]);
    const fanSpeedHistory = ref([]);
    
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

    const historyChartOption = computed(() => {
      // Helper function to deduplicate and format data
      const processHistoryData = (historyArray, valueField) => {
        if (!historyArray || historyArray.length === 0) return [];
        
        // Use a map to store the latest value for each unique timestamp (ISO string)
        const dataMap = new Map();
        historyArray.forEach(item => {
          dataMap.set(new Date(item.timestamp).toISOString(), item[valueField]);
        });
        
        // Convert map back to array for ECharts, and sort by time
        return Array.from(dataMap.entries())
          .map(([timestamp, value]) => [timestamp, value])
          .sort((a, b) => new Date(a[0]) - new Date(b[0]));
      };

      const tempData = processHistoryData(temperatureHistory.value, 'temperature');
      const fanData = processHistoryData(fanSpeedHistory.value, 'average_speed_rpm');

      return {
        backgroundColor: 'transparent',
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true,
        },
        xAxis: {
          type: 'time',
          name: '时间',
          axisLine: {
            lineStyle: {
              color: '#a0aec0',
            },
          },
          nameTextStyle: {
            color: '#a0aec0',
          },
          axisLabel: {
            rotate: 45,
            formatter: '{HH}:{mm}', // Format time on the axis
          }
        },
        yAxis: [
          {
            type: 'value',
            name: '温度 (°C)',
            position: 'left',
            axisLine: {
              lineStyle: {
                color: '#ff6b6b',
              },
            },
            nameTextStyle: {
              color: '#ff6b6b',
            },
            axisLabel: {
              color: '#ff6b6b',
            },
          },
          {
            type: 'value',
            name: '风扇转速 (RPM)',
            position: 'right',
            axisLine: {
              lineStyle: {
                color: '#4ade80',
              },
            },
            nameTextStyle: {
              color: '#4ade80',
            },
            axisLabel: {
              color: '#4ade80',
            },
          }
        ],
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: function (params) {
            if (!params || params.length === 0) return '';
            const time = new Date(params[0].value[0]).toLocaleString('zh-CN', {
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });
            let result = time + '<br/>';
            params.forEach(param => {
              const value = param.value[1];
              if (value !== null && value !== undefined) {
                result += `${param.marker}${param.seriesName}: ${value.toFixed(2)}<br/>`;
              }
            });
            return result;
          }
        },
        legend: {
          data: ['温度', '风扇转速'],
          textStyle: {
            color: '#a0aec0'
          }
        },
        series: [
          {
            name: '温度',
            data: tempData,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
              color: '#ff6b6b',
              width: 2,
            },
            yAxisIndex: 0,
          },
          {
            name: '风扇转速',
            data: fanData,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
              color: '#4ade80',
              width: 2,
            },
            yAxisIndex: 1,
          },
        ],
      };
    });

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
        
        // 获取历史数据
        await fetchHistoryData();
        
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

    const fetchHistoryData = async () => {
      try {
        // 获取最近温度历史
        const tempRes = await fetch(`/api/v1/history/${serverId}/temperature/recent?limit=540`);
        if (tempRes.ok) {
          temperatureHistory.value = await tempRes.json();
        }

        // 获取最近风扇转速历史
        const fanRes = await fetch(`/api/v1/history/${serverId}/fan-speed/recent?limit=540`);
        if (fanRes.ok) {
          fanSpeedHistory.value = await fanRes.json();
        }
      } catch (e) {
        console.error('获取历史数据失败:', e);
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
      historyChartOption,
      switchToAuto,
      switchToManual,
      applyManualSpeed,
      updateManualSpeed,
      updateCurve,
      saveCurve,
      refreshData,
      pointCount,
      updatePointCount,
      fetchHistoryData
    };
  }
};
</script>

<style scoped>
/* 玻璃拟态风格基础样式 */
.server-detail {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
  color: #ffffff;
  padding: 20px;
  box-sizing: border-box;
}

/* 顶部导航栏 */
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.back-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64ffda;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
}

.back-link:hover {
  color: #4fc3f7;
  transform: translateX(-2px);
}

.server-title h1 {
  margin: 0;
  font-size: 1.8em;
  color: #ffffff;
  font-weight: 600;
}

.model-badge {
  background: linear-gradient(45deg, #64ffda, #4fc3f7);
  color: #0f0f23;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.9em;
  font-weight: 600;
  margin-left: 12px;
}

.refresh-btn {
  background: rgba(100, 255, 218, 0.15);
  color: #64ffda;
  border: 1px solid rgba(100, 255, 218, 0.3);
  padding: 10px 18px;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
  font-weight: 500;
}

.refresh-btn:hover {
  background: rgba(100, 255, 218, 0.25);
  transform: translateY(-1px);
}

/* 错误横幅 */
.error-banner {
  background: rgba(255, 59, 48, 0.15);
  color: #ff3b30;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(255, 59, 48, 0.3);
  backdrop-filter: blur(10px);
}

.close-error {
  background: none;
  border: none;
  color: #ff3b30;
  font-size: 1.2em;
  cursor: pointer;
  margin-left: auto;
  padding: 4px;
}

/* 主要内容区域 */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
}

/* 卡片基础样式 - 玻璃拟态 */
.status-card, .realtime-card, .control-card, .manual-control-card, .curve-card, .points-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.status-card:hover, .realtime-card:hover, .control-card:hover, .manual-control-card:hover, 
.curve-card:hover, .points-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.card-icon {
  font-size: 1.5em;
}

.card-title {
  color: #ffffff;
  font-weight: 600;
  font-size: 1.2em;
}

/* 状态卡片内容 */
.status-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.status-label {
  color: #a0aec0;
  font-weight: 500;
}

.status-value {
  color: #ffffff;
  font-weight: 600;
}

.status-value.connected {
  color: #4ade80;
}

.status-value.disconnected {
  color: #ff6b6b;
}

/* 实时监控卡片 */
.realtime-content {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.metric-large {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
}

.metric-icon {
  font-size: 2em;
}

.metric-data {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-value-large {
  color: #64ffda;
  font-size: 1.8em;
  font-weight: 700;
}

.metric-label {
  color: #a0aec0;
  font-size: 0.9em;
}

/* 历史趋势区域 */
.history-section {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title h2 {
  color: #ffffff;
  font-size: 1.4em;
  font-weight: 600;
  margin: 0;
}

.section-subtitle {
  color: #a0aec0;
  font-size: 0.9em;
  margin-left: 8px;
}

.section-icon {
  font-size: 1.5em;
}

.history-chart-container {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  height: 400px;
}

/* 控制网格 */
.control-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
}

.control-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.control-right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 模式按钮 */
.mode-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.mode-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #ffffff;
  padding: 16px;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-1px);
}

.mode-btn.active {
  background: rgba(100, 255, 218, 0.2);
  border-color: #64ffda;
  box-shadow: 0 4px 16px rgba(100, 255, 218, 0.2);
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
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.speed-label {
  color: #a0aec0;
  font-weight: 500;
}

.speed-value {
  color: #64ffda;
  font-size: 1.5em;
  font-weight: 700;
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
  background: #64ffda;
  border-radius: 50%;
  cursor: pointer;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  color: #a0aec0;
  font-size: 0.8em;
}

.apply-btn {
  background: linear-gradient(45deg, #64ffda, #4fc3f7);
  color: #0f0f23;
  padding: 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1em;
  transition: all 0.3s ease;
}

.apply-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(100, 255, 218, 0.3);
}

/* 温控曲线 */
.curve-chart-container {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  height: 300px;
}

/* 控制点设置 */
.point-count-control {
  margin-bottom: 20px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-label {
  color: #a0aec0;
  font-weight: 500;
}

.point-slider {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
  margin: 12px 0;
}

.point-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  background: #64ffda;
  border-radius: 50%;
  cursor: pointer;
}

.slider-info {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.slider-value {
  background: #64ffda;
  color: #0f0f23;
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 1em;
}

.slider-label {
  color: #a0aec0;
  font-size: 0.9em;
}

/* 紧凑的控制点网格 */
.points-grid-compact {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.point-item-compact {
  background: rgba(255, 255, 255, 0.03);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.point-header-compact {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.point-number-compact {
  background: #64ffda;
  color: #0f0f23;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.8em;
}

.point-inputs-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group-compact {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-group-compact label {
  color: #a0aec0;
  font-size: 0.8em;
}

.temp-input-compact, .speed-input-compact {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
  padding: 6px;
  border-radius: 6px;
  width: 100%;
  text-align: center;
  font-size: 0.9em;
}

.unit {
  color: #a0aec0;
  font-size: 0.8em;
  margin-left: 4px;
}

.save-btn-compact {
  background: linear-gradient(45deg, #4ade80, #38a169);
  color: white;
  padding: 10px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9em;
  transition: all 0.3s ease;
}

.save-btn-compact:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(74, 222, 128, 0.3);
}

/* 图表通用样式 */
.chart {
  height: 100%;
  width: 100%;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .control-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .realtime-content {
    grid-template-columns: 1fr;
  }
  
  .mode-buttons {
    grid-template-columns: 1fr;
  }
  
  .points-grid-compact {
    grid-template-columns: 1fr;
  }
  
  .top-nav {
    flex-direction: column;
    gap: 16px;
  }
}
</style>