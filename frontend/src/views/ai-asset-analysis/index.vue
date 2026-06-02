<template>
  <div class="ai-asset-analysis-page" :class="{ 'theme-dark': isDarkTheme }">
    <a-card :bordered="false" class="workspace-card">
      <a-tabs v-model="activeTab" class="workspace-tabs" size="large">
        <a-tab-pane key="quick">
          <span slot="tab">
            <a-icon type="thunderbolt" />
            {{ $t('aiAssetAnalysis.tabs.quick') }}
          </span>
          <div class="tab-body">
            <AnalysisView
              v-if="activeTab === 'quick'"
              :embedded="true"
            />
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import AnalysisView from '@/views/ai-analysis'

export default {
  name: 'AIAssetAnalysis',
  components: {
    AnalysisView
  },
  data () {
    return {
      activeTab: 'quick'
    }
  },
  computed: {
    ...mapState({
      navTheme: state => state.app.theme
    }),
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    }
  }
}
</script>

<style lang="less" scoped>
.ai-asset-analysis-page {
  padding: 20px;
  min-height: calc(100vh - 120px);
  background: #f0f2f5;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;

  .workspace-card {
    border-radius: 14px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    border: 1px solid #e8e8e8;

    ::v-deep .ant-card-body { padding: 0; }

    .workspace-tabs {
      ::v-deep .ant-tabs-bar {
        margin-bottom: 0;
        padding: 0 20px;
        border-bottom: 1px solid #f0f0f0;
      }
      ::v-deep .ant-tabs-tab {
        font-size: 15px;
        font-weight: 600;
        padding: 14px 16px;
      }
    }

    .tab-body {
      ::v-deep .ai-analysis-container.embedded {
        border-radius: 0;
        overflow: hidden;
      }
    }
  }

  &.theme-dark {
    background: #141414;

    .workspace-card {
      background: #1c1c1c;
      border-color: #2a2a2a;

      .workspace-tabs {
        ::v-deep .ant-tabs-bar { border-bottom-color: #2a2a2a; }
        ::v-deep .ant-tabs-tab { color: #8b949e; &:hover { color: #c9d1d9; } }
        ::v-deep .ant-tabs-tab-active { color: #a78bfa; }
        ::v-deep .ant-tabs-ink-bar { background-color: #a78bfa; }
      }
    }
  }
}

@media (max-width: 768px) {
  .ai-asset-analysis-page {
    padding: 8px;
    min-height: auto;

    .workspace-card {
      border-radius: 10px;

      .workspace-tabs {
        ::v-deep .ant-tabs-bar {
          padding: 0 6px;
        }

        ::v-deep .ant-tabs-nav-scroll {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }

        ::v-deep .ant-tabs-tab {
          font-size: 14px;
          padding: 10px 8px;
          margin-right: 2px;
          white-space: nowrap;
        }
      }
    }
  }
}

@media (max-width: 480px) {
  .ai-asset-analysis-page {
    padding: 4px;

    .workspace-card {
      .workspace-tabs {
        ::v-deep .ant-tabs-bar {
          padding: 0 4px;
        }
        ::v-deep .ant-tabs-tab {
          font-size: 13px;
          padding: 8px 6px;
        }
      }
    }
  }
}
</style>
