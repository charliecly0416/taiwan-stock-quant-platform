<template>
  <div class="tw-stock-monitor">
    <div class="topbar">
      <div>
        <h2>台股趨勢監控</h2>
        <div class="subline">
          <a-tag color="blue">Research</a-tag>
          <a-tag color="green">orders_enabled=false</a-tag>
          <a-tag color="purple">Human Review</a-tag>
        </div>
      </div>
      <div class="top-actions">
        <a-switch
          v-model="autoRefreshEnabled"
          size="small"
          :disabled="!refreshIntervalMs"
          @change="handleAutoRefreshChange"
        />
        <span class="refresh-status">{{ refreshStatusText }}</span>
        <a-button @click="openConfigDrawer">
          <a-icon type="setting" /> 配置
        </a-button>
        <a-button @click="refreshAll" :loading="loading">
          <a-icon type="reload" /> 刷新
        </a-button>
        <a-button type="primary" @click="runScan" :loading="scanning">
          <a-icon type="scan" /> 手動研究掃描
        </a-button>
      </div>
    </div>

    <div class="summary-grid">
      <div class="metric-card">
        <span class="metric-label">監控名稱</span>
        <strong>{{ config.name || 'default' }}</strong>
        <small>{{ config.enabled ? 'enabled' : 'disabled' }}</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">觀察標的</span>
        <strong>{{ config.symbols.length }}</strong>
        <small>{{ config.symbols.join(', ') || '-' }}</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">掃描健康度</span>
        <strong :class="healthClass">{{ scanHealth.status || 'unknown' }}</strong>
        <small>success {{ scanHealth.success_rate == null ? '-' : (scanHealth.success_rate * 100).toFixed(1) + '%' }}</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">未讀提醒</span>
        <strong>{{ unreadCount }}</strong>
        <small>{{ alertItems.length }} alerts loaded</small>
      </div>
    </div>

    <a-alert
      v-if="degradedNotice"
      class="monitor-degraded-alert"
      type="warning"
      show-icon
      :message="degradedNotice"
    />

    <a-card ref="readonlyBacktestPanel" v-if="backtestPanelVisible" class="readonly-backtest-card" :bordered="false">
      <template slot="title">
        <div class="card-title-line">
          <span>台股只讀回測驗證</span>
          <div class="readonly-tags">
            <a-tag color="blue">historical simulation</a-tag>
            <a-tag color="green">orders_enabled=false</a-tag>
            <a-tag color="purple">connects_to_broker=false</a-tag>
          </div>
        </div>
      </template>
      <div class="backtest-toolbar">
        <a-select v-model="backtestForm.strategyId" style="width: 220px" size="small" :loading="loadingBacktestTemplates">
          <a-select-option v-for="template in backtestTemplates" :key="template.id" :value="template.id">{{ template.name }}</a-select-option>
        </a-select>
        <a-date-picker v-model="backtestForm.startDate" size="small" style="width: 150px" />
        <a-date-picker v-model="backtestForm.endDate" size="small" style="width: 150px" />
        <a-input-number v-model="backtestForm.initialCapital" size="small" :min="10000" :step="100000" style="width: 150px" />
        <a-button type="primary" size="small" :loading="runningBacktest" @click="runReadonlyBacktest">
          <a-icon type="line-chart" /> 歷史模擬
        </a-button>
      </div>
      <a-alert
        v-if="backtestError"
        class="backtest-alert"
        type="warning"
        show-icon
        :message="backtestError"
      />
      <div v-if="backtestResult" class="backtest-result">
        <div class="backtest-metrics">
          <div class="metric-card compact">
            <span class="metric-label">總收益</span>
            <strong>{{ formatSignedPercentFromNumber(backtestMetrics.totalReturn) }}</strong>
          </div>
          <div class="metric-card compact">
            <span class="metric-label">最大回撤</span>
            <strong>{{ formatSignedPercentFromNumber(backtestMetrics.maxDrawdown) }}</strong>
          </div>
          <div class="metric-card compact">
            <span class="metric-label">勝率</span>
            <strong>{{ formatSignedPercentFromNumber(backtestMetrics.winRate) }}</strong>
          </div>
          <div class="metric-card compact">
            <span class="metric-label">交易數</span>
            <strong>{{ backtestMetrics.totalTrades == null ? '-' : backtestMetrics.totalTrades }}</strong>
          </div>
        </div>
        <div class="backtest-grid">
          <div class="chart-frame backtest-chart-frame">
            <canvas ref="backtestEquityChart" class="tw-chart-canvas" width="900" height="300"></canvas>
            <div v-if="!backtestEquityCurve.length" class="chart-empty">尚無資金曲線</div>
          </div>
          <div class="backtest-side">
            <div class="readonly-note">歷史模擬，僅供人工復盤；不連接 broker，不建立委託，不寫入持倉。回測結果不是 qlib score 的驗證結論，也不是未來收益承諾。</div>
            <div class="assumption-list">
              <span>市場 {{ backtestAssumptions.market || 'TWStock' }}</span>
              <span>頻率 {{ backtestAssumptions.strategyTimeframe || '1D' }}</span>
              <span>幣別 {{ backtestAssumptions.currency || 'TWD' }}</span>
              <span>手續費 {{ formatNumber(backtestAssumptions.commission, 6) }}</span>
              <span>滑價 {{ formatNumber(backtestAssumptions.slippage, 6) }}</span>
              <span>整股 {{ backtestAssumptions.lotSize || 1000 }} / enforced={{ String(backtestAssumptions.lotSizeEnforced) }}</span>
            </div>
            <div class="quality-list">
              <span>Bars {{ backtestDataQuality.barCount || backtestDataQuality.bar_count || 0 }}</span>
              <span>Latest {{ backtestDataQuality.latestDate || '-' }}</span>
              <span>Source {{ backtestDataQuality.preferredSource || backtestDataQuality.source || '-' }}</span>
              <template v-if="backtestQualityWarnings.length">
                <a-tag v-for="warning in backtestQualityWarnings" :key="warning" color="orange">{{ warning }}</a-tag>
              </template>
              <a-tag v-else color="green">data quality ok</a-tag>
            </div>
          </div>
        </div>
        <a-table
          class="backtest-trades"
          row-key="_key"
          size="small"
          :columns="backtestTradeColumns"
          :data-source="backtestTrades"
          :pagination="{ pageSize: 6 }"
        />
      </div>
    </a-card>


    <a-card class="qlib-option-c-card" :bordered="false">
      <template slot="title">
        <div class="card-title-line">
          <span>qlib Option C 研究排序</span>
          <div class="readonly-tags">
            <a-tag color="blue">Research only</a-tag>
            <a-tag color="green">Not order</a-tag>
            <a-tag color="purple">Read-only</a-tag>
          </div>
        </div>
      </template>
      <div class="qlib-toolbar">
        <a-radio-group v-model="qlibBucket" size="small" @change="handleQlibBucketChange">
          <a-radio-button value="top30">Top 30</a-radio-button>
          <a-radio-button value="top50">Top 50</a-radio-button>
        </a-radio-group>
        <a-button size="small" @click="loadQlibSignals" :loading="loadingQlibSignals">
          <a-icon type="reload" /> 更新研究排序
        </a-button>
        <a-button v-if="selectedQlibRunId" size="small" @click="returnToLatestQlib" :loading="loadingQlibSignals">
          <a-icon type="rollback" /> 回到 latest
        </a-button>
      </div>
      <div class="qlib-health-panel">
        <div class="qlib-health-header">
          <div>
            <strong>qlib Option C 数据状态</strong>
            <span class="muted">趋势解释依赖 TWStock local daily bars；回测依赖 qd_tw_stock_daily_bars。</span>
          </div>
          <a-button size="small" @click="loadQlibHealth" :loading="loadingQlibHealth">
            <a-icon type="reload" /> 更新狀態
          </a-button>
        </div>
        <div class="qlib-health-tags">
          <a-tag :color="qlibHealthStatusColor">{{ qlibHealthStatusText }}</a-tag>
          <a-tag v-if="qlibHealthFreshness && qlibHealthFreshness.stale" color="orange">stale</a-tag>
          <a-tag v-if="qlibHealthWaitStatePresent" color="gold">wait-state</a-tag>
          <a-tag v-if="qlibHealthMissing" color="red">missing</a-tag>
          <a-tag v-if="qlibHealthLatest && qlibHealthLatest.accepted_validated" color="green">validated</a-tag>
        </div>
        <div class="qlib-health-grid">
          <span>asof <strong>{{ qlibHealthLatest.asof || '-' }}</strong></span>
          <span>run_id <strong>{{ qlibHealthLatest.run_id || '-' }}</strong></span>
          <span>artifact age <strong>{{ qlibHealthAgeText }}</strong></span>
          <span>recent runs <strong>{{ qlibHealthRunText }}</strong></span>
        </div>
        <div v-if="qlibHealthWarnings.length" class="qlib-warning-list">
          <a-tag v-for="warning in qlibHealthWarnings" :key="`health-${warning}`" color="orange">{{ warning }}</a-tag>
        </div>
        <a-alert
          v-if="qlibHealthError"
          class="qlib-state-alert"
          type="warning"
          show-icon
          :message="qlibHealthError"
        />
      </div>
      <div class="qlib-run-browser">
        <div class="qlib-run-header">
          <strong>qlib Option C 歷史研究 run</strong>
          <div class="qlib-run-actions">
            <a-select v-model="qlibRunStatusFilter" size="small" style="width: 130px" @change="loadQlibRuns">
              <a-select-option value="all">all</a-select-option>
              <a-select-option value="accepted">accepted</a-select-option>
              <a-select-option value="blocked">blocked</a-select-option>
              <a-select-option value="wait_state">wait_state</a-select-option>
            </a-select>
            <a-button size="small" @click="loadQlibRuns" :loading="loadingQlibRuns">
              <a-icon type="reload" /> 更新列表
            </a-button>
          </div>
        </div>
        <a-table
          row-key="run_id"
          size="small"
          class="qlib-run-table"
          :loading="loadingQlibRuns"
          :columns="qlibRunColumns"
          :data-source="qlibRuns"
          :pagination="false"
          :custom-row="qlibRunCustomRow"
        >
          <template slot="status" slot-scope="status, row">
            <a-tag :color="qlibRunStatusColor(row)">{{ status || 'unknown' }}</a-tag>
            <a-tag v-if="row.accepted_validated" color="green">validated</a-tag>
          </template>
          <template slot="run_id" slot-scope="runId">
            <span class="run-id-text">{{ runId }}</span>
          </template>
          <template slot="rows" slot-scope="text, row">
            <span>{{ row.prediction_rows || '-' }} / {{ row.top30_rows || '-' }} / {{ row.top50_rows || '-' }}</span>
          </template>
          <template slot="warnings" slot-scope="text, row">
            <template v-if="row.warnings && row.warnings.length">
              <a-tag v-for="warning in row.warnings.slice(0, 2)" :key="`${row.run_id}-${warning}`" color="orange">{{ warning }}</a-tag>
            </template>
            <span v-else class="muted">-</span>
          </template>
        </a-table>
      </div>
      <div class="qlib-ops-panel">
        <div class="qlib-ops-header">
          <div>
            <strong>qlib Option C Ops Dry-run</strong>
            <span class="muted">Dry-run only · Research ops · No latest update · No accepted artifact · No trading</span>
          </div>
          <div class="qlib-ops-actions">
            <a-date-picker v-model="qlibOpsForm.asof" size="small" style="width: 150px" />
            <a-button size="small" @click="loadQlibOpsLatest" :loading="loadingQlibOps">
              <a-icon type="reload" /> 更新 ops
            </a-button>
            <a-button v-if="qlibOpsCanTrigger" type="primary" size="small" @click="triggerQlibOpsDryRun" :loading="runningQlibOpsDryRun">
              <a-icon type="play-circle" /> 運行 dry-run
            </a-button>
            <a-tag v-else color="orange">Admin ops required</a-tag>
          </div>
        </div>
        <div class="qlib-ops-tags">
          <a-tag :color="qlibOpsStatusColor">{{ qlibOpsJob && qlibOpsJob.status ? qlibOpsJob.status : 'no-job' }}</a-tag>
          <a-tag color="blue">Dry-run only</a-tag>
          <a-tag color="purple">Research ops</a-tag>
          <a-tag color="green">No latest update</a-tag>
          <a-tag color="green">No accepted artifact</a-tag>
          <a-tag color="green">No trading</a-tag>
          <a-tag :color="qlibSchedulerStatusColor">Scheduler {{ qlibSchedulerEnabledText }}</a-tag>
          <a-tag color="blue">Manual tick dry-run only</a-tag>
        </div>
        <div class="qlib-ops-grid">
          <span>scheduler <strong>{{ qlibSchedulerEnabledText }}</strong></span>
          <span>mode <strong>{{ qlibScheduler.mode || '-' }}</strong></span>
          <span>next_run <strong>{{ qlibScheduler.next_run_at || '-' }}</strong></span>
          <span>auto_loop_started <strong>{{ String(qlibScheduler.auto_loop_started === true) }}</strong></span>
        </div>
        <div v-if="qlibOpsJob" class="qlib-ops-grid">
          <span>job_id <strong>{{ qlibOpsJob.job_id || '-' }}</strong></span>
          <span>asof <strong>{{ qlibOpsJob.asof || '-' }}</strong></span>
          <span>started <strong>{{ qlibOpsJob.started_at || '-' }}</strong></span>
          <span>finished <strong>{{ qlibOpsJob.finished_at || '-' }}</strong></span>
          <span>returncode <strong>{{ qlibOpsJob.returncode == null ? '-' : qlibOpsJob.returncode }}</strong></span>
          <span>parsed <strong>{{ qlibOpsJob.parsed_dry_run_status || '-' }}</strong></span>
          <span>{{ qlibOpsLatestChangedText }}</span>
          <span>{{ qlibOpsNormalRunText }}</span>
          <span>{{ qlibOpsArtifactText }}</span>
          <span>{{ qlibOpsNoTradingText }}</span>
        </div>
        <div v-else class="qlib-ops-empty">尚無 Option C ops dry-run job</div>
        <div v-if="qlibOpsJob" class="qlib-ops-log">
          <div class="qlib-ops-log-toolbar">
            <a-radio-group v-model="qlibOpsLogStream" size="small" @change="event => loadQlibOpsLog(event.target.value)">
              <a-radio-button value="stdout">stdout</a-radio-button>
              <a-radio-button value="stderr">stderr</a-radio-button>
            </a-radio-group>
            <a-button size="small" @click="loadQlibOpsLog(qlibOpsLogStream)" :loading="loadingQlibOpsLog">
              <a-icon type="file-search" /> 更新 log tail
            </a-button>
          </div>
          <pre class="qlib-ops-log-tail">{{ qlibOpsLogTail || 'empty log tail' }}</pre>
        </div>
        <a-alert
          v-if="qlibOpsError"
          class="qlib-state-alert"
          type="warning"
          show-icon
          :message="qlibOpsError"
        />
      </div>
      <a-alert
        v-if="qlibStateNotice"
        class="qlib-state-alert"
        :type="qlibSignalsAccepted ? 'info' : 'warning'"
        show-icon
        :message="qlibStateNotice"
      />
      <div v-if="qlibSignalsAccepted" class="qlib-meta-grid">
        <span>asof <strong>{{ qlibPayload.asof || '-' }}</strong></span>
        <span>run_id <strong>{{ qlibPayload.run_id || '-' }}</strong></span>
        <span>recorder_id <strong>{{ qlibPayload.recorder_id || '-' }}</strong></span>
        <span>rows <strong>{{ qlibSignals.length }}</strong></span>
      </div>
      <div v-if="qlibWarnings.length" class="qlib-warning-list">
        <a-tag v-for="warning in qlibWarnings" :key="warning" color="orange">{{ warning }}</a-tag>
      </div>
      <a-table
        v-if="qlibSignalsAccepted"
        row-key="rank"
        size="small"
        class="qlib-signal-table"
        :loading="loadingQlibSignals"
        :columns="qlibColumns"
        :data-source="qlibSignals"
        :pagination="{ pageSize: 10 }"
        :custom-row="qlibCustomRow"
      >
        <template slot="symbol" slot-scope="text, row">
          <strong>{{ row.symbol }}</strong>
          <span class="muted">{{ row.instrument }}</span>
        </template>
        <template slot="qlib_score" slot-scope="score">
          <span>{{ formatNumber(score, 6) }}</span>
        </template>
        <template slot="trend_label" slot-scope="text, row">
          <a-tag :color="qlibTrendAvailable(row) ? 'blue' : 'default'">{{ qlibTrendAvailable(row) ? row.trend.trend_label : 'trend unavailable' }}</a-tag>
        </template>
        <template slot="trend_score" slot-scope="text, row">
          <span>{{ qlibTrendAvailable(row) ? formatNumber(row.trend.trend_score, 2) : '-' }}</span>
        </template>
        <template slot="latest" slot-scope="text, row">
          <span>{{ qlibTrendAvailable(row) ? formatNumber(row.trend.latest_close, 2) : '-' }}</span>
          <span class="muted">{{ row.trend && row.trend.latest_date ? row.trend.latest_date : '-' }}</span>
        </template>
        <template slot="action" slot-scope="text, row">
          <div class="qlib-row-actions">
            <a-button size="small" @click.stop="addQlibWatchDraft(row)">
              <a-icon type="eye" /> 加入觀察
            </a-button>
            <a-button size="small" @click.stop="openQlibReadonlyBacktest(row)">
              <a-icon type="area-chart" /> 回測驗證
            </a-button>
          </div>
        </template>
        <template slot="quality" slot-scope="text, row">
          <a-tag :color="row.diagnostic_only ? 'green' : 'orange'">diagnostic_only={{ String(row.diagnostic_only) }}</a-tag>
          <a-tag :color="row.research_signal_not_order ? 'green' : 'orange'">research_signal_not_order={{ String(row.research_signal_not_order) }}</a-tag>
          <template v-if="row.trend && row.trend.quality_warnings && row.trend.quality_warnings.length">
            <a-tag v-for="warning in row.trend.quality_warnings" :key="`${row.symbol}-${warning}`" color="orange">{{ warning }}</a-tag>
          </template>
        </template>
      </a-table>
      <div v-else-if="!loadingQlibSignals" class="qlib-empty-state">
        {{ qlibEmptyText }}
      </div>
      <div class="qlib-watch-draft">
        <div class="qlib-watch-draft-header">
          <div>
            <strong>研究觀察草稿</strong>
            <span class="muted">觀察草稿僅供人工復盤，不會自動啟用掃描，不會自動建立提醒，不會產生訂單或持倉。</span>
          </div>
          <div class="qlib-watch-draft-actions">
            <a-button size="small" :disabled="!qlibWatchDraft.length" @click="fillMonitorConfigFromQlibDraft">
              <a-icon type="form" /> 填入監控配置
            </a-button>
            <a-button size="small" :disabled="!qlibWatchDraft.length" @click="clearQlibWatchDraft">
              <a-icon type="delete" /> 清空草稿
            </a-button>
          </div>
        </div>
        <div v-if="qlibWatchDraft.length" class="qlib-watch-draft-list">
          <div v-for="item in qlibWatchDraft" :key="item.symbol" class="qlib-watch-draft-item">
            <strong>{{ item.symbol }}</strong>
            <span>run {{ item.run_id || '-' }}</span>
            <span>rank {{ item.rank || '-' }}</span>
            <span>qlib {{ formatNumber(item.qlib_score, 6) }}</span>
            <span>{{ item.trend_label || 'trend unavailable' }}</span>
            <span>trend {{ item.trend_score == null ? '-' : formatNumber(item.trend_score, 2) }}</span>
            <a-button size="small" type="link" @click="removeQlibWatchDraft(item.symbol)">移除</a-button>
          </div>
        </div>
        <div v-else class="qlib-watch-draft-empty">尚未加入觀察草稿</div>
      </div>
      <div class="qlib-footnote">
        qlib_score 是橫截面研究分數，用於候選觀察與人工復盤；不與趨勢分數合成，不產生委託或持倉。
      </div>
    </a-card>



    <a-card class="tw-cross-analysis-card" :bordered="false">
      <template slot="title">
        <div class="card-title-line">
          <span>台股交叉分析</span>
          <div class="readonly-tags">
            <a-tag color="blue">研究排行</a-tag>
            <a-tag color="green">观察名单</a-tag>
            <a-tag color="purple">不是交易建议</a-tag>
          </div>
        </div>
      </template>
      <div class="cross-analysis-toolbar">
        <a-radio-group v-model="crossAnalysisBucket" size="small" @change="handleCrossAnalysisBucketChange">
          <a-radio-button value="top30">Top30</a-radio-button>
          <a-radio-button value="top50">Top50</a-radio-button>
          <a-radio-button value="all">All</a-radio-button>
        </a-radio-group>
        <a-select v-model="crossAnalysisCategory" size="small" style="width: 220px">
          <a-select-option value="all">全部 category</a-select-option>
          <a-select-option v-for="category in crossAnalysisCategories" :key="category" :value="category">{{ category }}</a-select-option>
        </a-select>
        <a-button size="small" @click="loadCrossAnalysis" :loading="loadingCrossAnalysis">
          <a-icon type="reload" /> 更新交叉分析
        </a-button>
      </div>
      <div class="cross-analysis-basis">
        <a-tag color="blue">Yahoo adjusted 模型信号</a-tag>
        <a-tag color="cyan">QuantDinger raw 日线趋势</a-tag>
        <a-tag color="green">orders_enabled=false</a-tag>
        <span>priority 是研究展示排序；qlib score 不是收益率、胜率、涨幅或上涨概率。</span>
      </div>
      <div class="cross-freshness-dashboard">
        <div class="freshness-card">
          <span>freshness status</span>
          <strong>{{ crossFreshness.status || 'unknown' }}</strong>
          <a-tag :color="crossFreshnessStatusColor">{{ crossFreshness.status || 'unknown' }}</a-tag>
        </div>
        <div class="freshness-card">
          <span>qlib asof</span>
          <strong>{{ crossFreshnessQlib.asof || crossAnalysisQlib.asof || '-' }}</strong>
          <small>{{ crossFreshnessQlib.run_id || crossAnalysisQlib.run_id || '-' }}</small>
        </div>
        <div class="freshness-card">
          <span>target_horizon</span>
          <strong>{{ crossFreshnessQlib.target_horizon || crossAnalysisQlib.target_horizon || '-' }}</strong>
          <small>research ranking</small>
        </div>
        <div class="freshness-card">
          <span>raw latest date range</span>
          <strong>{{ crossRawDateRangeText }}</strong>
          <small>{{ crossFreshnessQuant.source || 'raw TWStock daily KlineService data' }}</small>
        </div>
        <div class="freshness-card">
          <span>date gap range</span>
          <strong>{{ crossDateGapRangeText }}</strong>
          <small>qlib asof vs raw latest date</small>
        </div>
      </div>
      <div class="cross-basis-note">
        <span>{{ crossBasisNote }}</span>
        <span>qlib score 来自 Yahoo adjusted 模型信号。QuantDinger 趋势来自 raw 日线。两者可能因复权、除权息、数据源延迟出现差异。该状态只用于研究可见性，不会触发自动补数或交易。</span>
      </div>
      <div v-if="crossFreshnessWarnings.length" class="qlib-warning-list">
        <a-tag v-for="warning in crossFreshnessWarnings" :key="`cross-fresh-${warning}`" color="orange">{{ warning }}</a-tag>
      </div>
      <div class="tw-stock-agent-panel">
        <div class="agent-panel-header">
          <div>
            <strong>台股研究助手</strong>
            <span class="muted">只解释当前 qlib accepted latest、交叉分析与趋势上下文。</span>
          </div>
          <div class="readonly-tags">
            <a-tag color="blue">research-only</a-tag>
            <a-tag :color="agentModeColor">{{ agentModeText }}</a-tag>
            <a-tag v-if="agentBlocked" color="red">blocked</a-tag>
          </div>
        </div>
        <div class="agent-context-grid">
          <span>qlib asof <strong>{{ agentQlibAsof }}</strong></span>
          <span>run_id <strong>{{ agentQlibRunId }}</strong></span>
          <span>freshness <strong>{{ agentFreshnessStatus }}</strong></span>
          <span>items <strong>{{ agentItems.length }}</strong></span>
        </div>
        <div class="agent-suggestions">
          <a-button
            v-for="question in agentSuggestedQuestions"
            :key="question"
            size="small"
            @click="useAgentSuggestion(question)"
            :disabled="sendingAgentQuestion"
          >{{ question }}</a-button>
        </div>
        <div class="agent-input-row">
          <a-textarea
            v-model="agentQuestion"
            :rows="2"
            :max-length="500"
            placeholder="输入台股研究问题，例如：今天 top30 是哪些？"
            @pressEnter="handleAgentEnter"
          />
          <a-button type="primary" :loading="sendingAgentQuestion" @click="askTwStockAgent()">
            <a-icon type="message" /> 发送
          </a-button>
        </div>
        <a-alert
          v-if="agentError"
          class="agent-state-alert"
          type="warning"
          show-icon
          :message="agentError"
        />
        <a-alert
          v-if="agentDisabled"
          class="agent-state-alert"
          type="info"
          show-icon
          message="当前使用后端 deterministic fallback / 未启用 OpenAI。"
        />
        <a-alert
          v-if="agentBlocked"
          class="agent-state-alert"
          type="warning"
          show-icon
          message="该问题已被研究边界阻断；本面板只展示研究解释。"
        />
        <div v-if="agentAnswer" class="agent-answer-box">
          <strong>回答</strong>
          <p>{{ agentAnswer }}</p>
        </div>
        <div class="agent-disclaimer">{{ agentResearchDisclaimer }}</div>
        <div v-if="agentCitations.length" class="agent-citations">
          <strong>引用来源</strong>
          <a-tag v-for="citation in agentCitations" :key="citation" color="blue">{{ citation }}</a-tag>
        </div>
        <div v-if="agentWarnings.length" class="agent-warning-list">
          <strong>warnings</strong>
          <a-tag v-for="warning in agentWarnings" :key="warning" color="orange">{{ warning }}</a-tag>
        </div>
        <div v-if="agentItems.length" class="agent-item-list">
          <div v-for="item in agentItems" :key="`${item.symbol}-${item.qlib_rank || item.cross_category || 'agent'}`" class="agent-item">
            <strong>{{ item.symbol }}</strong>
            <span>rank {{ item.qlib_rank == null ? '-' : item.qlib_rank }}</span>
            <span>qlib score {{ item.qlib_score == null ? '-' : formatNumber(item.qlib_score, 6) }}</span>
            <span>trend {{ item.trend_label || '-' }}</span>
            <span>category {{ item.cross_category || '-' }}</span>
            <span>{{ item.human_action || '人工复盘' }}</span>
            <template v-if="item.quality_warnings && item.quality_warnings.length">
              <a-tag v-for="warning in item.quality_warnings" :key="`${item.symbol}-${warning}`" color="orange">{{ warning }}</a-tag>
            </template>
          </div>
        </div>
        <div v-else-if="agentResponse" class="agent-empty-state">本次回答没有附带项目列表。</div>
      </div>
      <div v-if="crossAnalysisAccepted" class="qlib-meta-grid">
        <span>asof <strong>{{ crossAnalysisQlib.asof || '-' }}</strong></span>
        <span>run_id <strong>{{ crossAnalysisQlib.run_id || '-' }}</strong></span>
        <span>target_horizon <strong>{{ crossAnalysisQlib.target_horizon || '-' }}</strong></span>
        <span>items <strong>{{ filteredCrossAnalysisItems.length }}</strong></span>
      </div>
      <a-alert
        v-if="crossAnalysisStateNotice"
        class="qlib-state-alert"
        :type="crossAnalysisAccepted ? 'info' : 'warning'"
        show-icon
        :message="crossAnalysisStateNotice"
      />
      <a-table
        v-if="crossAnalysisAccepted"
        row-key="symbol"
        size="small"
        class="cross-analysis-table"
        :loading="loadingCrossAnalysis"
        :columns="crossAnalysisColumns"
        :data-source="filteredCrossAnalysisItems"
        :pagination="{ pageSize: 10 }"
        :custom-row="crossAnalysisCustomRow"
      >
        <template slot="cross_rank" slot-scope="text, row">
          <strong>#{{ row.qlib && row.qlib.rank }}</strong>
          <span class="muted">{{ row.qlib && row.qlib.bucket }}</span>
        </template>
        <template slot="cross_symbol" slot-scope="text, row">
          <strong>{{ row.symbol }}</strong>
          <span class="muted">{{ row.instrument }}</span>
        </template>
        <template slot="cross_score" slot-scope="text, row">
          <span>{{ formatNumber(row.qlib && row.qlib.score, 6) }}</span>
        </template>
        <template slot="cross_trend" slot-scope="text, row">
          <a-tag :color="crossTrendColor(row)">{{ row.quantdinger && row.quantdinger.trend_label ? row.quantdinger.trend_label : 'trend_unavailable' }}</a-tag>
          <span>{{ row.quantdinger && row.quantdinger.trend_score == null ? '-' : formatNumber(row.quantdinger && row.quantdinger.trend_score, 2) }}</span>
        </template>
        <template slot="cross_category" slot-scope="text, row">
          <a-tag :color="crossCategoryColor(row.cross && row.cross.category)">{{ row.cross && row.cross.category }}</a-tag>
        </template>
        <template slot="cross_alignment" slot-scope="text, row">
          <a-tag :color="crossAlignmentColor(row.cross && row.cross.alignment)">{{ row.cross && row.cross.alignment }}</a-tag>
        </template>
        <template slot="cross_action" slot-scope="text, row">
          <span>{{ row.cross && row.cross.human_action }}</span>
        </template>
        <template slot="cross_basis" slot-scope="text, row">
          <div class="cross-basis-cell">
            <a-tag :color="crossBasisColor(row.data_basis && row.data_basis.data_basis_status)">{{ row.data_basis && row.data_basis.data_basis_status }}</a-tag>
            <span>date gap {{ row.data_basis && row.data_basis.date_gap_days == null ? '-' : row.data_basis.date_gap_days }}</span>
          </div>
        </template>
      </a-table>
      <div v-else-if="!loadingCrossAnalysis" class="qlib-empty-state">{{ crossAnalysisEmptyText }}</div>
      <div v-if="selectedCrossAnalysisDetail" class="cross-detail-panel">
        <div class="cross-detail-header">
          <strong>{{ selectedCrossAnalysisDetail.symbol }}</strong>
          <a-tag color="blue">只读详情</a-tag>
          <a-button size="small" type="link" @click="selectedCrossAnalysisDetail = null">关闭</a-button>
        </div>
        <div v-if="selectedCrossAnalysisDetail.item" class="cross-detail-grid">
          <span>category <strong>{{ selectedCrossAnalysisDetail.item.cross && selectedCrossAnalysisDetail.item.cross.category }}</strong></span>
          <span>human_action <strong>{{ selectedCrossAnalysisDetail.item.cross && selectedCrossAnalysisDetail.item.cross.human_action }}</strong></span>
          <span>qlib rank <strong>{{ selectedCrossAnalysisDetail.item.qlib && selectedCrossAnalysisDetail.item.qlib.rank }}</strong></span>
          <span>trend <strong>{{ selectedCrossAnalysisDetail.item.quantdinger && selectedCrossAnalysisDetail.item.quantdinger.trend_label }}</strong></span>
        </div>
        <div v-else class="cross-detail-grid">
          <span>status <strong>{{ selectedCrossAnalysisDetail.status }}</strong></span>
          <span>trend <strong>{{ selectedCrossAnalysisDetail.trend && selectedCrossAnalysisDetail.trend.trend_label }}</strong></span>
        </div>
        <div v-if="selectedCrossAnalysisDetail.item" class="cross-review-panel">
          <div class="cross-review-header">
            <strong>人工复盘</strong>
            <a-tag color="blue">只读</a-tag>
          </div>
          <div class="cross-review-form">
            <a-select v-model="crossReviewForm.decision_status" size="small" style="width: 160px">
              <a-select-option value="pending">pending</a-select-option>
              <a-select-option value="watching">watching</a-select-option>
              <a-select-option value="reviewed">reviewed</a-select-option>
              <a-select-option value="ignored">ignored</a-select-option>
              <a-select-option value="data_issue">data_issue</a-select-option>
            </a-select>
            <a-input v-model="crossReviewForm.user_note" size="small" placeholder="人工复盘备注" />
            <a-button size="small" type="primary" :loading="savingCrossReview" @click="saveCrossAnalysisReview">保存复盘</a-button>
            <a-button size="small" @click="openCrossAnalysisHistoricalSimulation">历史模拟</a-button>
          </div>
          <div class="cross-review-note">该回测是对选定股票的技术模板历史模拟，不代表 qlib 策略历史收益。</div>
          <a-alert v-if="crossReviewError" class="cross-review-alert" type="warning" :message="crossReviewError" show-icon />
          <a-alert v-if="crossReviewNotice" class="cross-review-alert" type="info" :message="crossReviewNotice" show-icon />
        </div>
      </div>
      <div class="qlib-footnote">
        数据口径差异：qlib 使用 Yahoo adjusted 模型信号；QuantDinger 使用 raw 日线趋势。交叉分析只用于人工复盘和观察名单，不调用 qlib ops；复盘仅保存状态和备注，历史模拟不会自动运行。
      </div>
    </a-card>

    <a-row :gutter="16" class="content-row">
      <a-col :xs="24" :xl="15">
        <a-card :bordered="false">
          <template slot="title">
            <div class="card-title-line">
              <span>日線 K 線 / 走勢</span>
              <a-tag color="blue">TWStock 1D</a-tag>
            </div>
          </template>
          <div class="chart-toolbar">
            <a-select v-model="chartSymbol" size="small" style="width: 140px" @change="handleChartSymbolChange">
              <a-select-option v-for="symbol in chartSymbols" :key="symbol" :value="symbol">{{ symbol }}</a-select-option>
            </a-select>
            <a-radio-group v-model="priceChartMode" size="small" @change="drawPriceChart">
              <a-radio-button value="candles">K 線</a-radio-button>
              <a-radio-button value="line">收盤線</a-radio-button>
            </a-radio-group>
            <a-radio-group v-model="chartRangeBars" size="small" @change="handleChartRangeChange">
              <a-radio-button :value="30">30D</a-radio-button>
              <a-radio-button :value="60">60D</a-radio-button>
              <a-radio-button :value="120">120D</a-radio-button>
              <a-radio-button value="all">All</a-radio-button>
            </a-radio-group>
            <a-checkbox v-model="showMovingAverages" @change="drawPriceChart">MA</a-checkbox>
            <a-checkbox v-model="showVolume" @change="drawPriceChart">量能</a-checkbox>
            <a-button size="small" @click="openBacktestPanel">
              <a-icon type="area-chart" /> 回測驗證
            </a-button>
            <a-button size="small" @click="refreshSelectedChart" :loading="loadingHistory || loadingKline">
              <a-icon type="reload" /> 更新圖表
            </a-button>
          </div>
          <div class="selected-symbol-panel" v-if="selectedTrendItem">
            <div class="selected-symbol-main">
              <strong>{{ selectedTrendItem.symbol }}</strong>
              <a-tag :color="trendTagColor(selectedTrendItem)">{{ selectedTrendItem.trend && selectedTrendItem.trend.label }}</a-tag>
              <span>Score {{ selectedTrendItem.trend && selectedTrendItem.trend.score }}</span>
            </div>
            <div class="selected-symbol-stats">
              <span>5D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_5d) }}</span>
              <span>20D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_20d) }}</span>
              <span>60D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_60d) }}</span>
              <span>Vol {{ formatPercent(selectedTrendItem.risk && selectedTrendItem.risk.volatility_20d_annualized) }}</span>
              <span>量比 {{ formatNumber(selectedTrendItem.volume && selectedTrendItem.volume.ratio_to_avg20, 2) }}</span>
              <span>{{ priceDataStatusText }}</span>
              <span>{{ chartWindowText }}</span>
            </div>
          </div>
          <a-alert
            v-if="priceDataStale"
            class="chart-data-alert"
            type="warning"
            show-icon
            message="日線資料可能過舊，請刷新或檢查行情接口後再人工判讀。"
          />
          <div class="chart-frame">
            <canvas
              ref="priceChart"
              class="tw-chart-canvas"
              width="900"
              height="420"
              @mousemove="event => handleChartMouseMove('price', event)"
              @mouseleave="clearChartHover('price')"
            ></canvas>
            <div v-if="chartHover.price" class="chart-tooltip" :style="chartTooltipStyle(chartHover.price)">
              <strong>{{ chartHover.price.point.date || chartSymbol }}</strong>
              <span>O {{ formatNumber(chartHover.price.point.open, 2) }}</span>
              <span>H {{ formatNumber(chartHover.price.point.high, 2) }}</span>
              <span>L {{ formatNumber(chartHover.price.point.low, 2) }}</span>
              <span>C {{ formatNumber(chartHover.price.point.close, 2) }}</span>
              <span>V {{ formatCompactNumber(chartHover.price.point.volume) }}</span>
            </div>
            <div v-if="!priceCandles.length && !loadingKline" class="chart-empty">{{ chartEmptyText }}</div>
          </div>
          <div class="ma-legend" v-if="showMovingAverages && priceCandles.length">
            <span><i class="ma-dot ma5"></i>MA5</span>
            <span><i class="ma-dot ma20"></i>MA20</span>
            <span><i class="ma-dot ma60"></i>MA60</span>
          </div>
          <div class="chart-footnote">
            日線 K 線來自只讀行情接口；非盤中即時行情，僅供人工復盤，不產生任何委託。
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :xl="9">
        <a-card :bordered="false">
          <template slot="title">
            <div class="card-title-line">
              <span>趨勢分數歷史</span>
              <a-tag color="purple">Manual Review</a-tag>
            </div>
          </template>
          <div class="chart-frame compact">
            <canvas
              ref="scoreChart"
              class="tw-chart-canvas"
              width="520"
              height="300"
              @mousemove="event => handleChartMouseMove('score', event)"
              @mouseleave="clearChartHover('score')"
            ></canvas>
            <div v-if="chartHover.score" class="chart-tooltip" :style="chartTooltipStyle(chartHover.score)">
              <strong>{{ chartHover.score.point.date || chartSymbol }}</strong>
              <span>Score {{ formatNumber(chartHover.score.point.close, 1) }}</span>
            </div>
            <div v-if="!historyItems.length && !loadingHistory" class="chart-empty">尚無掃描歷史</div>
          </div>
          <div class="history-meta">
            <span>{{ historyItems.length }} points</span>
            <span>{{ chartMetaText }}</span>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16" class="content-row">
      <a-col :xs="24" :xl="15">
        <a-card title="趨勢列表" :bordered="false">
          <a-table
            row-key="symbol"
            size="middle"
            :loading="loadingTrends"
            :columns="trendColumns"
            :data-source="trendItems"
            :pagination="false"
            :row-class-name="trendRowClassName"
            :custom-row="trendCustomRow"
          >
            <template slot="symbol" slot-scope="text, row">
              <strong>{{ row.symbol }}</strong>
              <span class="muted">{{ row.exchange }}</span>
            </template>
            <template slot="score" slot-scope="score">
              <a-progress :percent="Number(score || 0)" size="small" :status="score >= 65 ? 'success' : 'normal'" />
            </template>
            <template slot="quality" slot-scope="quality">
              <template v-if="quality && quality.warnings && quality.warnings.length">
                <a-tag v-for="warning in quality.warnings" :key="warning" color="orange">{{ warning }}</a-tag>
              </template>
              <a-tag v-else color="green">ok</a-tag>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :xl="9">
        <a-card title="掃描健康度" :bordered="false">
          <div class="health-panel">
            <div class="health-status" :class="healthClass">{{ scanHealth.status || 'unknown' }}</div>
            <div class="health-list">
              <span>Success: {{ scanHealth.success_count || 0 }}</span>
              <span>Failed: {{ scanHealth.failed_count || 0 }}</span>
              <span>Scanned: {{ scanHealth.total_scanned_count || 0 }}</span>
              <span>Alerts: {{ scanHealth.total_alert_count || 0 }}</span>
            </div>
            <a-alert
              v-if="scanHealth.recent_failures && scanHealth.recent_failures.length"
              type="warning"
              show-icon
              :message="scanHealth.recent_failures[0].error || 'recent failure'"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="提醒與人工復盤" :bordered="false" class="alerts-card">
      <div class="alert-toolbar">
        <a-radio-group v-model="alertFilter" size="small" @change="loadAlerts">
          <a-radio-button value="all">全部</a-radio-button>
          <a-radio-button value="unread">未讀</a-radio-button>
        </a-radio-group>
      </div>
      <a-table
        row-key="id"
        size="middle"
        :loading="loadingAlerts"
        :columns="alertColumns"
        :data-source="alertItems"
        :pagination="{ pageSize: 8 }"
      >
        <template slot="category" slot-scope="text, row">
          <a-tag :color="alertCategoryColor(row)">{{ alertCategory(row) }}</a-tag>
        </template>
        <template slot="decision_status" slot-scope="text, row">
          <a-select :value="row.decision_status || 'pending'" size="small" style="width: 116px" @change="status => updateAlertStatus(row, status)">
            <a-select-option value="pending">pending</a-select-option>
            <a-select-option value="watch">watch</a-select-option>
            <a-select-option value="ignored">ignored</a-select-option>
            <a-select-option value="acted">acted</a-select-option>
          </a-select>
        </template>
      </a-table>
    </a-card>

    <a-drawer title="監控配置" :visible="configDrawerVisible" width="420" @close="configDrawerVisible = false">
      <a-form layout="vertical">
        <a-form-item label="Name">
          <a-input v-model="configForm.name" />
        </a-form-item>
        <a-form-item label="Symbols">
          <a-textarea v-model="configForm.symbolsText" :rows="4" />
        </a-form-item>
        <a-form-item label="Limit bars">
          <a-input-number v-model="configForm.limit_bars" :min="20" :max="500" style="width: 100%" />
        </a-form-item>
        <a-form-item label="Refresh interval sec">
          <a-input-number v-model="configForm.refresh_interval_sec" :min="0" :max="86400" style="width: 100%" />
        </a-form-item>
        <a-form-item label="Score change threshold">
          <a-input-number v-model="configForm.score_change_threshold" :min="0" :max="100" style="width: 100%" />
        </a-form-item>
        <a-form-item label="Enabled">
          <a-switch v-model="configForm.enabled" />
        </a-form-item>
        <a-form-item label="Notes">
          <a-textarea v-model="configForm.notes" :rows="3" />
        </a-form-item>
      </a-form>
      <div class="drawer-actions">
        <a-button @click="configDrawerVisible = false">取消</a-button>
        <a-button type="primary" @click="saveConfig" :loading="savingConfig">保存</a-button>
      </div>
    </a-drawer>
  </div>
</template>

<script>
import moment from 'moment'
import {
  getTwStockTrends,
  getTwStockMonitorConfig,
  saveTwStockMonitorConfig,
  getTwStockAlerts,
  updateTwStockAlert,
  scanTwStockMonitor,
  getTwStockScanLogs,
  getTwStockHistory,
  getTwStockKline,
  getTwStockBacktestTemplates,
  runTwStockReadonlyBacktest,
  getLatestQlibOptionCSignals,
  getQlibOptionCHealth,
  getQlibOptionCRuns,
  getQlibOptionCRunDetail,
  triggerQlibOptionCDryRun,
  getQlibOptionCJob,
  getQlibOptionCJobLog,
  getQlibOptionCLatestJob,
  getQlibOptionCScheduler,
  getTwStockCrossAnalysisLatest,
  getTwStockCrossAnalysisSymbol,
  getTwStockCrossAnalysisReviews,
  saveTwStockCrossAnalysisReview,
  getTwStockAgentContext,
  chatTwStockAgent
} from '@/api/tw-stock'

export default {
  name: 'TWStockMonitor',
  data () {
    return {
      loading: false,
      loadingTrends: false,
      loadingAlerts: false,
      loadingHistory: false,
      loadingKline: false,
      loadingBacktestTemplates: false,
      loadingQlibSignals: false,
      loadingQlibHealth: false,
      loadingQlibRuns: false,
      loadingQlibOps: false,
      runningQlibOpsDryRun: false,
      loadingQlibOpsLog: false,
      loadingCrossAnalysis: false,
      loadingCrossAnalysisDetail: false,
      loadingAgentContext: false,
      sendingAgentQuestion: false,
      savingCrossReview: false,
      runningBacktest: false,
      scanning: false,
      savingConfig: false,
      alertFilter: 'all',
      autoRefreshEnabled: true,
      autoRefreshTimer: null,
      lastRefreshedAt: '',
      chartSymbol: '',
      priceChartMode: 'candles',
      chartRangeBars: 120,
      showMovingAverages: true,
      showVolume: true,
      historyItems: [],
      priceCandles: [],
      chartHover: {
        price: null,
        score: null
      },
      chartLayouts: {
        price: null,
        score: null,
        backtest: null
      },
      backtestPanelVisible: false,
      backtestTemplates: [],
      backtestForm: {
        strategyId: 'ma_cross_builtin',
        startDate: null,
        endDate: null,
        initialCapital: 1000000
      },
      backtestResult: null,
      backtestError: '',
      qlibBucket: 'top30',
      qlibPayload: null,
      qlibHealth: null,
      qlibHealthError: '',
      qlibError: '',
      qlibRuns: [],
      qlibRunStatusFilter: 'all',
      selectedQlibRunId: '',
      qlibOpsJob: null,
      qlibScheduler: {},
      qlibOpsLogStream: 'stdout',
      qlibOpsLogTail: '',
      qlibOpsError: '',
      qlibOpsForm: {
        asof: '2026-06-01'
      },
      qlibWatchDraft: [],
      crossAnalysisBucket: 'top30',
      crossAnalysisCategory: 'all',
      crossAnalysisPayload: null,
      crossAnalysisError: '',
      selectedCrossAnalysisDetail: null,
      crossReviewForm: {
        decision_status: 'pending',
        user_note: ''
      },
      crossReviewError: '',
      crossReviewNotice: '',
      agentContext: null,
      agentContextError: '',
      agentQuestion: '',
      agentResponse: null,
      agentError: '',
      agentSuggestedQuestions: [
        '今天 top30 是哪些？',
        '今天模型和趋势都支持的股票有哪些？',
        '今天建议回避或人工复盘的股票有哪些？',
        '2330 的指标是多少？',
        '当前数据新鲜度和口径是什么？'
      ],
      configDrawerVisible: false,
      config: {
        name: 'default',
        symbols: [],
        limit_bars: 120,
        refresh_interval_sec: 900,
        score_change_threshold: 8,
        enabled: false,
        notes: ''
      },
      configForm: {},
      trendItems: [],
      alertItems: [],
      scanHealth: {},
      degradedNotice: '',
      trendColumns: [
        { title: 'Symbol', dataIndex: 'symbol', scopedSlots: { customRender: 'symbol' } },
        { title: 'Label', dataIndex: 'trend.label' },
        { title: 'Score', dataIndex: 'trend.score', scopedSlots: { customRender: 'score' } },
        { title: 'Latest', dataIndex: 'latest.date' },
        { title: 'Close', dataIndex: 'latest.close' },
        { title: '20D', dataIndex: 'returns.ret_20d', customRender: value => this.formatPercent(value) },
        { title: '60D', dataIndex: 'returns.ret_60d', customRender: value => this.formatPercent(value) },
        { title: 'Vol Ratio', dataIndex: 'volume.ratio_to_avg20', customRender: value => this.formatNumber(value, 2) },
        { title: 'Bars', dataIndex: 'quality.bar_count' },
        { title: 'Quality', dataIndex: 'quality', scopedSlots: { customRender: 'quality' } }
      ],
      alertColumns: [
        { title: 'Symbol', dataIndex: 'symbol', width: 90 },
        { title: 'Category', dataIndex: 'category', scopedSlots: { customRender: 'category' }, width: 130 },
        { title: 'Severity', dataIndex: 'severity', width: 100 },
        { title: 'Message', dataIndex: 'message' },
        { title: 'Status', dataIndex: 'decision_status', scopedSlots: { customRender: 'decision_status' }, width: 150 }
      ],
      qlibRunColumns: [
        { title: 'status', dataIndex: 'status', scopedSlots: { customRender: 'status' }, width: 170 },
        { title: 'asof', dataIndex: 'asof', width: 110 },
        { title: 'run_id', dataIndex: 'run_id', scopedSlots: { customRender: 'run_id' } },
        { title: 'created_at', dataIndex: 'created_at', width: 190 },
        { title: 'prediction/top30/top50', dataIndex: 'rows', scopedSlots: { customRender: 'rows' }, width: 170 },
        { title: 'warnings', dataIndex: 'warnings', scopedSlots: { customRender: 'warnings' }, width: 260 }
      ],
      qlibColumns: [
        { title: 'Rank', dataIndex: 'rank', width: 80 },
        { title: 'Symbol', dataIndex: 'symbol', scopedSlots: { customRender: 'symbol' }, width: 150 },
        { title: 'qlib_score', dataIndex: 'qlib_score', scopedSlots: { customRender: 'qlib_score' }, width: 140 },
        { title: 'trend_label', dataIndex: 'trend.trend_label', scopedSlots: { customRender: 'trend_label' }, width: 130 },
        { title: 'trend_score', dataIndex: 'trend.trend_score', scopedSlots: { customRender: 'trend_score' }, width: 120 },
        { title: 'latest_close / latest_date', dataIndex: 'trend.latest_close', scopedSlots: { customRender: 'latest' }, width: 170 },
        { title: '研究动作', dataIndex: 'action', scopedSlots: { customRender: 'action' }, width: 220 },
        { title: 'quality_warnings', dataIndex: 'quality', scopedSlots: { customRender: 'quality' } }
      ],
      crossAnalysisColumns: [
        { title: '研究排行', dataIndex: 'qlib.rank', scopedSlots: { customRender: 'cross_rank' }, width: 100 },
        { title: 'Symbol', dataIndex: 'symbol', scopedSlots: { customRender: 'cross_symbol' }, width: 140 },
        { title: 'qlib score', dataIndex: 'qlib.score', scopedSlots: { customRender: 'cross_score' }, width: 120 },
        { title: 'raw trend', dataIndex: 'quantdinger.trend_label', scopedSlots: { customRender: 'cross_trend' }, width: 150 },
        { title: 'latest date', dataIndex: 'quantdinger.latest_date', width: 120 },
        { title: 'category', dataIndex: 'cross.category', scopedSlots: { customRender: 'cross_category' }, width: 190 },
        { title: 'alignment', dataIndex: 'cross.alignment', scopedSlots: { customRender: 'cross_alignment' }, width: 110 },
        { title: 'human_action', dataIndex: 'cross.human_action', scopedSlots: { customRender: 'cross_action' } },
        { title: 'data_basis', dataIndex: 'data_basis.data_basis_status', scopedSlots: { customRender: 'cross_basis' }, width: 220 }
      ],
      backtestTradeColumns: [
        { title: 'Time', dataIndex: 'time', width: 150 },
        { title: 'Type', dataIndex: 'type', width: 120 },
        { title: 'Price', dataIndex: 'price', customRender: value => this.formatNumber(value, 2) },
        { title: 'Amount', dataIndex: 'amount', customRender: value => this.formatNumber(value, 2) },
        { title: 'Profit', dataIndex: 'profit', customRender: value => this.formatNumber(value, 2) },
        { title: 'Balance', dataIndex: 'balance', customRender: value => this.formatNumber(value, 2) }
      ]
    }
  },
  computed: {
    unreadCount () {
      return this.alertItems.filter(item => !item.is_read).length
    },
    healthClass () {
      return `health-${this.scanHealth.status || 'unknown'}`
    },
    chartSymbols () {
      const symbols = this.trendItems.filter(item => item && item.ok !== false).map(item => item.symbol).filter(Boolean)
      return symbols.length ? symbols : (this.config.symbols || [])
    },
    selectedTrendItem () {
      return this.trendItems.find(item => item.symbol === this.chartSymbol) || this.trendItems.find(item => item && item.ok !== false) || this.trendItems[0] || null
    },
    refreshIntervalMs () {
      const seconds = Number(this.config.refresh_interval_sec || 0)
      return seconds > 0 ? seconds * 1000 : 0
    },
    refreshStatusText () {
      if (!this.refreshIntervalMs) return '自動刷新關閉'
      const minutes = Math.max(1, Math.round(this.refreshIntervalMs / 60000))
      const suffix = this.lastRefreshedAt ? ` · ${this.lastRefreshedAt}` : ''
      return `${this.autoRefreshEnabled ? '自動刷新' : '暫停'} ${minutes}m${suffix}`
    },
    chartMetaText () {
      const latest = this.selectedTrendItem && this.selectedTrendItem.latest
      if (!latest) return '-'
      return `${latest.date || '-'} close ${latest.close == null ? '-' : latest.close}`
    },
    displayedPriceCandles () {
      return this.sliceByChartRange(this.priceCandles)
    },
    displayedHistoryItems () {
      return this.sliceByChartRange(this.historyItems)
    },
    latestPriceBar () {
      return this.priceCandles.length ? this.priceCandles[this.priceCandles.length - 1] : null
    },
    priceDataAgeDays () {
      if (!this.latestPriceBar || !this.latestPriceBar.date) return null
      const parsed = new Date(`${this.latestPriceBar.date}T00:00:00Z`)
      if (Number.isNaN(parsed.getTime())) return null
      return Math.floor((Date.now() - parsed.getTime()) / 86400000)
    },
    priceDataStale () {
      return this.priceDataAgeDays != null && this.priceDataAgeDays > 10
    },
    priceDataStatusText () {
      if (!this.latestPriceBar) return '日線 -'
      const age = this.priceDataAgeDays == null ? '-' : `${this.priceDataAgeDays}d`
      return `日線 ${this.latestPriceBar.date || '-'} · ${this.displayedPriceCandles.length}/${this.priceCandles.length} bars · ${age}`
    },
    chartEmptyText () {
      const item = this.selectedTrendItem || {}
      const quality = item.quality || {}
      const warnings = Array.isArray(quality.warnings) ? quality.warnings.join(', ') : ''
      if (item.ok === false) return `${item.symbol || this.chartSymbol} 暫無日線資料${item.error ? `：${item.error}` : ''}`
      return warnings ? `等待日線資料：${warnings}` : '等待日線資料'
    },
    chartWindowText () {
      const points = this.displayedPriceCandles
      if (points.length < 2) return '窗口 -'
      const first = points[0]
      const last = points[points.length - 1]
      const closes = points.map(item => Number(item.close)).filter(Number.isFinite)
      const highs = points.map(item => Number(item.high)).filter(Number.isFinite)
      const lows = points.map(item => Number(item.low)).filter(Number.isFinite)
      const ret = first.close ? (last.close - first.close) / first.close : null
      const high = highs.length ? Math.max(...highs) : null
      const low = lows.length ? Math.min(...lows) : null
      return `窗口 ${points.length}D · ${this.formatPercent(ret)} · H ${this.formatNumber(high, 2)} / L ${this.formatNumber(low, 2)}`
    },
    backtestMetrics () {
      return (this.backtestResult && (this.backtestResult.metrics || this.backtestResult)) || {}
    },
    backtestAssumptions () {
      return (this.backtestResult && this.backtestResult.executionAssumptions) || {}
    },
    backtestDataQuality () {
      return (this.backtestResult && this.backtestResult.dataQuality) || {}
    },
    backtestQualityWarnings () {
      const warnings = this.backtestDataQuality && this.backtestDataQuality.warnings
      return Array.isArray(warnings) ? warnings : []
    },
    backtestEquityCurve () {
      const curve = this.backtestResult && this.backtestResult.equityCurve
      return Array.isArray(curve) ? curve : []
    },
    backtestTrades () {
      const trades = this.backtestResult && this.backtestResult.trades
      return Array.isArray(trades) ? trades.map((item, index) => Object.assign({ _key: `${item.time || 'trade'}-${index}` }, item)) : []
    },
    qlibHealthLatest () {
      return (this.qlibHealth && this.qlibHealth.latest) || {}
    },
    qlibHealthFreshness () {
      return (this.qlibHealth && this.qlibHealth.freshness) || {}
    },
    qlibHealthRuns () {
      return (this.qlibHealth && this.qlibHealth.runs) || {}
    },
    qlibHealthStatusText () {
      return (this.qlibHealth && this.qlibHealth.status) || 'missing'
    },
    qlibHealthStatusColor () {
      if (!this.qlibHealth || this.qlibHealthMissing) return 'red'
      if (this.qlibHealthFreshness && this.qlibHealthFreshness.stale) return 'orange'
      if (this.qlibHealth.status === 'accepted' && this.qlibHealthLatest.accepted_validated) return 'green'
      if (String(this.qlibHealth.status || '').indexOf('wait_state') === 0) return 'gold'
      return 'default'
    },
    qlibHealthMissing () {
      return !this.qlibHealth || this.qlibHealthLatest.exists === false || this.qlibHealth.status === 'missing_latest_signal'
    },
    qlibHealthWaitStatePresent () {
      return Number(this.qlibHealthRuns.wait_state || 0) > 0
    },
    qlibHealthAgeText () {
      const freshness = this.qlibHealthFreshness || {}
      const asofAge = freshness.asof_age_days == null ? '-' : `${freshness.asof_age_days}d`
      const createdAge = freshness.created_age_hours == null ? '-' : `${freshness.created_age_hours}h`
      return `asof ${asofAge} / created ${createdAge}`
    },
    qlibHealthRunText () {
      const runs = this.qlibHealthRuns || {}
      return `accepted ${runs.accepted || 0} / wait-state ${runs.wait_state || 0} / blocked ${runs.blocked || 0} / other ${runs.other || 0}`
    },
    qlibHealthWarnings () {
      const latestWarnings = this.qlibHealthLatest && Array.isArray(this.qlibHealthLatest.warnings) ? this.qlibHealthLatest.warnings : []
      const data = this.qlibHealth && this.qlibHealth.dataAvailability
      const dataWarnings = data && Array.isArray(data.warnings) ? data.warnings : []
      const freshness = this.qlibHealthFreshness || {}
      const freshnessWarnings = Array.isArray(freshness.warnings) ? freshness.warnings : []
      const staleReason = freshness.stale_reason ? [freshness.stale_reason] : []
      return Array.from(new Set([].concat(latestWarnings, dataWarnings, freshnessWarnings, staleReason).filter(Boolean)))
    },
    qlibOpsStatusColor () {
      const status = this.qlibOpsJob && this.qlibOpsJob.status
      if (status === 'dry_run_passed') return 'green'
      if (status === 'running') return 'blue'
      if (status === 'conflict') return 'gold'
      if (status && status.indexOf('blocked') === 0) return 'red'
      if (status && status.indexOf('failed') >= 0) return 'red'
      return 'default'
    },
    qlibOpsTradingFlags () {
      return (this.qlibOpsJob && this.qlibOpsJob.trading) || {}
    },
    qlibSchedulerEnabledText () {
      return this.qlibScheduler && this.qlibScheduler.enabled === true ? 'enabled' : 'disabled'
    },
    qlibSchedulerStatusColor () {
      return this.qlibScheduler && this.qlibScheduler.enabled === true ? 'gold' : 'default'
    },
    qlibOpsCanTrigger () {
      const user = this.readLocalJson('User-Info') || {}
      const role = user.role && typeof user.role === 'object' ? user.role : { id: user.role }
      const roleId = role.id || user.role || user.role_id || user.roleId
      const permissions = []
        .concat(Array.isArray(user.permissions) ? user.permissions : [])
        .concat(Array.isArray(role.permissions) ? role.permissions : [])
        .concat(Array.isArray(role.permissionList) ? role.permissionList : [])
      return roleId === 'admin' || permissions.includes('tw_stock_qlib_ops') || permissions.includes('tw_stock_ops')
    },
    qlibOpsLatestChangedText () {
      if (!this.qlibOpsJob) return '-'
      return `latest_signal_updated=${String(this.qlibOpsJob.latest_signal_updated === true)}`
    },
    qlibOpsNormalRunText () {
      if (!this.qlibOpsJob) return '-'
      return `normal_signal_run=${String(this.qlibOpsJob.normal_signal_run === true)}`
    },
    qlibOpsArtifactText () {
      if (!this.qlibOpsJob) return '-'
      return `accepted_artifact_generated=${String(this.qlibOpsJob.accepted_artifact_generated === true)}`
    },
    qlibOpsNoTradingText () {
      const flags = this.qlibOpsTradingFlags
      return `orders_enabled=${String(flags.orders_enabled === true)} / connects_to_broker=${String(flags.connects_to_broker === true)} / writes_orders=${String(flags.writes_orders === true)} / writes_positions=${String(flags.writes_positions === true)}`
    },
    qlibSignalsAccepted () {
      return !!(this.qlibPayload && this.qlibPayload.ok && this.qlibPayload.status === 'accepted')
    },
    qlibSignals () {
      if (!this.qlibSignalsAccepted) return []
      const rows = this.qlibPayload && this.qlibPayload.signals
      return Array.isArray(rows) ? rows : []
    },
    qlibWarnings () {
      const warnings = this.qlibPayload && this.qlibPayload.warnings
      return Array.isArray(warnings) ? warnings : []
    },
    qlibStateNotice () {
      if (this.qlibError) return this.qlibError
      if (!this.qlibPayload) return ''
      const source = this.selectedQlibRunId ? `歷史 run ${this.selectedQlibRunId}` : 'latest'
      if (this.qlibSignalsAccepted) return `已載入 ${source} ${this.qlibPayload.bucket || this.qlibBucket} 研究排序；請人工復盤，不作為訂單。`
      return `${this.qlibPayload.status || 'unavailable'}：${this.qlibPayload.message || 'qlib 研究排序目前不可用；blocked/wait-state run 不展示可用 signals。'}`
    },
    qlibEmptyText () {
      if (!this.qlibPayload && !this.qlibError) return '尚未載入 qlib Option C 研究排序'
      return '目前沒有可用 qlib 研究排序表'
    },
    crossAnalysisAccepted () {
      return !!(this.crossAnalysisPayload && this.crossAnalysisPayload.ok && this.crossAnalysisPayload.status === 'accepted')
    },
    crossAnalysisQlib () {
      return (this.crossAnalysisPayload && this.crossAnalysisPayload.qlib) || {}
    },
    crossFreshness () {
      return (this.crossAnalysisPayload && this.crossAnalysisPayload.freshness) || {}
    },
    crossFreshnessQlib () {
      return (this.crossFreshness && this.crossFreshness.qlib) || {}
    },
    crossFreshnessQuant () {
      return (this.crossFreshness && this.crossFreshness.quantdinger) || {}
    },
    crossFreshnessWarnings () {
      const warnings = this.crossFreshness && this.crossFreshness.warnings
      return Array.isArray(warnings) ? warnings : []
    },
    crossFreshnessStatusColor () {
      const status = this.crossFreshness.status
      if (status === 'fresh') return 'green'
      if (status === 'historical') return 'blue'
      if (status === 'stale') return 'orange'
      if (status === 'blocked') return 'red'
      return 'default'
    },
    crossRawDateRangeText () {
      const min = this.crossFreshnessQuant.latest_date_min
      const max = this.crossFreshnessQuant.latest_date_max
      if (!min && !max) return '-'
      return min === max ? min : `${min || '-'} ~ ${max || '-'}`
    },
    crossDateGapRangeText () {
      const min = this.crossFreshness.date_gap_days_min
      const max = this.crossFreshness.date_gap_days_max
      if (min == null && max == null) return '-'
      return min === max ? String(min) : `${min == null ? '-' : min} ~ ${max == null ? '-' : max}`
    },
    crossBasisNote () {
      const basis = (this.crossAnalysisPayload && this.crossAnalysisPayload.basis) || {}
      return basis.note || 'qlib score comes from Yahoo adjusted model signals. QuantDinger trend comes from raw daily bars.'
    },
    crossAnalysisItems () {
      const items = this.crossAnalysisPayload && this.crossAnalysisPayload.items
      return Array.isArray(items) ? items : []
    },
    crossAnalysisCategories () {
      return Array.from(new Set(this.crossAnalysisItems.map(item => item && item.cross && item.cross.category).filter(Boolean)))
    },
    filteredCrossAnalysisItems () {
      if (this.crossAnalysisCategory === 'all') return this.crossAnalysisItems
      return this.crossAnalysisItems.filter(item => item && item.cross && item.cross.category === this.crossAnalysisCategory)
    },
    crossAnalysisStateNotice () {
      if (this.crossAnalysisError) return this.crossAnalysisError
      if (!this.crossAnalysisPayload) return ''
      if (this.crossAnalysisAccepted) return `已載入 ${this.crossAnalysisPayload.bucket || this.crossAnalysisBucket} 台股交叉分析；僅供人工復盤與觀察名單。`
      return `${this.crossAnalysisPayload.status || 'unavailable'}：${this.crossAnalysisPayload.message || '交叉分析目前不可用，請檢查 qlib accepted latest 或 raw 日線資料。'}`
    },
    crossAnalysisEmptyText () {
      if (!this.crossAnalysisPayload && !this.crossAnalysisError) return '尚未載入台股交叉分析'
      return '目前沒有可用交叉分析項目'
    },
    agentResponseDigest () {
      return (this.agentResponse && this.agentResponse.context_digest) || {}
    },
    agentContextQlib () {
      return (this.agentContext && this.agentContext.qlib) || {}
    },
    agentQlibAsof () {
      return this.agentResponseDigest.qlib_asof || this.agentContextQlib.asof || this.crossAnalysisQlib.asof || '-'
    },
    agentQlibRunId () {
      return this.agentResponseDigest.qlib_run_id || this.agentContextQlib.run_id || this.crossAnalysisQlib.run_id || '-'
    },
    agentFreshnessStatus () {
      const contextFreshness = (this.agentContext && this.agentContext.freshness) || {}
      return this.agentResponseDigest.freshness_status || contextFreshness.status || this.crossFreshness.status || 'unknown'
    },
    agentModeText () {
      const mode = this.agentResponse && this.agentResponse.mode
      if (mode === 'disabled') return 'deterministic fallback'
      return mode || 'context ready'
    },
    agentModeColor () {
      const mode = this.agentResponse && this.agentResponse.mode
      if (mode === 'disabled') return 'gold'
      if (mode === 'openai') return 'green'
      if (mode === 'mock') return 'blue'
      return 'default'
    },
    agentDisabled () {
      return !!(this.agentResponse && this.agentResponse.mode === 'disabled')
    },
    agentBlocked () {
      return !!(this.agentResponse && this.agentResponse.blocked)
    },
    agentAnswer () {
      return (this.agentResponse && this.agentResponse.answer) || ''
    },
    agentResearchDisclaimer () {
      return (this.agentResponse && this.agentResponse.research_only_disclaimer) || (this.agentContext && this.agentContext.disclaimers && this.agentContext.disclaimers[0]) || '仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或入场概率。'
    },
    agentCitations () {
      const citations = this.agentResponse && this.agentResponse.citations
      return Array.isArray(citations) ? citations : []
    },
    agentWarnings () {
      const warnings = this.agentResponse && this.agentResponse.warnings
      return Array.isArray(warnings) ? warnings : []
    },
    agentItems () {
      const items = this.agentResponse && this.agentResponse.items
      return Array.isArray(items) ? items : []
    }
  },
  mounted () {
    const routeSymbol = this.$route && this.$route.query && this.$route.query.symbol
    if (routeSymbol) this.chartSymbol = String(routeSymbol).trim().toUpperCase()
    this.initializeBacktestDates()
    this.loadBacktestTemplates()
    this.loadQlibWatchDraft()
    this.loadQlibHealth()
    this.loadQlibSignals()
    this.loadQlibRuns()
    this.loadQlibScheduler()
    this.loadQlibOpsLatest()
    this.loadCrossAnalysis()
    this.loadTwStockAgentContext()
    this.refreshAll()
    window.addEventListener('resize', this.redrawCharts)
  },
  beforeDestroy () {
    this.stopAutoRefresh()
    window.removeEventListener('resize', this.redrawCharts)
  },
  methods: {
    unwrap (response) {
      if (response && response.data && Object.prototype.hasOwnProperty.call(response.data, 'data')) {
        return response.data.data
      }
      if (response && Object.prototype.hasOwnProperty.call(response, 'data')) {
        return response.data
      }
      return response
    },
    readLocalJson (key) {
      try {
        const raw = window.localStorage.getItem(key)
        return raw ? JSON.parse(raw) : null
      } catch (error) {
        return null
      }
    },
    initializeBacktestDates () {
      const end = new Date()
      const start = new Date()
      start.setFullYear(start.getFullYear() - 1)
      this.backtestForm.startDate = this.toDateMoment(start)
      this.backtestForm.endDate = this.toDateMoment(end)
    },
    toDateMoment (date) {
      return moment(date)
    },
    formatPickerDate (value) {
      if (!value) return ''
      if (typeof value.format === 'function') return value.format('YYYY-MM-DD')
      const parsed = value instanceof Date ? value : new Date(value)
      if (Number.isNaN(parsed.getTime())) return ''
      return parsed.toISOString().slice(0, 10)
    },
    async loadQlibHealth () {
      this.loadingQlibHealth = true
      this.qlibHealthError = ''
      try {
        const data = this.unwrap(await getQlibOptionCHealth())
        this.qlibHealth = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.qlibHealth = data || null
        this.qlibHealthError = (response && response.msg) || error.message || 'qlib Option C 数据状态讀取失敗'
      } finally {
        this.loadingQlibHealth = false
      }
    },
    async loadQlibSignals () {
      this.loadingQlibSignals = true
      this.qlibError = ''
      this.qlibPayload = null
      this.selectedQlibRunId = ''
      try {
        const data = this.unwrap(await getLatestQlibOptionCSignals({ bucket: this.qlibBucket, enrichTrend: true, trendLimit: 120 }))
        this.qlibPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.qlibPayload = data || null
        this.qlibError = (response && response.msg) || error.message || 'qlib Option C 研究排序讀取失敗'
      } finally {
        this.loadingQlibSignals = false
      }
    },
    async loadQlibRuns () {
      this.loadingQlibRuns = true
      try {
        const data = this.unwrap(await getQlibOptionCRuns({ limit: 20, status: this.qlibRunStatusFilter }))
        this.qlibRuns = data && Array.isArray(data.items) ? data.items : []
      } catch (error) {
        this.qlibRuns = []
      } finally {
        this.loadingQlibRuns = false
      }
    },
    async loadQlibRunDetail (run) {
      if (!run || !run.run_id) return
      this.loadingQlibSignals = true
      this.qlibError = ''
      try {
        const data = this.unwrap(await getQlibOptionCRunDetail(run.run_id, { bucket: this.qlibBucket, enrichTrend: run.status === 'accepted' && run.accepted_validated === true, trendLimit: 120 }))
        this.selectedQlibRunId = run.run_id
        this.qlibPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.selectedQlibRunId = run.run_id
        this.qlibPayload = data || null
        this.qlibError = (response && response.msg) || error.message || '歷史 qlib run 讀取失敗'
      } finally {
        this.loadingQlibSignals = false
      }
    },
    returnToLatestQlib () {
      this.loadQlibSignals()
    },
    handleQlibBucketChange () {
      if (this.selectedQlibRunId) {
        const run = this.qlibRuns.find(item => item.run_id === this.selectedQlibRunId)
        if (run) return this.loadQlibRunDetail(run)
      }
      this.loadQlibSignals()
    },
    qlibRunStatusColor (run) {
      const status = run && run.status
      if (status === 'accepted' && run.accepted_validated) return 'green'
      if (status && status.indexOf('wait_state') === 0) return 'gold'
      if (status && status.indexOf('blocked') === 0) return 'red'
      return 'default'
    },
    qlibRunCustomRow (record) {
      return {
        on: {
          click: () => this.loadQlibRunDetail(record)
        }
      }
    },
    async loadTwStockAgentContext () {
      this.loadingAgentContext = true
      this.agentContextError = ''
      try {
        const data = this.unwrap(await getTwStockAgentContext({ maxItems: 10 }))
        this.agentContext = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.agentContext = response && response.data ? response.data : null
        this.agentContextError = (response && response.msg) || error.message || '台股研究助手上下文读取失败。'
      } finally {
        this.loadingAgentContext = false
      }
    },
    handleAgentEnter (event) {
      if (event && event.shiftKey) return
      if (event && typeof event.preventDefault === 'function') event.preventDefault()
      this.askTwStockAgent()
    },
    useAgentSuggestion (question) {
      this.agentQuestion = question
      this.askTwStockAgent(question)
    },
    async askTwStockAgent (question) {
      const text = String(question || this.agentQuestion || '').trim().slice(0, 500)
      if (!text) {
        this.agentError = '请输入台股研究问题。'
        return
      }
      this.agentQuestion = text
      this.sendingAgentQuestion = true
      this.agentError = ''
      try {
        const data = this.unwrap(await chatTwStockAgent({
          question: text,
          symbol: this.chartSymbol || '',
          maxItems: 10
        }))
        this.agentResponse = data || null
        if (data && data.context_digest && !this.agentContext) {
          this.agentContext = { qlib: { asof: data.context_digest.qlib_asof, run_id: data.context_digest.qlib_run_id }, freshness: { status: data.context_digest.freshness_status } }
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        this.agentResponse = response && response.data ? response.data : null
        this.agentError = (response && response.msg) || error.message || '台股研究助手回答失败。'
      } finally {
        this.sendingAgentQuestion = false
      }
    },
    async loadCrossAnalysis () {
      this.loadingCrossAnalysis = true
      this.crossAnalysisError = ''
      try {
        const maxItems = this.crossAnalysisBucket === 'top30' ? 30 : 50
        const data = this.unwrap(await getTwStockCrossAnalysisLatest({
          bucket: this.crossAnalysisBucket,
          limit: 120,
          maxItems,
          includeRawTrend: false
        }))
        this.crossAnalysisPayload = data || null
        if (this.crossAnalysisCategory !== 'all' && !this.crossAnalysisCategories.includes(this.crossAnalysisCategory)) {
          this.crossAnalysisCategory = 'all'
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.crossAnalysisPayload = data || null
        this.crossAnalysisError = (response && response.msg) || error.message || '台股交叉分析讀取失敗；僅顯示只讀錯誤狀態。'
      } finally {
        this.loadingCrossAnalysis = false
      }
    },
    handleCrossAnalysisBucketChange () {
      this.crossAnalysisCategory = 'all'
      this.loadCrossAnalysis()
    },
    async loadCrossAnalysisDetail (row) {
      if (!row || !row.symbol) return
      this.loadingCrossAnalysisDetail = true
      try {
        const data = this.unwrap(await getTwStockCrossAnalysisSymbol(row.symbol, { limit: 120, includeRawTrend: true }))
        this.selectedCrossAnalysisDetail = data || null
        this.prepareCrossReviewForm()
      } catch (error) {
        const response = error && error.response && error.response.data
        this.selectedCrossAnalysisDetail = (response && response.data) || { ok: false, status: 'read_error', symbol: row.symbol }
        this.prepareCrossReviewForm()
      } finally {
        this.loadingCrossAnalysisDetail = false
      }
    },
    prepareCrossReviewForm () {
      this.crossReviewError = ''
      this.crossReviewNotice = ''
      this.crossReviewForm = { decision_status: 'pending', user_note: '' }
      this.loadCrossAnalysisReviewState()
    },
    async loadCrossAnalysisReviewState () {
      const detail = this.selectedCrossAnalysisDetail
      const item = detail && detail.item
      const runId = (detail && detail.qlib && detail.qlib.run_id) || (this.crossAnalysisQlib && this.crossAnalysisQlib.run_id)
      const asof = (detail && detail.qlib && detail.qlib.asof) || (this.crossAnalysisQlib && this.crossAnalysisQlib.asof)
      if (!item || !detail.symbol || !runId || !asof) return
      try {
        const data = this.unwrap(await getTwStockCrossAnalysisReviews({ asof, run_id: runId, symbol: detail.symbol, limit: 1 }))
        const review = data && Array.isArray(data.items) && data.items[0]
        if (review) {
          this.crossReviewForm = {
            decision_status: review.decision_status || 'pending',
            user_note: review.user_note || ''
          }
        }
      } catch (error) {
        this.crossReviewError = '复盘状态读取失败；可继续查看只读详情。'
      }
    },
    async saveCrossAnalysisReview () {
      const detail = this.selectedCrossAnalysisDetail
      const item = detail && detail.item
      const runId = (detail && detail.qlib && detail.qlib.run_id) || (this.crossAnalysisQlib && this.crossAnalysisQlib.run_id)
      const asof = (detail && detail.qlib && detail.qlib.asof) || (this.crossAnalysisQlib && this.crossAnalysisQlib.asof)
      if (!item || !detail.symbol || !runId || !asof) return
      this.savingCrossReview = true
      this.crossReviewError = ''
      this.crossReviewNotice = ''
      try {
        const data = this.unwrap(await saveTwStockCrossAnalysisReview({
          asof,
          run_id: runId,
          symbol: detail.symbol,
          cross_category: item.cross && item.cross.category,
          decision_status: this.crossReviewForm.decision_status,
          user_note: this.crossReviewForm.user_note
        }))
        if (data && data.ok === false) throw new Error(data.message || data.status || 'save failed')
        this.crossReviewNotice = '复盘状态已保存，仅记录人工状态和备注。'
      } catch (error) {
        const response = error && error.response && error.response.data
        this.crossReviewError = (response && response.msg) || error.message || '复盘状态保存失败。'
      } finally {
        this.savingCrossReview = false
      }
    },
    async openCrossAnalysisHistoricalSimulation () {
      const detail = this.selectedCrossAnalysisDetail
      const symbol = detail && detail.symbol
      if (!symbol) return
      await this.selectTrendSymbol(symbol)
      this.backtestForm = Object.assign({}, this.backtestForm, {
        strategyId: 'ma_cross_builtin',
        initialCapital: 1000000
      })
      this.backtestPanelVisible = true
      this.backtestResult = null
      this.backtestError = ''
      if (!this.backtestTemplates.length) this.loadBacktestTemplates()
      this.$nextTick(() => {
        const panel = this.$refs.readonlyBacktestPanel
        const node = panel && (panel.$el || panel)
        if (node && typeof node.scrollIntoView === 'function') {
          node.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
        this.drawBacktestEquityChart()
      })
    },
    crossAnalysisCustomRow (record) {
      return {
        on: {
          click: () => this.loadCrossAnalysisDetail(record)
        }
      }
    },
    crossTrendColor (row) {
      const label = row && row.quantdinger && row.quantdinger.trend_label
      if (label === 'uptrend' || label === 'rebound') return 'green'
      if (label === 'downtrend' || label === 'pullback') return 'red'
      if (label === 'sideways' || label === 'unknown') return 'orange'
      return 'default'
    },
    crossCategoryColor (category) {
      if (category === 'focus_watch') return 'green'
      if (category === 'secondary_watch') return 'blue'
      if (category === 'model_trend_divergence') return 'orange'
      if (category === 'data_review_required' || category === 'trend_unavailable') return 'red'
      return 'default'
    },
    crossAlignmentColor (alignment) {
      if (alignment === 'aligned') return 'green'
      if (alignment === 'divergent') return 'orange'
      if (alignment === 'blocked') return 'red'
      return 'default'
    },
    crossBasisColor (status) {
      if (status === 'ok') return 'green'
      if (status === 'date_gap') return 'orange'
      if (status === 'quantdinger_raw_unavailable') return 'red'
      return 'default'
    },

    normalizeQlibOpsJob (job) {
      return job && typeof job === 'object' ? job : null
    },
    async loadQlibScheduler () {
      try {
        const data = this.unwrap(await getQlibOptionCScheduler())
        this.qlibScheduler = data && typeof data === 'object' ? data : {}
      } catch (error) {
        this.qlibScheduler = { enabled: false, mode: 'dry-run-only', auto_loop_started: false }
      }
    },
    async loadQlibOpsLatest () {
      this.loadingQlibOps = true
      this.qlibOpsError = ''
      try {
        const data = this.unwrap(await getQlibOptionCLatestJob())
        this.qlibOpsJob = this.normalizeQlibOpsJob(data && data.job)
        if (this.qlibOpsJob && this.qlibOpsJob.job_id) await this.loadQlibOpsLog(this.qlibOpsLogStream)
      } catch (error) {
        const response = error && error.response && error.response.data
        this.qlibOpsError = (response && response.msg) || error.message || 'Option C ops dry-run 狀態讀取失敗'
      } finally {
        this.loadingQlibOps = false
      }
    },
    async triggerQlibOpsDryRun () {
      if (!this.qlibOpsCanTrigger) {
        this.qlibOpsError = 'Option C ops admin or tw_stock_qlib_ops permission required'
        return
      }
      const asof = this.formatPickerDate(this.qlibOpsForm.asof) || String(this.qlibOpsForm.asof || '').trim()
      if (!/^\d{4}-\d{2}-\d{2}$/.test(asof)) {
        this.qlibOpsError = 'asof must match YYYY-MM-DD'
        return
      }
      this.runningQlibOpsDryRun = true
      this.qlibOpsError = ''
      try {
        const data = this.unwrap(await triggerQlibOptionCDryRun(asof))
        this.qlibOpsJob = this.normalizeQlibOpsJob(data)
        if (this.qlibOpsJob && this.qlibOpsJob.job_id) {
          await this.refreshQlibOpsJob()
          await this.loadQlibOpsLog(this.qlibOpsLogStream)
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.qlibOpsJob = this.normalizeQlibOpsJob(data) || this.qlibOpsJob
        this.qlibOpsError = (response && response.msg) || error.message || 'Option C ops dry-run 執行失敗'
      } finally {
        this.runningQlibOpsDryRun = false
      }
    },
    async refreshQlibOpsJob () {
      if (!this.qlibOpsJob || !this.qlibOpsJob.job_id) return
      this.loadingQlibOps = true
      try {
        const data = this.unwrap(await getQlibOptionCJob(this.qlibOpsJob.job_id))
        this.qlibOpsJob = this.normalizeQlibOpsJob(data) || this.qlibOpsJob
      } finally {
        this.loadingQlibOps = false
      }
    },
    async loadQlibOpsLog (stream = this.qlibOpsLogStream) {
      if (!this.qlibOpsJob || !this.qlibOpsJob.job_id) {
        this.qlibOpsLogTail = ''
        return
      }
      const normalized = stream === 'stderr' ? 'stderr' : 'stdout'
      this.qlibOpsLogStream = normalized
      this.loadingQlibOpsLog = true
      try {
        const data = this.unwrap(await getQlibOptionCJobLog(this.qlibOpsJob.job_id, normalized))
        this.qlibOpsLogTail = (data && data.tail) || ''
      } finally {
        this.loadingQlibOpsLog = false
      }
    },

    qlibWatchDraftStorageKey () {
      return 'tw-stock-monitor-qlib-watch-draft'
    },
    loadQlibWatchDraft () {
      try {
        const raw = window.localStorage.getItem(this.qlibWatchDraftStorageKey())
        const items = raw ? JSON.parse(raw) : []
        this.qlibWatchDraft = Array.isArray(items) ? items.filter(item => item && item.symbol).slice(0, 80) : []
      } catch (error) {
        this.qlibWatchDraft = []
      }
    },
    persistQlibWatchDraft () {
      try {
        window.localStorage.setItem(this.qlibWatchDraftStorageKey(), JSON.stringify(this.qlibWatchDraft))
      } catch (error) {}
    },
    addQlibWatchDraft (row) {
      if (!row || !row.symbol) return
      const trend = row.trend || {}
      const item = {
        symbol: String(row.symbol).trim().toUpperCase(),
        run_id: (this.qlibPayload && this.qlibPayload.run_id) || '',
        rank: row.rank,
        qlib_score: row.qlib_score,
        trend_label: trend.trend_label || '',
        trend_score: trend.trend_score == null ? null : trend.trend_score
      }
      const next = this.qlibWatchDraft.filter(existing => existing.symbol !== item.symbol)
      next.unshift(item)
      this.qlibWatchDraft = next.slice(0, 80)
      this.persistQlibWatchDraft()
    },
    removeQlibWatchDraft (symbol) {
      const normalized = String(symbol || '').trim().toUpperCase()
      this.qlibWatchDraft = this.qlibWatchDraft.filter(item => item.symbol !== normalized)
      this.persistQlibWatchDraft()
    },
    clearQlibWatchDraft () {
      this.qlibWatchDraft = []
      this.persistQlibWatchDraft()
    },
    fillMonitorConfigFromQlibDraft () {
      const symbols = []
      const seen = new Set()
      const add = symbol => {
        const normalized = String(symbol || '').trim().toUpperCase()
        if (normalized && !seen.has(normalized)) {
          seen.add(normalized)
          symbols.push(normalized)
        }
      }
      ;(this.config.symbols || []).forEach(add)
      this.qlibWatchDraft.forEach(item => add(item.symbol))
      this.configForm = Object.assign({}, this.config, this.configForm, {
        symbolsText: symbols.join(', ')
      })
      this.configDrawerVisible = true
    },
    qlibTrendAvailable (row) {
      return !!(row && row.trend && row.trend.ok)
    },
    async openQlibReadonlyBacktest (row) {
      if (!row || !row.symbol) return
      await this.selectTrendSymbol(row.symbol)
      this.backtestPanelVisible = true
      if (!this.backtestTemplates.length) this.loadBacktestTemplates()
      this.$nextTick(() => {
        const panel = this.$refs.readonlyBacktestPanel
        const node = panel && (panel.$el || panel)
        if (node && typeof node.scrollIntoView === 'function') {
          node.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
        this.drawBacktestEquityChart()
      })
    },
    qlibCustomRow (record) {
      return {
        on: {
          click: () => this.selectTrendSymbol(record.symbol)
        }
      }
    },
    async loadBacktestTemplates () {
      this.loadingBacktestTemplates = true
      try {
        const data = this.unwrap(await getTwStockBacktestTemplates())
        this.backtestTemplates = (data && data.items) || []
        if (!this.backtestTemplates.find(item => item.id === this.backtestForm.strategyId) && this.backtestTemplates.length) {
          this.backtestForm.strategyId = this.backtestTemplates[0].id
        }
      } finally {
        this.loadingBacktestTemplates = false
      }
    },
    openBacktestPanel () {
      this.backtestPanelVisible = true
      if (!this.backtestTemplates.length) this.loadBacktestTemplates()
      this.$nextTick(this.drawBacktestEquityChart)
    },
    async runReadonlyBacktest () {
      if (!this.chartSymbol) return
      this.runningBacktest = true
      this.backtestError = ''
      try {
        const payload = {
          symbol: this.chartSymbol,
          strategyId: this.backtestForm.strategyId,
          startDate: this.formatPickerDate(this.backtestForm.startDate),
          endDate: this.formatPickerDate(this.backtestForm.endDate),
          initialCapital: Number(this.backtestForm.initialCapital || 1000000),
          strategyConfig: { template: {} }
        }
        const data = this.unwrap(await runTwStockReadonlyBacktest(payload))
        this.backtestResult = data && data.result ? data.result : data
        this.$nextTick(this.drawBacktestEquityChart)
      } catch (error) {
        const response = error && error.response && error.response.data
        const message = (response && response.msg) || error.message || '回測資料不足，請先更新本地日線歸檔。'
        this.backtestError = message.includes('qd_tw_stock_daily_bars') ? '需要先更新本地日線歸檔 qd_tw_stock_daily_bars 後再回測。' : message
        this.backtestResult = null
      } finally {
        this.runningBacktest = false
      }
    },
    async refreshAll () {
      this.loading = true
      try {
        await this.loadConfig()
        await Promise.all([this.loadTrends(), this.loadAlerts(), this.loadScanLogs(), this.loadQlibHealth(), this.loadQlibSignals(), this.loadQlibOpsLatest(), this.loadCrossAnalysis(), this.loadTwStockAgentContext()])
        this.lastRefreshedAt = new Date().toLocaleTimeString()
        this.syncAutoRefreshTimer()
      } finally {
        this.loading = false
      }
    },
    async loadConfig () {
      const data = this.unwrap(await getTwStockMonitorConfig({ name: this.config.name || 'default' }))
      this.config = Object.assign({}, this.config, data || {})
      if (data && data.degraded) {
        this.degradedNotice = '資料庫暫不可用：已載入預設台股清單，可查看趨勢與執行一次性研究掃描，但提醒與歷史不會持久保存。'
      }
    },
    async loadTrends () {
      if (!this.config.symbols || !this.config.symbols.length) return
      this.loadingTrends = true
      try {
        const data = this.unwrap(await getTwStockTrends({
          symbols: this.config.symbols.join(','),
          limit: this.config.limit_bars || 120
        }))
        this.trendItems = data.items || []
        this.syncChartSymbol()
        await Promise.all([this.loadKline(), this.loadHistory()])
        this.$nextTick(this.redrawCharts)
      } finally {
        this.loadingTrends = false
      }
    },
    async loadAlerts () {
      this.loadingAlerts = true
      try {
        const data = this.unwrap(await getTwStockAlerts({
          name: this.config.name || 'default',
          limit: 100,
          unread_only: this.alertFilter === 'unread'
        }))
        this.alertItems = data.items || []
      } finally {
        this.loadingAlerts = false
      }
    },
    async loadScanLogs () {
      const data = this.unwrap(await getTwStockScanLogs({ limit: 20 }))
      this.scanHealth = data.health || {}
    },
    async loadKline () {
      if (!this.chartSymbol) {
        this.priceCandles = []
        return
      }
      this.loadingKline = true
      try {
        const data = this.unwrap(await getTwStockKline({
          symbol: this.chartSymbol,
          limit: this.config.limit_bars || 120
        }))
        this.priceCandles = Array.isArray(data) ? data.map(this.normalizeKlineBar).filter(Boolean) : []
      } finally {
        this.loadingKline = false
      }
    },
    async loadHistory () {
      if (!this.chartSymbol) {
        this.historyItems = []
        return
      }
      this.loadingHistory = true
      try {
        const data = this.unwrap(await getTwStockHistory({
          name: this.config.name || 'default',
          symbol: this.chartSymbol,
          limit: 120
        }))
        this.historyItems = data.items || []
      } finally {
        this.loadingHistory = false
      }
    },
    async runScan () {
      this.scanning = true
      try {
        const scanData = this.unwrap(await scanTwStockMonitor({ name: this.config.name || 'default', force: true }))
        if (scanData && scanData.degraded) {
          this.trendItems = scanData.items || []
          this.scanHealth = {
            status: 'degraded',
            success_count: 1,
            failed_count: 0,
            total_scanned_count: scanData.scanned_count || 0,
            total_alert_count: scanData.alert_count || 0,
            success_rate: 1,
            orders_enabled: false
          }
          this.degradedNotice = '資料庫暫不可用：本次為一次性研究掃描，結果未寫入提醒或歷史。'
          this.syncChartSymbol()
          await Promise.all([this.loadKline(), this.loadHistory().catch(() => { this.historyItems = [] })])
          this.$nextTick(this.redrawCharts)
        } else {
          await Promise.all([this.loadTrends(), this.loadAlerts(), this.loadScanLogs()])
        }
        this.lastRefreshedAt = new Date().toLocaleTimeString()
      } finally {
        this.scanning = false
      }
    },
    openConfigDrawer () {
      this.configForm = Object.assign({}, this.config, {
        symbolsText: (this.config.symbols || []).join(', ')
      })
      this.configDrawerVisible = true
    },
    async saveConfig () {
      this.savingConfig = true
      try {
        const payload = Object.assign({}, this.configForm, {
          symbols: String(this.configForm.symbolsText || '').split(',').map(item => item.trim()).filter(Boolean)
        })
        delete payload.symbolsText
        const data = this.unwrap(await saveTwStockMonitorConfig(payload))
        this.config = Object.assign({}, this.config, data || {})
        this.configDrawerVisible = false
        await this.loadTrends()
        this.syncAutoRefreshTimer()
      } finally {
        this.savingConfig = false
      }
    },
    async updateAlertStatus (row, status) {
      await updateTwStockAlert(row.id, {
        is_read: true,
        decision_status: status,
        user_note: row.user_note || ''
      })
      await this.loadAlerts()
    },
    alertCategory (row) {
      const snapshot = row.snapshot || {}
      const context = snapshot.alert_context || {}
      if (context.category) return context.category
      if (row.alert_type === 'quality_warning') return 'data_quality'
      if (row.alert_type === 'score_change' || row.alert_type === 'label_change') return 'trend_change'
      return 'other'
    },
    alertCategoryColor (row) {
      const category = this.alertCategory(row)
      if (category === 'data_quality') return 'orange'
      if (category === 'trend_change') return 'blue'
      return 'default'
    },
    syncChartSymbol () {
      const symbols = this.chartSymbols
      if (!symbols.length) {
        this.chartSymbol = ''
        return
      }
      if (!this.chartSymbol || !symbols.includes(this.chartSymbol)) {
        this.chartSymbol = symbols[0]
      }
    },
    async handleChartSymbolChange () {
      this.clearChartHover('price')
      this.clearChartHover('score')
      await Promise.all([this.loadKline(), this.loadHistory()])
      this.$nextTick(this.redrawCharts)
    },
    async selectTrendSymbol (symbol) {
      if (!symbol || symbol === this.chartSymbol) return
      this.chartSymbol = symbol
      await this.handleChartSymbolChange()
    },
    trendCustomRow (record) {
      return {
        on: {
          click: () => this.selectTrendSymbol(record.symbol)
        }
      }
    },
    trendRowClassName (record) {
      return record && record.symbol === this.chartSymbol ? 'trend-row-active' : 'trend-row-clickable'
    },
    async refreshSelectedChart () {
      await Promise.all([this.loadTrends(), this.loadKline(), this.loadHistory()])
      this.$nextTick(this.redrawCharts)
    },
    handleChartRangeChange () {
      this.clearChartHover('price')
      this.clearChartHover('score')
      this.$nextTick(this.redrawCharts)
    },
    sliceByChartRange (items) {
      if (!Array.isArray(items)) return []
      if (this.chartRangeBars === 'all') return items
      const count = Number(this.chartRangeBars || 0)
      return count > 0 ? items.slice(-count) : items
    },
    handleAutoRefreshChange () {
      this.syncAutoRefreshTimer()
    },
    syncAutoRefreshTimer () {
      this.stopAutoRefresh()
      if (!this.autoRefreshEnabled || !this.refreshIntervalMs) return
      this.autoRefreshTimer = window.setInterval(() => {
        if (!this.loading && !this.scanning) this.refreshAll()
      }, this.refreshIntervalMs)
    },
    stopAutoRefresh () {
      if (this.autoRefreshTimer) {
        window.clearInterval(this.autoRefreshTimer)
        this.autoRefreshTimer = null
      }
    },
    normalizeKlineBar (bar) {
      if (!bar || typeof bar !== 'object') return null
      const close = Number(bar.close)
      const open = Number(bar.open == null ? close : bar.open)
      const high = Number(bar.high == null ? Math.max(open, close) : bar.high)
      const low = Number(bar.low == null ? Math.min(open, close) : bar.low)
      const rawTime = Number(bar.time || bar.timestamp || 0)
      if (!Number.isFinite(close) || close <= 0) return null
      return {
        date: this.formatKlineDate(rawTime),
        open,
        high,
        low,
        close,
        volume: Number(bar.volume || 0)
      }
    },
    formatPercent (value) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return `${(num * 100).toFixed(2)}%`
    },
    formatNumber (value, digits = 2) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return num.toFixed(digits)
    },
    formatCompactNumber (value) {
      const num = Number(value || 0)
      if (!Number.isFinite(num) || num <= 0) return '-'
      if (num >= 100000000) return `${(num / 100000000).toFixed(2)}億`
      if (num >= 10000) return `${(num / 10000).toFixed(1)}萬`
      return String(Math.round(num))
    },
    formatSignedPercentFromNumber (value) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return `${num.toFixed(2)}%`
    },
    trendTagColor (item) {
      const label = item && item.trend && item.trend.label
      if (label === 'uptrend' || label === 'rebound') return 'green'
      if (label === 'downtrend' || label === 'pullback') return 'red'
      if (label === 'sideways') return 'orange'
      return 'blue'
    },
    movingAveragePoints (period) {
      const values = this.displayedPriceCandles.map(item => Number(item.close || 0))
      return this.displayedPriceCandles.map((item, index) => {
        if (index + 1 < period) return Object.assign({}, item, { ma: null })
        const slice = values.slice(index + 1 - period, index + 1)
        const ma = slice.reduce((sum, value) => sum + value, 0) / period
        return Object.assign({}, item, { ma })
      })
    },
    formatKlineDate (time) {
      if (!time) return ''
      const millis = time > 1000000000000 ? time : time * 1000
      const parsed = new Date(millis)
      if (Number.isNaN(parsed.getTime())) return ''
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Taipei',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).format(parsed)
    },
    redrawCharts () {
      this.drawPriceChart()
      this.drawScoreChart()
      this.drawBacktestEquityChart()
    },
    drawPriceChart () {
      this.chartLayouts.price = this.drawFinancialChart(this.$refs.priceChart, this.displayedPriceCandles, {
        mode: this.priceChartMode,
        yKey: 'close',
        lineColor: '#2563eb',
        upColor: '#cf1322',
        downColor: '#0f8a4b',
        hoverIndex: this.chartHover.price && this.chartHover.price.index,
        showVolume: this.showVolume,
        movingAverages: this.showMovingAverages
          ? [
              { label: 'MA5', color: '#f59e0b', points: this.movingAveragePoints(5) },
              { label: 'MA20', color: '#2563eb', points: this.movingAveragePoints(20) },
              { label: 'MA60', color: '#7c3aed', points: this.movingAveragePoints(60) }
            ]
          : []
      })
    },
    drawScoreChart () {
      const points = this.displayedHistoryItems.map(item => ({
        date: item.latest_date || item.scanned_at || '',
        close: Number(item.score || 0)
      }))
      this.chartLayouts.score = this.drawFinancialChart(this.$refs.scoreChart, points, {
        mode: 'line',
        yKey: 'close',
        minY: 0,
        maxY: 100,
        lineColor: '#7c3aed',
        hoverIndex: this.chartHover.score && this.chartHover.score.index
      })
    },
    drawBacktestEquityChart () {
      const points = this.backtestEquityCurve.map(item => ({
        date: String(item.time || '').slice(0, 10),
        close: Number(item.value || 0)
      })).filter(item => Number.isFinite(item.close) && item.close > 0)
      this.chartLayouts.backtest = this.drawFinancialChart(this.$refs.backtestEquityChart, points, {
        mode: 'line',
        yKey: 'close',
        lineColor: '#0f766e'
      })
    },
    handleChartMouseMove (chartKey, event) {
      const layout = this.chartLayouts[chartKey]
      if (!layout || !layout.points.length) return
      const rect = event.currentTarget.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const rawIndex = layout.points.length > 1
        ? Math.round((mouseX - layout.pad.left) / layout.xStep)
        : 0
      const index = Math.max(0, Math.min(layout.points.length - 1, rawIndex))
      const x = layout.pad.left + (layout.points.length > 1 ? layout.xStep * index : layout.plotW / 2)
      const point = layout.points[index]
      const y = layout.y(Number(point.close || point[layout.yKey] || 0))
      const hover = { index, x, y, point }
      this.$set(this.chartHover, chartKey, hover)
      if (chartKey === 'price') this.drawPriceChart()
      else this.drawScoreChart()
    },
    clearChartHover (chartKey) {
      if (!this.chartHover[chartKey]) return
      this.$set(this.chartHover, chartKey, null)
      if (chartKey === 'price') this.drawPriceChart()
      else this.drawScoreChart()
    },
    chartTooltipStyle (hover) {
      return {
        left: `${Math.max(8, hover.x + 12)}px`,
        top: `${Math.max(8, hover.y - 12)}px`
      }
    },
    drawFinancialChart (canvas, points, options = {}) {
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const rect = canvas.getBoundingClientRect()
      const ratio = window.devicePixelRatio || 1
      const width = Math.max(320, Math.floor(rect.width || canvas.width))
      const height = Math.max(220, Math.floor(rect.height || canvas.height))
      canvas.width = width * ratio
      canvas.height = height * ratio
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, width, height)
      if (!points.length) return null
      const pad = { left: 48, right: 16, top: 18, bottom: 34 }
      const yKey = options.yKey || 'close'
      const volumeH = options.showVolume ? Math.max(54, Math.floor(height * 0.18)) : 0
      const volumeGap = options.showVolume ? 12 : 0
      const values = points
        .flatMap(point => [point.open, point.high, point.low, point.close, point[yKey]])
        .concat((options.movingAverages || []).flatMap(ma => ma.points.map(point => point.ma)))
        .map(Number)
        .filter(value => Number.isFinite(value) && value > 0)
      const minY = options.minY != null ? options.minY : Math.min(...values) * 0.995
      const maxY = options.maxY != null ? options.maxY : Math.max(...values) * 1.005
      const plotW = width - pad.left - pad.right
      const plotH = height - pad.top - pad.bottom - volumeH - volumeGap
      const volumeTop = pad.top + plotH + volumeGap
      const xStep = points.length > 1 ? plotW / (points.length - 1) : plotW
      const y = value => pad.top + (maxY - value) / Math.max(1, maxY - minY) * plotH
      ctx.strokeStyle = '#e5e7eb'
      ctx.lineWidth = 1
      for (let i = 0; i <= 4; i += 1) {
        const gy = pad.top + (plotH / 4) * i
        ctx.beginPath()
        ctx.moveTo(pad.left, gy)
        ctx.lineTo(width - pad.right, gy)
        ctx.stroke()
      }
      ctx.fillStyle = '#667085'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(maxY.toFixed(2), pad.left - 8, pad.top + 4)
      ctx.fillText(minY.toFixed(2), pad.left - 8, pad.top + plotH)
      if (options.mode === 'candles') {
        const candleW = Math.max(8, Math.min(34, xStep * 0.48))
        points.forEach((point, index) => {
          const x = pad.left + (points.length > 1 ? xStep * index : plotW / 2)
          const open = Number(point.open || point.close)
          const close = Number(point.close || open)
          const high = Number(point.high || Math.max(open, close))
          const low = Number(point.low || Math.min(open, close))
          const color = close >= open ? (options.upColor || '#cf1322') : (options.downColor || '#0f8a4b')
          ctx.strokeStyle = color
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.moveTo(x, y(high))
          ctx.lineTo(x, y(low))
          ctx.stroke()
          const top = Math.min(y(open), y(close))
          const bodyH = Math.max(2, Math.abs(y(open) - y(close)))
          ctx.fillRect(x - candleW / 2, top, candleW, bodyH)
        })
      } else {
        ctx.strokeStyle = options.lineColor || '#2563eb'
        ctx.lineWidth = 2
        ctx.beginPath()
        points.forEach((point, index) => {
          const x = pad.left + (points.length > 1 ? xStep * index : plotW / 2)
          const py = y(Number(point[yKey] || point.close || 0))
          if (index === 0) ctx.moveTo(x, py)
          else ctx.lineTo(x, py)
        })
        ctx.stroke()
      }
      ;(options.movingAverages || []).forEach(ma => {
        ctx.strokeStyle = ma.color
        ctx.lineWidth = 1.6
        ctx.beginPath()
        let started = false
        ma.points.forEach((point, index) => {
          if (!point.ma) return
          const x = pad.left + (points.length > 1 ? xStep * index : plotW / 2)
          const py = y(Number(point.ma))
          if (!started) {
            ctx.moveTo(x, py)
            started = true
          } else {
            ctx.lineTo(x, py)
          }
        })
        if (started) ctx.stroke()
      })
      if (options.showVolume) {
        const maxVolume = Math.max(...points.map(point => Number(point.volume || 0)), 1)
        ctx.strokeStyle = '#e5e7eb'
        ctx.beginPath()
        ctx.moveTo(pad.left, volumeTop)
        ctx.lineTo(width - pad.right, volumeTop)
        ctx.stroke()
        const barW = Math.max(2, Math.min(9, xStep * 0.42))
        points.forEach((point, index) => {
          const x = pad.left + (points.length > 1 ? xStep * index : plotW / 2)
          const open = Number(point.open || point.close)
          const close = Number(point.close || open)
          const color = close >= open ? 'rgba(207, 19, 34, 0.42)' : 'rgba(15, 138, 75, 0.42)'
          const h = Math.max(1, Number(point.volume || 0) / maxVolume * volumeH)
          ctx.fillStyle = color
          ctx.fillRect(x - barW / 2, volumeTop + volumeH - h, barW, h)
        })
      }
      const hoverIndex = Number(options.hoverIndex)
      if (Number.isInteger(hoverIndex) && hoverIndex >= 0 && hoverIndex < points.length) {
        const x = pad.left + (points.length > 1 ? xStep * hoverIndex : plotW / 2)
        const point = points[hoverIndex]
        const py = y(Number(point.close || point[yKey] || 0))
        ctx.strokeStyle = 'rgba(17, 24, 39, 0.42)'
        ctx.lineWidth = 1
        ctx.setLineDash([4, 4])
        ctx.beginPath()
        ctx.moveTo(x, pad.top)
        ctx.lineTo(x, pad.top + plotH + volumeH + volumeGap)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(pad.left, py)
        ctx.lineTo(width - pad.right, py)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.fillStyle = '#111827'
        ctx.beginPath()
        ctx.arc(x, py, 3, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.fillStyle = '#667085'
      ctx.textAlign = 'left'
      ctx.fillText(points[0].date || '', pad.left, height - 10)
      ctx.textAlign = 'right'
      ctx.fillText(points[points.length - 1].date || '', width - pad.right, height - 10)
      return { pad, width, height, plotW, plotH, xStep, points, y, yKey }
    }
  }
}
</script>

<style lang="less" scoped>
.tw-stock-monitor {
  padding: 20px;
  background: #f5f7fb;
  min-height: 100%;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.topbar h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 650;
}

.subline,
.top-actions,
.drawer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.refresh-status {
  color: #667085;
  font-size: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  min-height: 92px;
  background: #fff;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-card strong {
  font-size: 22px;
  color: #1f2937;
}

.metric-card small,
.metric-label,
.muted {
  color: #667085;
}

.muted {
  margin-left: 6px;
  font-size: 12px;
}

.content-row,
.alerts-card {
  margin-top: 16px;
}

.card-title-line,
.chart-toolbar,
.history-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.chart-toolbar {
  justify-content: flex-start;
  margin-bottom: 12px;
}

.selected-symbol-panel {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) minmax(280px, 1.3fr);
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
}

.selected-symbol-main,
.selected-symbol-stats,
.ma-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.selected-symbol-main strong {
  color: #111827;
  font-size: 18px;
}

.selected-symbol-stats,
.ma-legend {
  color: #475467;
  font-size: 12px;
}

.ma-legend {
  margin-top: 8px;
}

.ma-dot {
  display: inline-block;
  width: 18px;
  height: 3px;
  margin-right: 5px;
  vertical-align: middle;
  border-radius: 999px;
}

.ma-dot.ma5 { background: #f59e0b; }
.ma-dot.ma20 { background: #2563eb; }
.ma-dot.ma60 { background: #7c3aed; }

.chart-frame {
  position: relative;
  min-height: 420px;
}

.chart-frame.compact {
  min-height: 300px;
}

.tw-chart-canvas {
  width: 100%;
  height: 420px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
}

.chart-frame.compact .tw-chart-canvas {
  height: 300px;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  pointer-events: none;
}

.chart-tooltip {
  position: absolute;
  z-index: 3;
  min-width: 116px;
  max-width: 180px;
  padding: 8px 10px;
  background: rgba(17, 24, 39, 0.9);
  color: #fff;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
  pointer-events: none;
  transform: translateY(-50%);
}

.chart-tooltip strong,
.chart-tooltip span {
  display: block;
  line-height: 1.45;
  font-size: 12px;
}

.chart-tooltip strong {
  margin-bottom: 2px;
}

.chart-data-alert {
  margin-bottom: 12px;
}

.chart-footnote,
.history-meta {
  margin-top: 8px;
  color: #667085;
  font-size: 12px;
}

.health-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.health-status {
  font-size: 28px;
  font-weight: 700;
}

.health-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  color: #475467;
}

.health-healthy { color: #0f8a4b; }
.health-degraded { color: #b7791f; }
.health-failed { color: #c53030; }
.health-unknown { color: #667085; }

.alert-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.monitor-degraded-alert {
  margin-bottom: 16px;
}

.readonly-backtest-card {
  margin-top: 16px;
}

.qlib-option-c-card {
  margin-top: 16px;
}

.qlib-toolbar,
.qlib-warning-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.qlib-health-panel {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fbfdff;
}

.qlib-health-header,
.qlib-health-tags {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.qlib-health-header strong {
  display: block;
  margin-bottom: 3px;
}

.qlib-health-tags {
  justify-content: flex-start;
}

.qlib-health-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.qlib-health-grid span {
  min-width: 0;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  color: #475467;
  overflow-wrap: anywhere;
}

.qlib-health-grid strong {
  color: #111827;
  font-weight: 600;
}


.qlib-run-browser {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fbfdff;
}

.qlib-run-header,
.qlib-run-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.qlib-run-table /deep/ .ant-table-row {
  cursor: pointer;
}

.tw-stock-agent-panel {
  margin: 12px 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
}

.agent-panel-header,
.agent-suggestions,
.agent-input-row,
.agent-citations,
.agent-warning-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-panel-header {
  justify-content: space-between;
  margin-bottom: 10px;
}

.agent-context-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.agent-context-grid span {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
  color: #475467;
  overflow-wrap: anywhere;
}

.agent-context-grid strong {
  color: #111827;
}

.agent-suggestions,
.agent-input-row,
.agent-state-alert,
.agent-answer-box,
.agent-disclaimer,
.agent-citations,
.agent-warning-list,
.agent-item-list,
.agent-empty-state {
  margin-top: 10px;
}

.agent-input-row {
  align-items: stretch;
}

.agent-input-row .ant-input {
  flex: 1 1 320px;
}

.agent-answer-box {
  padding: 10px 12px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
}

.agent-answer-box p {
  margin: 6px 0 0;
  color: #1f2937;
  line-height: 1.65;
}

.agent-disclaimer {
  color: #667085;
  font-size: 12px;
}

.agent-item-list {
  display: grid;
  gap: 8px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #ffffff;
  color: #475467;
}

.agent-item strong {
  color: #111827;
}

.agent-empty-state {
  color: #98a2b3;
  font-size: 12px;
}

.run-id-text {
  display: inline-block;
  max-width: 100%;
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}


.qlib-row-actions,
.qlib-watch-draft-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.qlib-watch-draft {
  margin-top: 12px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fbfdff;
}

.qlib-watch-draft-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.qlib-watch-draft-header strong {
  display: block;
  margin-bottom: 3px;
}

.qlib-watch-draft-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qlib-watch-draft-item {
  display: grid;
  grid-template-columns: 80px minmax(180px, 1fr) repeat(4, minmax(80px, auto)) 60px;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #ffffff;
  overflow-wrap: anywhere;
}

.qlib-watch-draft-empty {
  color: #98a2b3;
  font-size: 12px;
}

.qlib-meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.qlib-meta-grid span {
  min-width: 0;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  color: #475467;
  overflow-wrap: anywhere;
}

.qlib-meta-grid strong {
  color: #111827;
  font-weight: 600;
}

.qlib-state-alert {
  margin-bottom: 12px;
}

.qlib-signal-table /deep/ .ant-table-row {
  cursor: pointer;
}

.qlib-empty-state {
  padding: 24px;
  text-align: center;
  color: #98a2b3;
  border: 1px dashed #d9e2ec;
  border-radius: 8px;
  background: #fbfdff;
}

.qlib-footnote {
  margin-top: 10px;
  color: #667085;
  font-size: 12px;
}


.readonly-tags,
.backtest-toolbar,
.backtest-metrics,
.assumption-list,
.quality-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.backtest-toolbar {
  justify-content: flex-start;
  margin-bottom: 12px;
}

.backtest-alert {
  margin-bottom: 12px;
}

.backtest-result {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.backtest-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card.compact {
  min-height: 78px;
}

.backtest-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1.4fr) minmax(280px, 0.6fr);
  gap: 16px;
  align-items: start;
}

.backtest-chart-frame {
  min-height: 300px;
}

.backtest-chart-frame .tw-chart-canvas {
  height: 300px;
}

.backtest-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.readonly-note {
  padding: 10px 12px;
  border: 1px solid #d9f7be;
  background: #f6ffed;
  color: #245b1f;
  border-radius: 8px;
  line-height: 1.5;
}

.assumption-list,
.quality-list {
  align-items: flex-start;
  color: #475467;
  font-size: 12px;
}

.assumption-list span,
.quality-list span {
  padding: 4px 8px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 6px;
}

.backtest-trades {
  margin-top: 4px;
}

/deep/ .trend-row-clickable,
/deep/ .trend-row-active {
  cursor: pointer;
}

/deep/ .trend-row-active td {
  background: #eef6ff !important;
}

.drawer-actions {
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .tw-stock-monitor {
    padding: 12px;
  }

  .topbar {
    flex-direction: column;
  }

  .summary-grid,
  .selected-symbol-panel,
  .backtest-metrics,
  .backtest-grid,
  .cross-freshness-dashboard,
  .cross-detail-grid {
    grid-template-columns: 1fr;
  }
}


.tw-cross-analysis-card {
  margin-top: 16px;
}

.cross-analysis-toolbar,
.cross-analysis-basis,
.cross-detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.cross-analysis-basis {
  color: #475467;
  font-size: 12px;
}

.cross-freshness-dashboard {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.freshness-card {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-wrap: anywhere;
}

.freshness-card span,
.freshness-card small,
.cross-basis-note {
  color: #667085;
  font-size: 12px;
}

.freshness-card strong {
  color: #111827;
}

.cross-basis-note {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #fbfdff;
}

.cross-analysis-table /deep/ .ant-table-row {
  cursor: pointer;
}

.cross-basis-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #475467;
  font-size: 12px;
}

.cross-detail-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #fbfdff;
}

.cross-detail-header {
  justify-content: space-between;
}

.cross-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.cross-detail-grid span {
  min-width: 0;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  color: #475467;
  overflow-wrap: anywhere;
}

.cross-detail-grid strong {
  color: #111827;
}

.cross-review-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
  background: #fff;
}

.cross-review-header,
.cross-review-form {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cross-review-form {
  margin-top: 10px;
}

.cross-review-note {
  margin-top: 8px;
  color: #667085;
  font-size: 12px;
}

.cross-review-alert {
  margin-top: 8px;
}

.qlib-ops-panel {
  margin: 14px 0;
  padding: 14px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #fbfdff;
}

.qlib-ops-header,
.qlib-ops-actions,
.qlib-ops-tags,
.qlib-ops-log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.qlib-ops-tags {
  justify-content: flex-start;
  margin-top: 10px;
}

.qlib-ops-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 14px;
  margin-top: 12px;
  font-size: 12px;
}

.qlib-ops-grid span,
.qlib-ops-empty {
  min-width: 0;
  overflow-wrap: anywhere;
  color: #475467;
}

.qlib-ops-grid strong {
  color: #111827;
  font-weight: 600;
}

.qlib-ops-log {
  margin-top: 12px;
}

.qlib-ops-log-tail {
  margin: 8px 0 0;
  max-height: 180px;
  overflow: auto;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #0f172a;
  color: #d1e7ff;
  font-size: 12px;
  white-space: pre-wrap;
}

</style>
