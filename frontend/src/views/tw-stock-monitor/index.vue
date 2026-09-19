<template>
  <div class="tw-stock-monitor">
    <div class="topbar">
      <div>
        <h2>台股研究</h2>
        <div class="subline">
          <span>台湾股票量化研究工作台</span>
        </div>
      </div>
      <div class="top-actions">
        <a-checkbox v-model="advancedResearchVisible" data-testid="advanced-research-toggle">高级研究与运维</a-checkbox>
        <a-switch
          v-model="autoRefreshEnabled"
          size="small"
          :disabled="!refreshIntervalMs"
          @change="handleAutoRefreshChange"
        />
        <span class="refresh-status">{{ refreshStatusText }}</span>
        <a-button @click="copyReadonlyStatusSummary">
          <a-icon type="copy" /> 复制摘要
        </a-button>
        <a-button @click="downloadReadonlyStatusSummary">
          <a-icon type="download" /> 导出摘要
        </a-button>
        <a-button @click="openConfigDrawer">
          <a-icon type="setting" /> 查看配置
        </a-button>
        <a-button @click="refreshAll" :loading="loading">
          <a-icon type="reload" /> 刷新
        </a-button>
      </div>
    </div>

    <a-alert
      class="research-boundary-alert"
      type="info"
      show-icon
      message="本页面仅用于台股研究信号的人工复盘与历史验证，不连接券商，不产生真实交易委托，不构成投资建议。"
    />

    <div class="page-section-rail" data-testid="tw-stock-section-rail">
      <span class="page-section-rail-label">定位</span>
      <a-button
        v-for="item in pageRailItems"
        :key="item.id"
        size="small"
        :class="['page-section-rail-button', `rail-tone-${item.tone}`]"
        @click="scrollToSection(item.id)"
      >
        {{ item.label }}
      </a-button>
    </div>

    <div class="summary-grid">
      <div class="metric-card">
        <span class="metric-label">当前榜单</span>
        <strong>{{ rankingBucketText }}</strong>
        <small>{{ qlibSignals.length }} 支候选</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">模型日期</span>
        <strong>{{ rankingDateText }}</strong>
        <small>行情 {{ rankingRawDateText }}</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">榜首标的</span>
        <strong>{{ qlibTopSymbol }}</strong>
        <small>{{ qlibTopScoreText }}</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">数据提示</span>
        <strong>{{ rankingQualityStatus }}</strong>
        <small>{{ rankingQualityBrief }}</small>
      </div>
    </div>

    <div class="data-freshness-overview" id="daov-section-freshness" data-testid="tw-stock-data-freshness-overview">
      <div class="data-freshness-header">
        <div>
          <strong>数据链路状态</strong>
          <span>{{ freshnessOverviewMessage }}</span>
        </div>
        <div class="data-freshness-actions">
          <a-tag :color="freshnessOverviewStatusColor">{{ freshnessOverviewStatusText }}</a-tag>
          <a-button
            size="small"
            :loading="loadingReadonlyOpsStatus || loadingDailyAutoUpdateStatus || loadingQlibHealth || loadingCurrentStrategyContext || loadingReadonlyStrategySnapshot || loadingAgentContext"
            @click="refreshFreshnessOverview"
          >
            <a-icon type="reload" /> 刷新状态
          </a-button>
        </div>
      </div>
      <details class="data-freshness-details" data-testid="data-freshness-technical-details">
        <summary>查看数据链路详情</summary>
      <div class="data-freshness-shadow" data-testid="b19r2r-shadow-status">
        <strong>A+B 自动影子：{{ b19ShadowStatusText }}</strong>
        <span>信号日期 {{ b19ShadowAsOf }} · 最近就绪 {{ b19ShadowLastReadyAsOf }}</span>
        <small>独立研究观察，不替换 Model A，不阻塞 Model A 日更。</small>
      </div>
      <div class="data-freshness-track">
        <div class="data-freshness-node">
          <span>Raw / 行情</span>
          <strong>{{ freshnessRawDateText }}</strong>
          <small>{{ freshnessRawSourceText }}</small>
        </div>
        <div class="data-freshness-node" :class="{ lagging: freshnessAcceptedLagging }">
          <span>qlib accepted latest</span>
          <strong>{{ freshnessAcceptedDateText }}</strong>
          <small>{{ freshnessAcceptedSourceText }}</small>
        </div>
        <div class="data-freshness-node" :class="{ lagging: freshnessSnapshotLagging }">
          <span>readonly strategy snapshot latest</span>
          <strong>{{ freshnessSnapshotDateText }}</strong>
          <small>{{ freshnessSnapshotSourceText }}</small>
        </div>
        <div class="data-freshness-node" :class="{ lagging: freshnessAgentLagging }">
          <span>Agent DailyAgentPromptArtifact latest</span>
          <strong>{{ freshnessAgentDateText }}</strong>
          <small>{{ freshnessAgentSourceText }}</small>
        </div>
      </div>
      <div class="data-freshness-ops-grid">
        <div class="data-freshness-ops-item">
          <span>controlled signal latest</span>
          <strong>{{ freshnessControlledSignalDateText }}</strong>
          <small>{{ freshnessControlledSignalSourceText }}</small>
        </div>
        <div class="data-freshness-ops-item">
          <span>latest natural cron job</span>
          <strong>{{ readonlyOpsNaturalCronText }}</strong>
          <small>{{ readonlyOpsNaturalCronDetailText }}</small>
        </div>
        <div class="data-freshness-ops-item">
          <span>latest DAPR18 evidence job</span>
          <strong>{{ readonlyOpsDapr18EvidenceText }}</strong>
          <small>{{ readonlyOpsDapr18EvidenceDetailText }}</small>
        </div>
        <div class="data-freshness-ops-item">
          <span>DAPR18 dry-run/publish flags</span>
          <strong>{{ readonlyOpsDapr18FlagsText }}</strong>
          <small>{{ readonlyOpsDapr18PointerText }}</small>
        </div>
      </div>
      <div class="data-freshness-ops-hint">
        <a-icon type="info-circle" />
        <span><strong>blocker</strong> {{ readonlyOpsBlockerText }}</span>
        <span><strong>next_action_hint</strong> {{ readonlyOpsNextActionHint }}</span>
      </div>
      <div class="data-freshness-footnote">
        <a-icon type="safety-certificate" />
        <span>只读展示；刷新状态只读取现有接口，不拉取数据、不改 latest、不连接券商。</span>
      </div>
      </details>
    </div>

    <a-alert
      v-if="degradedNotice"
      class="monitor-degraded-alert"
      type="warning"
      show-icon
      :message="degradedNotice"
    />

    <a-card
      id="daov-section-strategy"
      class="strategy-workbench-overview-card"
      :bordered="false"
      data-testid="strategy-workbench-overview-card"
    >
      <template slot="title">
        <div class="card-title-line">
          <div class="workbench-title-block">
            <span>今日策略总览</span>
            <small>按当前只读 snapshot asof 查看信号、目标交易日、候选覆盖和模拟账户状态。</small>
          </div>
          <div class="readonly-tags">
            <a-tag color="blue">只读研究</a-tag>
            <a-tag :color="workbenchOverviewStatusColor">{{ workbenchOverviewStatusText }}</a-tag>
          </div>
        </div>
      </template>
      <div class="workbench-overview-toolbar">
        <div class="workbench-status-copy">{{ workbenchOverviewStatusMessage }}</div>
        <div class="workbench-overview-actions">
          <a-button size="small" :loading="loadingCurrentStrategyContext" @click="loadCurrentStrategyContext">
            <a-icon type="reload" /> 刷新策略口径
          </a-button>
          <a-button size="small" :loading="loadingPhaseYZProductization" @click="loadPhaseYZProductizationStatus">
            <a-icon type="reload" /> 刷新模拟状态
          </a-button>
        </div>
      </div>
      <a-alert
        v-if="currentStrategyContextError"
        class="workbench-overview-alert"
        type="warning"
        show-icon
        :message="currentStrategyContextError"
      />
      <a-alert
        v-if="phaseYZProductizationError"
        class="workbench-overview-alert"
        type="warning"
        show-icon
        :message="phaseYZProductizationError"
      />
      <a-alert
        v-if="currentStrategyContextMismatchText"
        class="workbench-overview-alert"
        type="info"
        show-icon
        :message="currentStrategyContextMismatchText"
      />
      <div class="workbench-overview-grid">
        <div>
          <span>信号日期</span>
          <strong>{{ currentContextSignalAsOf }}</strong>
          <small>目标交易日：{{ workbenchTargetTradingDay }}</small>
        </div>
        <div>
          <span>模型与策略</span>
          <strong>{{ workbenchModelDisplayText }}</strong>
          <small>{{ workbenchStrategyDisplayText }}</small>
        </div>
        <div>
          <span>候选覆盖</span>
          <strong>{{ workbenchCandidateCoverageText }}</strong>
          <small>Model A 榜首：{{ currentContextLTRTopSymbol }}</small>
        </div>
        <div>
          <span>模拟账户</span>
          <strong>{{ workbenchPaperApplyStatusText }}</strong>
          <small>{{ workbenchPaperApplyReasonText }}</small>
        </div>
      </div>
      <a-collapse class="workbench-technical-collapse" :bordered="false">
        <a-collapse-panel key="strategy-overview-tech" header="查看技术详情">
          <div class="workbench-technical-grid">
            <span>base_model_id <strong>{{ workbenchBaseModelId }}</strong></span>
            <span>treatment_model_id <strong>{{ workbenchTreatmentModelId }}</strong></span>
            <span>strategy_rule <strong>{{ currentContextStrategyRule }}</strong></span>
            <span>ranking_source <strong>{{ workbenchRankingSource }}</strong></span>
            <span>candidate_boundary <strong>{{ workbenchCandidateBoundary }}</strong></span>
            <span>execution_price_mode <strong>{{ phaseYZExecutionPriceMode }}</strong></span>
            <span>current context status <strong>{{ currentStrategyContextStatusText }}</strong></span>
            <span>productization state <strong>{{ phaseYZProductizationStateText }}</strong></span>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </a-card>

    <readonly-model-strategy-comparison-panel
      :payload="readonlyModelStrategyComparisonPayload"
      :error="readonlyModelStrategyComparisonError"
      :loading="loadingReadonlyModelStrategyComparison"
      @select="loadReadonlyModelStrategyComparison"
      @refresh="loadReadonlyModelStrategyComparison"
    />

    <section id="daov-section-snapshot" class="monitor-anchor-section">
      <readonly-strategy-snapshot-panel
        :payload="readonlyStrategySnapshotPayload"
        :error="readonlyStrategySnapshotError"
        :loading="loadingReadonlyStrategySnapshot"
        @refresh="loadReadonlyStrategySnapshot"
      />
    </section>

    <section id="daov-section-replay" class="monitor-anchor-section">
      <readonly-replay-window-panel
        :index-payload="readonlyReplayWindowIndexPayload"
        :payload="readonlyReplayWindowPayload"
        :index-error="readonlyReplayWindowIndexError"
        :error="readonlyReplayWindowError"
        :loading-index="loadingReadonlyReplayWindowIndex"
        :loading-window="loadingReadonlyReplayWindow"
        :active-model-id="currentStrategyContext.default_model_id"
        :selected-key="readonlyReplayWindowSelectedKey"
        @select-window="handleReadonlyReplayWindowSelect"
        @refresh-index="loadReadonlyReplayWindowIndex"
        @query="loadReadonlyReplayWindow"
      />
    </section>

    <section class="monitor-anchor-section">
      <paper-portfolio-panel
        :phase-yz-status="phaseYZProductizationPayload"
        @ask-agent="askAgentFromWorkbench"
      />
    </section>

    <readonly-shadow-exposure-panel
      v-show="advancedResearchVisible"
      :payload="readonlyShadowExposurePayload"
      :error="readonlyShadowExposureError"
      :loading="loadingReadonlyShadowExposure"
      @refresh="loadReadonlyShadowExposure"
    />

    <trading-agents-readonly-panel
      v-show="advancedResearchVisible"
      :payload="tradingAgentsReadonlyPayload"
      :error="tradingAgentsReadonlyError"
      :loading="loadingTradingAgentsReadonly"
      @refresh="loadTradingAgentsReadonlyAnalysis"
    />

    <a-card v-show="advancedResearchVisible" id="daov-section-research" class="rank-tech-replay-card" :bordered="false" data-testid="rank-tech-portfolio-replay-readonly">
      <template slot="title">
        <div class="card-title-line">
        <span>今日复盘与历史模拟</span>
          <div class="readonly-tags">
            <a-tag color="blue">只读研究</a-tag>
            <a-tag color="green">不连接券商</a-tag>
          </div>
        </div>
      </template>
      <div class="rank-tech-toolbar" data-testid="rank-tech-replay-controls">
        <a-radio-group v-model="rankTechBucket" size="small" @change="handleRankTechReplayControlChange">
          <a-radio-button value="top30">Top30</a-radio-button>
          <a-radio-button value="top50">Top50</a-radio-button>
        </a-radio-group>
        <a-radio-group v-model="rankTechRange" size="small" @change="handlePortfolioReplayControlChange">
          <a-radio-button value="half_year">近半年</a-radio-button>
          <a-radio-button value="one_year">近一年</a-radio-button>
        </a-radio-group>
        <a-select v-model="rankTechVariant" size="small" style="width: 240px" @change="handlePortfolioReplayControlChange">
          <a-select-option value="all">全部对照</a-select-option>
          <a-select-option value="qlib_only">只看模型排名</a-select-option>
          <a-select-option value="qlib_plus_trend">加入趋势确认</a-select-option>
          <a-select-option value="qlib_plus_trend_indicators">加入技术指标确认</a-select-option>
          <a-select-option value="qlib_plus_trend_position_risk">加入追高风险过滤</a-select-option>
        </a-select>
        <a-button size="small" :loading="loadingRankTechCross || runningPortfolioReplay" @click="loadRankTechPortfolioPanel">
          <a-icon type="reload" /> 刷新复盘
        </a-button>
      </div>
      <a-alert
        class="rank-tech-readonly-note"
        type="info"
        show-icon
        message="只读历史模拟，不是投资建议，不连接券商，不生成订单。"
      />
      <a-alert
        v-if="rankTechLatestError"
        class="rank-tech-alert"
        type="warning"
        show-icon
        :message="rankTechLatestError"
      />
      <div class="rank-tech-grid">
        <section class="rank-tech-panel">
          <div class="rank-tech-panel-head">
            <strong>今天先看什么</strong>
            <a-tag :color="rankTechAccepted ? 'green' : 'orange'">{{ rankTechStatusText }}</a-tag>
          </div>
          <div v-if="loadingRankTechCross" class="rank-tech-empty">正在读取当前 asof 复盘...</div>
          <div v-else-if="rankTechPriorityItems.length" class="rank-tech-priority-list">
            <div v-for="item in rankTechPriorityItems" :key="`rank-tech-${item.symbol}`" class="rank-tech-priority-item">
              <div class="rank-tech-symbol-line">
                <strong>{{ item.symbol }}</strong>
                <span>{{ item.name || displayStockName(item) }}</span>
                <a-tag :color="rankTechActionColor(item)">{{ rankTechActionLabel(item) }}</a-tag>
                <a-tag :color="positionRiskColor(item)">{{ positionRiskLabel(item) }}</a-tag>
              </div>
              <div class="rank-tech-reason-line">
                <span>{{ rankTechUserConclusion(item) }}</span>
                <span>{{ rankTechUserReason(item) }}</span>
                <span class="muted">{{ rankTechUserEvidence(item) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="rank-tech-empty">暂无可展示的当前 asof 复盘。</div>
        </section>
        <section class="rank-tech-panel">
          <div class="rank-tech-panel-head">
            <strong>为什么</strong>
            <span>{{ rankTechBucketLabel }} · {{ rankTechDateText }}</span>
          </div>
          <div v-if="rankTechPriorityItems.length" class="rank-tech-why-list">
            <div v-for="item in rankTechPriorityItems.slice(0, 4)" :key="`rank-tech-why-${item.symbol}`" class="rank-tech-why-item">
              <strong>{{ item.symbol }} {{ item.name || '' }}</strong>
              <span>{{ rankTechUserConclusion(item) }}</span>
              <span>{{ rankTechUserReason(item) }}</span>
              <span>{{ rankTechUserEvidence(item) }}</span>
              <span>位置 {{ positionRiskLabel(item) }}：{{ positionRiskReason(item) }}</span>
              <small>{{ rankTechQualityBrief(item) }}</small>
            </div>
          </div>
          <div v-else class="rank-tech-empty">等待当前 asof 复盘数据。</div>
        </section>
      </div>


      <section class="ltr-readonly-explanation" data-testid="ltr-readonly-explanation-panel">
        <div class="rank-tech-panel-head">
          <strong>为什么现在不动</strong>
          <a-tag color="blue">只读复盘</a-tag>
        </div>
        <a-alert
          v-if="ltrReadonlyExplanationError"
          class="rank-tech-alert"
          type="warning"
          show-icon
          :message="ltrReadonlyExplanationError"
        />
        <div v-if="loadingLtrReadonlyExplanation" class="rank-tech-empty">正在读取只读解释...</div>
        <div v-else-if="ltrReadonlyExplanationMethods.length" class="ltr-explanation-grid">
          <div v-for="item in ltrReadonlyExplanationMethods" :key="item.method_key" class="ltr-explanation-card">
            <strong>{{ item.why_no_action }}</strong>
            <span>{{ item.tradeoff_summary }}</span>
            <a-tag color="purple">{{ item.research_role_label }}</a-tag>
            <small>{{ item.readonly_disclaimer }}</small>
            <a-collapse class="ltr-explanation-detail" :bordered="false">
              <a-collapse-panel key="detail" header="查看历史回放明细">
                <div class="ltr-detail-grid">
                  <span>{{ item.detail.net_return_summary }}</span>
                  <span>{{ item.detail.drawdown_summary }}</span>
                  <span>{{ item.detail.action_count_summary }}</span>
                  <span>{{ item.detail.turnover_summary }}</span>
                  <span class="ltr-detail-wide">{{ item.detail.relative_to_top50_adaptive }}</span>
                  <small class="ltr-detail-wide">{{ item.detail.detail_disclaimer }}</small>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </div>
        <div v-else class="rank-tech-empty">只读解释暂不可用。</div>
      </section>

      <section class="ltr-optional-sim-strategy" data-testid="ltr-optional-sim-strategy-panel">
        <div class="rank-tech-panel-head">
          <strong>历史研究策略（当前 baseline 仅 Model A）</strong>
          <div>
            <a-tag color="blue">默认主策略</a-tag>
            <a-tag color="cyan">可选模拟</a-tag>
            <a-tag color="green">只读历史模拟</a-tag>
          </div>
        </div>
        <a-alert
          class="rank-tech-alert"
          type="info"
          show-icon
          :message="`Model B/LTR 仅保留为只读历史研究，不参与当前 Model-A-only baseline。${ltrOptionalSimBoundaryText}`"
        />
        <a-alert
          class="rank-tech-alert"
          type="warning"
          show-icon
          message="历史模拟，不代表未来收益；首屏主指标使用独立测试区间，明细包含样本内/验证/样本外混合结果。"
        />
        <a-alert
          v-if="ltrOptionalSimError"
          class="rank-tech-alert"
          type="warning"
          show-icon
          :message="ltrOptionalSimError"
        />
        <div v-if="loadingLtrOptionalSimStrategies" class="rank-tech-empty">正在读取可选模拟策略...</div>
        <div v-else-if="ltrOptionalSimStrategies.length" class="ltr-optional-content">
          <div class="ltr-optional-selector">
            <span>当前查看</span>
            <a-select
              v-model="ltrOptionalSimSelected"
              size="small"
              style="width: 280px"
            >
              <a-select-option
                v-for="item in ltrOptionalSimStrategies"
                :key="item.method_key"
                :value="item.method_key"
              >
                {{ item.display_name }}
              </a-select-option>
            </a-select>
          </div>
          <div class="ltr-optional-grid" v-if="ltrOptionalSimSelectedStrategy">
            <div class="ltr-optional-card active">
              <div class="ltr-optional-card-head">
                <strong>{{ ltrOptionalSimSelectedStrategy.display_name }}</strong>
                <a-tag :color="ltrOptionalSimSelectedStrategy.is_default_main_strategy ? 'blue' : 'cyan'">{{ ltrOptionalSimSelectedStrategy.status_label }}</a-tag>
              </div>
              <span>{{ ltrOptionalSimSelectedStrategy.note }}</span>
              <div class="ltr-optional-metrics">
                <div>
                  <small>样本范围</small>
                  <b>{{ ltrOptionalSimSelectedStrategy.sample_scope || '-' }}</b>
                </div>
                <div>
                  <small>费用后历史模拟</small>
                  <b>{{ ltrOptionalSimMetricText(ltrOptionalSimSelectedStrategy, 'fee_tax_adjusted_net_return', 'percent') }}</b>
                </div>
                <div>
                  <small>最大回撤</small>
                  <b>{{ ltrOptionalSimMetricText(ltrOptionalSimSelectedStrategy, 'max_drawdown', 'percent') }}</b>
                </div>
                <div>
                  <small>动作数</small>
                  <b>{{ ltrOptionalSimMetricText(ltrOptionalSimSelectedStrategy, 'action_count', 'integer') }}</b>
                </div>
                <div>
                  <small>换手 proxy</small>
                  <b>{{ ltrOptionalSimMetricText(ltrOptionalSimSelectedStrategy, 'turnover_proxy_by_notional_over_avg_equity', 'number') }}</b>
                </div>
                <div>
                  <small>independent_test 切片</small>
                  <b>{{ ltrOptionalSimSelectedStrategy.oos_interpretation_allowed ? '是' : '否' }}</b>
                </div>
              </div>
              <a-collapse class="ltr-explanation-detail" :bordered="false">
                <a-collapse-panel key="optional-detail" header="查看只读历史模拟明细">
                  <div class="ltr-detail-grid">
                    <span v-for="slice in ltrOptionalSimSelectedStrategy.walk_forward" :key="`${ltrOptionalSimSelectedStrategy.method_key}-${slice.fold_id}`">
                      {{ slice.test_period || slice.fold_id }}：费用后 {{ formatReplayPercent(slice.fee_tax_adjusted_net_return) }}，回撤 {{ formatReplayPercent(slice.max_drawdown) }}，动作 {{ slice.action_count == null ? '-' : slice.action_count }}，换手 {{ formatNumber(slice.turnover_proxy_by_notional_over_avg_equity, 2) }}
                    </span>
                    <span class="ltr-detail-wide">period 数 {{ ltrOptionalSimSelectedStrategy.method_summary && ltrOptionalSimSelectedStrategy.method_summary.period_count }}，正收益 period {{ ltrOptionalSimSelectedStrategy.method_summary && ltrOptionalSimSelectedStrategy.method_summary.positive_period_count }}</span>
                    <small class="ltr-detail-wide">{{ ltrOptionalSimSelectedStrategy.boundary_text }}</small>
                  </div>
                </a-collapse-panel>
              </a-collapse>
            </div>
          </div>
        </div>
        <div v-else class="rank-tech-empty">可选模拟策略暂不可用。</div>
      </section>
      <div class="portfolio-replay-section">
        <div class="rank-tech-panel-head">
          <strong>过去表现</strong>
          <span>{{ portfolioReplayRangeText }}</span>
        </div>
        <div v-if="portfolioReplayExecutionText" class="portfolio-warning-line">{{ portfolioReplayExecutionText }}</div>
        <a-alert
          v-if="portfolioReplayError"
          class="rank-tech-alert"
          type="warning"
          show-icon
          :message="portfolioReplayError"
        />
        <div v-if="runningPortfolioReplay" class="rank-tech-empty">正在计算历史模拟表现...</div>
        <div v-else-if="portfolioReplayComparisonItems.length" class="portfolio-replay-grid">
          <div v-for="item in portfolioReplayComparisonItems" :key="item.variant" class="portfolio-replay-card">
            <strong>{{ portfolioVariantLabel(item.variant) }}</strong>
            <div class="portfolio-metric-row">
              <span>总收益</span>
              <b>{{ formatReplayPercent(item.metrics.totalReturn) }}</b>
            </div>
            <div class="portfolio-metric-row">
              <span>最大回撤</span>
              <b>{{ formatReplayPercent(item.metrics.maxDrawdown) }}</b>
            </div>
            <div class="portfolio-metric-row">
              <span>动作次数</span>
              <b>{{ item.metrics.actionCount == null ? '-' : item.metrics.actionCount }}</b>
            </div>
            <div class="portfolio-metric-row">
              <span>费用税费估算</span>
              <b>{{ formatCompactNumber(item.metrics.feeAndTax) }}</b>
            </div>
            <div class="portfolio-warning-line"><span>位置过滤：</span>{{ portfolioPositionRiskText(item) }}</div>
            <div class="portfolio-warning-line">{{ portfolioReplayWarningText(item) }}</div>
          </div>
        </div>
        <div v-else class="rank-tech-empty">暂无历史模拟表现。</div>
        <div v-if="portfolioReplayStrategyItems.length" class="portfolio-policy-section">
          <div class="rank-tech-panel-head compact-head">
            <strong>策略规则回放</strong>
            <span>历史模拟，不代表未来收益</span>
          </div>
          <div class="portfolio-replay-grid">
            <div v-for="item in portfolioReplayStrategyItems" :key="item.profile.key" class="portfolio-replay-card">
              <strong>{{ item.profile.label }}</strong>
              <small>{{ item.profile.description }}</small>
              <div class="portfolio-metric-row">
                <span>历史收益</span>
                <b>{{ formatReplayPercent(item.metrics.totalReturn) }}</b>
              </div>
              <div class="portfolio-metric-row">
                <span>最大回撤</span>
                <b>{{ formatReplayPercent(item.metrics.maxDrawdown) }}</b>
              </div>
              <div class="portfolio-metric-row">
                <span>动作次数</span>
                <b>{{ item.metrics.actionCount == null ? '-' : item.metrics.actionCount }}</b>
              </div>
              <div class="portfolio-warning-line">{{ portfolioStrategyBrief(item) }}</div>
            </div>
          </div>
        </div>
      </div>
    </a-card>

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


    <a-card v-show="advancedResearchVisible" class="qlib-option-c-card" :bordered="false">
      <template slot="title">
        <div class="card-title-line">
          <span>当前 asof 研究排名</span>
          <div class="readonly-tags">
            <a-tag color="blue">研究排序</a-tag>
            <a-tag color="green">非交易建议</a-tag>
          </div>
        </div>
      </template>
      <div class="qlib-toolbar">
        <a-radio-group v-model="qlibBucket" size="small" @change="handleQlibBucketChange">
          <a-radio-button value="top30">Top 30</a-radio-button>
          <a-radio-button value="top50">Top 50</a-radio-button>
        </a-radio-group>
        <a-button size="small" @click="loadQlibSignals" :loading="loadingQlibSignals">
          <a-icon type="reload" /> 刷新榜单
        </a-button>
        <a-button v-if="selectedQlibRunId" size="small" @click="returnToLatestQlib" :loading="loadingQlibSignals">
          <a-icon type="rollback" /> 回到 latest
        </a-button>
      </div>
      <a-collapse class="advanced-ops-collapse advanced-ops-collapse-contained" :bordered="false">
        <a-collapse-panel key="ops" header="高级只读诊断">
          <div class="advanced-ops-intro">
            <strong>低频维护信息</strong>
            <span>默认折叠；只用于排查数据状态、历史 run 和 dry-run 证据，不触发补数、发布或 latest 切换。</span>
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
      <div class="daily-auto-update-panel" data-testid="tw-stock-daily-auto-update-panel">
        <div class="daily-auto-update-header">
          <div>
            <strong>每日自動更新觀測</strong>
            <span class="muted">DAPR18 no-publish / dry-run observation；只讀觀測 FinMind raw 與 Yahoo/Scrapling qlib 新鮮度。</span>
          </div>
          <a-button size="small" @click="loadDailyAutoUpdateStatus" :loading="loadingDailyAutoUpdateStatus">
            <a-icon type="reload" /> 更新狀態
          </a-button>
        </div>
        <div class="daily-auto-update-tags">
          <a-tag :color="dailyAutoUpdateStatusColor">{{ dailyAutoUpdateData.last_job_status || dailyAutoUpdateData.latest_status || 'no-job' }}</a-tag>
          <a-tag v-if="dailyAutoUpdateFreshWait" color="orange">fresh_data_wait</a-tag>
          <a-tag :color="dailyAutoUpdateData.cron_installed_hint ? 'blue' : 'default'">{{ dailyAutoUpdateCronHintText }}</a-tag>
          <a-tag color="green">orders_enabled=false</a-tag>
          <a-tag color="green">connects_to_broker=false</a-tag>
          <a-tag color="purple">research_signal_not_order=true</a-tag>
        </div>
        <div class="daily-auto-update-grid">
          <span>qlib accepted latest asof <strong>{{ dailyAutoUpdateData.latest_asof || 'unknown' }}</strong></span>
          <span>latest status <strong>{{ dailyAutoUpdateData.latest_status || '-' }}</strong></span>
          <span>latest run_id <strong>{{ dailyAutoUpdateData.latest_run_id || '-' }}</strong></span>
          <span>pending asof <strong>{{ dailyAutoUpdateData.pending_asof || '-' }}</strong></span>
          <span>pending reason <strong>{{ dailyAutoUpdateData.pending_reason || '-' }}</strong></span>
          <span>last job <strong>{{ dailyAutoUpdateData.last_job_status || '-' }}</strong></span>
          <span>started <strong>{{ dailyAutoUpdateData.last_job_started_at || '-' }}</strong></span>
          <span>finished <strong>{{ dailyAutoUpdateData.last_job_finished_at || '-' }}</strong></span>
        </div>
        <div class="daily-auto-update-source-grid">
          <div class="daily-auto-update-source-card">
            <span>FinMind raw</span>
            <strong>{{ dailyAutoUpdateData.finmind_update_status || '-' }}</strong>
            <small>archived_count={{ dailyAutoUpdateData.finmind_archived_count == null ? '-' : dailyAutoUpdateData.finmind_archived_count }}</small>
          </div>
          <div class="daily-auto-update-source-card">
            <span>Yahoo/Scrapling qlib</span>
            <strong>目标 {{ dailyAutoUpdateData.yahoo_target_asof || '-' }}，当前最大日期 {{ dailyAutoUpdateData.yahoo_date_max || '-' }}</strong>
            <small>缺失 {{ dailyAutoUpdateData.yahoo_missing_asof_count == null ? '-' : dailyAutoUpdateData.yahoo_missing_asof_count }} 支。</small>
          </div>
          <div class="daily-auto-update-source-card">
            <span>next retry</span>
            <strong>{{ dailyAutoUpdateData.next_retry_hint || '-' }}</strong>
            <small>{{ dailyAutoUpdateCronExplainText }}</small>
          </div>
          <div class="daily-auto-update-source-card">
            <span>publish gate</span>
            <strong>no-publish / dry-run observation</strong>
            <small>未见 TW_DAPR18_PUBLISH_* 授权证据时，不展示自动发布成功。</small>
          </div>
          <div class="daily-auto-update-source-card">
            <span>research boundary</span>
            <strong>{{ dailyAutoUpdateNoTradingText }}</strong>
            <small>只读狀態，不觸發資料拉取、產物切換或交易。</small>
          </div>
        </div>
        <a-alert
          v-if="dailyAutoUpdateFreshWait"
          class="daily-auto-update-alert"
          type="warning"
          show-icon
          message="same-day data window wait：FinMind raw 数据已更新，但 Yahoo/Scrapling qlib 复权数据尚未到目标日期。系统会继续按定时任务重试 pending asof；当前 qlib accepted latest 不更新是保护状态，不是失败。"
        />
        <a-alert
          v-if="dailyAutoUpdateError"
          class="daily-auto-update-alert"
          type="warning"
          show-icon
          :message="dailyAutoUpdateError"
        />
        <div v-if="dailyAutoUpdateWarnings.length" class="daily-auto-update-warnings">
          <a-tag v-for="warning in dailyAutoUpdateWarnings" :key="`daily-auto-${warning}`" color="orange">{{ warning }}</a-tag>
        </div>
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
            <a-tag v-else color="orange">{{ readonlyWorkbenchMode ? '前端只读，不手动运行 ops' : 'Admin ops required' }}</a-tag>
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
        </a-collapse-panel>
      </a-collapse>
      <a-alert
        v-if="qlibStateNotice"
        class="qlib-state-alert"
        :type="qlibSignalsAccepted ? 'info' : 'warning'"
        show-icon
        :message="qlibStateNotice"
      />
      <div v-if="qlibSignalsAccepted" class="ranking-meta-grid">
        <span>榜单 <strong>{{ rankingBucketText }}</strong></span>
        <span>模型日期 <strong>{{ rankingDateText }}</strong></span>
        <span>行情日期 <strong>{{ rankingRawDateText }}</strong></span>
        <span>榜首 <strong>{{ qlibTopSymbol }}</strong></span>
        <span>提示 <strong>{{ rankingQualityStatus }}</strong></span>
      </div>
      <a-alert
        v-if="rankingDataNote"
        class="ranking-data-note"
        type="info"
        show-icon
        :message="rankingDataNote"
      />
      <div v-if="qlibWarnings.length" class="qlib-warning-list">
        <a-tag v-for="warning in qlibWarnings" :key="warning" color="orange">{{ warning }}</a-tag>
      </div>
      <a-table
        v-if="qlibSignalsAccepted"
        row-key="rank"
        size="small"
        class="qlib-signal-table"
        data-testid="qlib-signal-table"
        :loading="loadingQlibSignals"
        :columns="qlibColumns"
        :data-source="qlibSignals"
        :pagination="{ pageSize: 10 }"
        :custom-row="qlibCustomRow"
      >
        <template slot="symbol" slot-scope="text, row">
          <div class="symbol-name-cell">
            <strong>{{ displayInstrument(row) }}</strong>
            <span class="muted instrument-code">{{ displayStockName(row) }}</span>
          </div>
        </template>
        <template slot="qlib_score" slot-scope="score">
          <span>{{ formatNumber(score, 6) }}</span>
        </template>
        <template slot="latest" slot-scope="text, row">
          <div class="price-date-cell">
            <strong>{{ qlibTrendAvailable(row) ? formatNumber(row.trend.latest_close, 2) : '-' }}</strong>
            <span class="muted">{{ row.trend && row.trend.latest_date ? row.trend.latest_date : '-' }}</span>
          </div>
        </template>
        <template slot="action" slot-scope="text, row">
          <div class="qlib-row-actions">
            <a-button size="small" data-testid="qlib-watch-add" @click.stop="addQlibWatchDraft(row)">
              <a-icon type="eye" /> 加入觀察
            </a-button>
            <a-button size="small" data-testid="qlib-sim-draft" @click.stop="prefillSimDraftFromQlib(row)">
              <a-icon type="wallet" /> 模拟账户说明
            </a-button>
            <a-button
              size="small"
              :loading="runningBacktest && chartSymbol === row.symbol"
              :disabled="runningBacktest && chartSymbol !== row.symbol"
              @click.stop="openQlibReadonlyBacktest(row)"
            >
              <a-icon type="area-chart" /> 回測驗證
            </a-button>
          </div>
        </template>
      </a-table>
      <div v-else-if="!loadingQlibSignals" class="qlib-empty-state">
        {{ qlibEmptyText }}
      </div>
      <div class="qlib-watch-draft" data-testid="qlib-watch-draft">
        <div class="qlib-watch-draft-header">
          <div>
            <strong>研究觀察草稿</strong>
            <span class="muted">觀察草稿僅供人工復盤，不會自動啟用掃描，不會自動建立提醒，不會產生訂單或持倉。</span>
          </div>
          <div class="qlib-watch-draft-actions">
            <a-button size="small" data-testid="qlib-watch-fill-config" :disabled="!qlibWatchDraft.length" @click="fillMonitorConfigFromQlibDraft">
              <a-icon type="form" /> 查看配置草稿
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
        模型分数只用于候选排序和人工复盘，不代表方向判断、胜率或未来收益，也不会产生委托或持仓。
      </div>
    </a-card>

    <a-card v-show="advancedResearchVisible" class="rank-change-card" :bordered="false">
      <template slot="title">
        <div class="card-title-line">
          <span>排名变化</span>
          <div class="readonly-tags">
            <a-tag color="blue">{{ rankingBucketText }}</a-tag>
            <a-tag color="green">只读比较</a-tag>
          </div>
        </div>
      </template>
      <div class="rank-change-toolbar">
        <span>{{ rankChangesDateText }}</span>
        <a-button size="small" @click="loadRankChanges" :loading="loadingRankChanges">
          <a-icon type="reload" /> 更新变化
        </a-button>
      </div>
      <a-alert
        v-if="rankChangesError"
        class="rank-change-alert"
        type="warning"
        show-icon
        :message="rankChangesError"
      />
      <div v-if="rankChangesAccepted" class="rank-change-summary">
        <div class="rank-change-summary-item">
          <span>新进榜</span>
          <strong>{{ rankChangesSummary.entered_count || 0 }}</strong>
        </div>
        <div class="rank-change-summary-item">
          <span>掉出榜</span>
          <strong>{{ rankChangesSummary.exited_count || 0 }}</strong>
        </div>
        <div class="rank-change-summary-item">
          <span>连续在榜</span>
          <strong>{{ rankChangesSummary.stayed_count || 0 }}</strong>
        </div>
        <div class="rank-change-summary-item">
          <span>平均升降</span>
          <strong>{{ rankChangesSummary.avg_rank_delta == null ? '-' : rankChangesSummary.avg_rank_delta }}</strong>
        </div>
      </div>
      <a-tabs v-if="rankChangesAccepted" v-model="rankChangesActiveTab" size="small" class="rank-change-tabs">
        <a-tab-pane key="entered" :tab="`新进榜 ${rankChangesEntered.length}`" />
        <a-tab-pane key="exited" :tab="`掉出榜 ${rankChangesExited.length}`" />
        <a-tab-pane key="stayed" :tab="`持续在榜 ${rankChangesStayed.length}`" />
        <a-tab-pane key="gainers" tab="上升最快" />
        <a-tab-pane key="decliners" tab="下降最快" />
        <a-tab-pane v-if="qlibBucket === 'top30'" key="candidates" tab="候补观察" />
      </a-tabs>
      <a-table
        v-if="rankChangesAccepted"
        row-key="symbol"
        size="small"
        class="rank-change-table"
        :loading="loadingRankChanges"
        :columns="rankChangeColumns"
        :data-source="rankChangesCurrentItems"
        :pagination="{ pageSize: 8 }"
      >
        <template slot="rank_change_symbol" slot-scope="text, row">
          <div class="symbol-name-cell">
            <strong>{{ row.instrument || displayInstrument(row) }}</strong>
            <span class="muted instrument-code">{{ row.name || row.symbol }}</span>
          </div>
        </template>
        <template slot="rank_change_delta" slot-scope="text, row">
          <div class="rank-change-rank-cell">
            <strong>{{ rankChangeRankText(row) }}</strong>
            <span :class="['rank-change-delta', Number(row.rank_delta || 0) >= 0 ? 'positive' : 'negative']">{{ rankChangeDeltaText(row) }}</span>
          </div>
        </template>
        <template slot="rank_change_score" slot-scope="text, row">
          <div class="rank-change-score-cell">
            <strong>{{ row.current_score == null ? '-' : formatNumber(row.current_score, 6) }}</strong>
            <span>{{ row.score_delta == null ? '分数变化 -' : formatSignedNumber(row.score_delta, 6) }}</span>
          </div>
        </template>
        <template slot="rank_change_streak" slot-scope="text, row">
          <span>{{ row.streak_days ? `${row.streak_days} 日` : '-' }}</span>
        </template>
        <template slot="rank_change_label" slot-scope="text, row">
          <a-tag :color="rankChangeLabelColor(row)">{{ row.change_label || '-' }}</a-tag>
        </template>
      </a-table>
      <div v-else-if="!loadingRankChanges" class="qlib-empty-state">尚无可比较的 accepted 排名历史</div>
    </a-card>




    <a-card class="tw-cross-analysis-card" :bordered="false">
      <template v-if="advancedResearchVisible" slot="title">
        <div class="card-title-line">
          <span>台股交叉分析</span>
          <div class="readonly-tags">
            <a-tag color="blue">研究排行</a-tag>
            <a-tag color="green">观察名单</a-tag>
            <a-tag color="purple">不是交易建议</a-tag>
          </div>
        </div>
      </template>
      <div v-show="advancedResearchVisible">
      <div class="cross-analysis-toolbar">
        <a-radio-group v-model="crossAnalysisBucket" size="small" @change="handleCrossAnalysisBucketChange">
          <a-radio-button value="top30">Top30</a-radio-button>
          <a-radio-button value="top50">Top50</a-radio-button>
          <a-radio-button value="all">All</a-radio-button>
        </a-radio-group>
        <a-select v-model="crossAnalysisCategory" size="small" style="width: 220px">
          <a-select-option value="all">全部分组</a-select-option>
          <a-select-option v-for="category in crossAnalysisCategories" :key="category" :value="category">{{ crossCategoryLabel(category) }}</a-select-option>
        </a-select>
        <a-button size="small" @click="loadCrossAnalysis" :loading="loadingCrossAnalysis">
          <a-icon type="reload" /> 更新交叉分析
        </a-button>
      </div>
      <div class="cross-analysis-summary">
        <div class="cross-summary-item">
          <span>模型 / 行情日期</span>
          <strong>{{ crossModelRawDateText }}</strong>
        </div>
        <div class="cross-summary-item">
          <span>当前筛选</span>
          <strong>{{ crossAnalysisBucketLabel }} / {{ crossAnalysisCategoryLabel }}</strong>
        </div>
        <div class="cross-summary-item">
          <span>研究分组</span>
          <strong>{{ crossCategorySummaryText }}</strong>
        </div>
        <div class="cross-summary-item">
          <span>QuantDinger 状态</span>
          <strong>{{ crossTrendSummaryText }}</strong>
        </div>
      </div>
      <a-collapse class="advanced-ops-collapse compact" :bordered="false">
        <a-collapse-panel key="basis" header="查看数据口径">
          <div class="cross-basis-note">
            <span>{{ crossBasisNote }}</span>
            <span>模型分数来自 Yahoo adjusted 研究信号；趋势和日线来自本地 raw 行情。交叉分析只帮助人工复盘，不触发补数、委托或持仓。</span>
          </div>
          <div v-if="crossFreshnessWarnings.length" class="qlib-warning-list">
            <a-tag v-for="warning in crossFreshnessWarnings" :key="`cross-fresh-${warning}`" color="orange">{{ qualityWarningLabel(warning) }}</a-tag>
          </div>
        </a-collapse-panel>
      </a-collapse>
      </div>
      <div id="daov-section-agent" class="tw-stock-agent-panel">
        <div class="agent-panel-header">
          <div>
            <strong>策略解释助手</strong>
            <span class="muted">基于 Agent DailyAgentPromptArtifact latest，解释候选、排名、模拟账户状态和数据新鲜度。</span>
          </div>
          <div class="readonly-tags">
            <a-tag color="blue">只读解释</a-tag>
            <a-tag :color="agentModeColor">{{ agentModeText }}</a-tag>
            <a-tag v-if="agentBlocked" color="red">blocked</a-tag>
          </div>
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
            placeholder="输入策略解释问题，例如：为什么模拟账户不能应用？"
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
          message="该问题已被研究边界阻断；本面板只展示策略解释。"
        />
        <div v-if="agentAnswer" class="agent-answer-box">
          <strong>回答</strong>
          <p>{{ agentAnswer }}</p>
        </div>
        <div class="agent-disclaimer">{{ agentResearchDisclaimer }}</div>
        <div v-if="agentItems.length" class="agent-item-list">
          <div v-for="item in agentItems" :key="`${item.symbol}-${item.qlib_rank || item.cross_category || 'agent'}`" class="agent-item">
            <strong>{{ item.symbol }}</strong>
            <span>排名 {{ item.qlib_rank == null ? '-' : item.qlib_rank }}</span>
            <span>分数 {{ item.qlib_score == null ? '-' : formatNumber(item.qlib_score, 6) }}</span>
            <span>{{ item.human_action || '人工复盘' }}</span>
          </div>
        </div>
        <div v-else-if="agentResponse" class="agent-empty-state">本次回答没有附带项目列表。</div>
        <a-collapse v-if="agentResponse" class="agent-detail-collapse" :bordered="false">
          <a-collapse-panel key="agent-detail" header="查看回答来源与边界">
            <div class="agent-context-grid">
              <span>signal_asof <strong>{{ agentSignalAsof }}</strong></span>
              <span>target_date <strong>{{ agentTargetDate }}</strong></span>
              <span>checksum <strong>{{ agentChecksumText }}</strong></span>
              <span>状态 / 模式 <strong>{{ agentFreshnessStatus }} / {{ agentModeText }}</strong></span>
            </div>
            <div v-if="agentCitations.length" class="agent-citations">
              <strong>引用来源</strong>
              <a-tag v-for="citation in agentCitations" :key="citation" color="blue">{{ citation }}</a-tag>
            </div>
            <div v-if="agentWarnings.length" class="agent-warning-list">
              <strong>提示</strong>
              <a-tag v-for="warning in agentWarnings" :key="warning" color="orange">{{ qualityWarningLabel(warning) }}</a-tag>
            </div>
            <div v-if="agentSkills.length" class="agent-skill-list">
              <strong>调用能力</strong>
              <a-tag v-for="skill in agentSkills" :key="`${skill.name}-${skill.status}`" color="purple">{{ skill.title || skill.name }} · {{ skill.status || skill.mode }}</a-tag>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </div>
      <div v-show="advancedResearchVisible">
      <div v-if="crossAnalysisAccepted" class="qlib-meta-grid">
        <span>模型日期 <strong>{{ crossAnalysisQlib.asof || '-' }}</strong></span>
        <span>行情日期 <strong>{{ crossRawDateRangeText }}</strong></span>
        <span>标的数量 <strong>{{ filteredCrossAnalysisItems.length }}</strong></span>
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
          <div class="symbol-name-cell">
            <strong>{{ displayInstrument(row) }}</strong>
            <span class="muted">{{ displayStockName(row) }}</span>
          </div>
        </template>
        <template slot="cross_score" slot-scope="text, row">
          <span>{{ formatNumber(row.qlib && row.qlib.score, 6) }}</span>
        </template>
        <template slot="cross_trend" slot-scope="text, row">
          <div class="cross-trend-cell">
            <a-tag :color="crossTrendColor(row)">{{ crossTrendDisplayLabel(row) }}</a-tag>
            <span>分数 {{ row.quantdinger && row.quantdinger.trend_score == null ? '-' : formatNumber(row.quantdinger && row.quantdinger.trend_score, 2) }}</span>
            <span v-if="row.positionRisk || (row.technical && row.technical.positionRisk)">位置 {{ positionRiskLabel(row) }}</span>
            <small>{{ row.quantdinger && row.quantdinger.latest_date ? row.quantdinger.latest_date : '-' }}</small>
          </div>
        </template>
        <template slot="cross_category" slot-scope="text, row">
          <a-tag :color="crossCategoryColor(row.cross && row.cross.category)">{{ crossCategoryLabel(row.cross && row.cross.category) }}</a-tag>
        </template>
        <template slot="cross_alignment" slot-scope="text, row">
          <a-tag :color="crossAlignmentColor(row.cross && row.cross.alignment)">{{ row.cross && row.cross.alignment }}</a-tag>
        </template>
        <template slot="cross_summary" slot-scope="text, row">
          <div class="cross-summary-cell">
            <strong>{{ crossPriorityLabel(row.cross && row.cross.priority) }}</strong>
            <span>{{ row.cross && row.cross.summary ? row.cross.summary : crossActionLabel(row.cross && row.cross.human_action) }}</span>
          </div>
        </template>
        <template slot="cross_basis" slot-scope="text, row">
          <div class="cross-basis-cell">
            <a-tag :color="crossBasisColor(row.data_basis && row.data_basis.data_basis_status)">{{ crossBasisLabel(row.data_basis && row.data_basis.data_basis_status) }}</a-tag>
            <span>{{ crossQualityBrief(row) }}</span>
            <small>{{ crossDateGapLabel(row.data_basis && row.data_basis.date_gap_days) }}</small>
          </div>
        </template>
        <template slot="cross_sim_draft" slot-scope="text, row">
          <a-button
            size="small"
            data-testid="cross-sim-draft"
            :disabled="!canPrefillSimDraftFromCross(row)"
            @click.stop="prefillSimDraftFromCross(row)"
          >
            <a-icon type="wallet" /> 模拟账户说明
          </a-button>
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
          <span>综合分组 <strong>{{ crossCategoryLabel(selectedCrossAnalysisDetail.item.cross && selectedCrossAnalysisDetail.item.cross.category) }}</strong></span>
          <span>复盘提示 <strong>{{ crossActionLabel(selectedCrossAnalysisDetail.item.cross && selectedCrossAnalysisDetail.item.cross.human_action) }}</strong></span>
          <span>qlib 排名 <strong>{{ selectedCrossAnalysisDetail.item.qlib && selectedCrossAnalysisDetail.item.qlib.rank }}</strong></span>
          <span>QuantDinger 趋势 <strong>{{ crossTrendDisplayLabel(selectedCrossAnalysisDetail.item) }}</strong></span>
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
            <a-select v-model="crossReviewForm.decision_status" size="small" style="width: 160px" :disabled="readonlyWorkbenchMode">
              <a-select-option value="pending">pending</a-select-option>
              <a-select-option value="watching">watching</a-select-option>
              <a-select-option value="reviewed">reviewed</a-select-option>
              <a-select-option value="ignored">ignored</a-select-option>
              <a-select-option value="data_issue">data_issue</a-select-option>
            </a-select>
            <a-input v-model="crossReviewForm.user_note" size="small" placeholder="人工复盘备注" :disabled="readonlyWorkbenchMode" />
            <a-tag v-if="readonlyWorkbenchMode" color="blue">只读查看，不保存复盘</a-tag>
            <a-button v-else size="small" type="primary" :loading="savingCrossReview" @click="saveCrossAnalysisReview">保存复盘</a-button>
            <a-button size="small" @click="openCrossAnalysisHistoricalSimulation" :loading="runningBacktest">查看资金曲线</a-button>
            <a-button size="small" type="primary" ghost :loading="crossBacktestValidation.loading" @click="runCrossHistoricalValidation">
              <a-icon type="experiment" /> 多策略验证
            </a-button>
          </div>
          <div class="cross-review-note">多策略验证会比较多个内置日线策略，按综合稳健评分选择较优模板；只用于模拟复盘，不是收益承诺，也不是实盘指令。</div>
          <a-alert v-if="crossReviewError" class="cross-review-alert" type="warning" :message="crossReviewError" show-icon />
          <a-alert v-if="crossReviewNotice" class="cross-review-alert" type="info" :message="crossReviewNotice" show-icon />
          <div class="cross-backtest-validation">
            <div class="cross-validation-header">
              <strong>回测验证分析</strong>
              <a-tag :color="crossValidationStateColor">{{ crossValidationStateText }}</a-tag>
            </div>
            <a-alert
              v-if="crossBacktestValidation.error"
              class="cross-review-alert"
              type="warning"
              show-icon
              :message="crossBacktestValidation.error"
            />
            <div v-if="crossBacktestValidation.best" class="cross-validation-best">
              <div>
                <span>较优策略</span>
                <strong>{{ crossBacktestValidation.best.strategyName }}</strong>
              </div>
              <div>
                <span>总收益</span>
                <strong>{{ formatSignedPercentFromNumber(crossBacktestValidation.best.totalReturn) }}</strong>
              </div>
              <div>
                <span>最大回撤</span>
                <strong>{{ formatSignedPercentFromNumber(crossBacktestValidation.best.maxDrawdown) }}</strong>
              </div>
              <div>
                <span>当前 asof 模拟动作</span>
                <strong>{{ crossBacktestValidation.actionLabel }}</strong>
              </div>
            </div>
            <div v-if="crossBacktestValidation.reason" class="cross-validation-reason">{{ crossBacktestValidation.reason }}</div>
            <div v-if="crossBacktestValidation.results.length" class="cross-validation-list">
              <div v-for="item in crossBacktestValidation.results" :key="item.strategyId" class="cross-validation-item">
                <strong>{{ item.strategyName }}</strong>
                <span>收益 {{ formatSignedPercentFromNumber(item.totalReturn) }}</span>
                <span>回撤 {{ formatSignedPercentFromNumber(item.maxDrawdown) }}</span>
                <span>胜率 {{ formatSignedPercentFromNumber(item.winRate) }}</span>
                <span>交易 {{ item.totalTrades == null ? '-' : item.totalTrades }}</span>
                <a-tag :color="item.ok ? 'blue' : 'orange'">{{ item.ok ? '完成' : '不可用' }}</a-tag>
              </div>
            </div>
            <div v-else-if="!crossBacktestValidation.loading" class="cross-validation-empty">选择一只股票后点击“多策略验证”。</div>
          </div>
        </div>
      </div>
      <div class="qlib-footnote">
        数据口径差异：qlib 使用 Yahoo adjusted 模型信号；QuantDinger 使用 raw 日线趋势。交叉分析只用于人工复盘和观察名单，不调用 qlib ops；复盘仅保存状态和备注，查看资金曲线和多策略验证都只做只读历史模拟。
      </div>
      </div>
    </a-card>

    <a-row v-show="advancedResearchVisible" :gutter="16" class="content-row">
      <a-col :xs="24" :xl="15">
        <a-card :bordered="false">
          <template slot="title">
            <div class="card-title-line">
              <span>日線 K 線 / 走勢</span>
              <a-tag color="blue">TWStock 1D</a-tag>
            </div>
          </template>
          <div class="chart-toolbar">
            <a-radio-group v-model="chartSymbolSource" size="small" @change="handleChartSourceChange">
              <a-radio-button value="top30">Top30</a-radio-button>
              <a-radio-button value="top50">Top50</a-radio-button>
              <a-radio-button value="custom">输入代码</a-radio-button>
            </a-radio-group>
            <a-select
              v-if="chartSymbolSource !== 'custom'"
              v-model="chartSymbol"
              size="small"
              show-search
              option-filter-prop="children"
              :filter-option="filterChartSymbolOption"
              :loading="loadingChartSymbols"
              style="width: 220px"
              @change="handleChartSymbolChange"
            >
              <a-select-option v-for="item in chartSymbolOptions" :key="item.symbol" :value="item.symbol">
                {{ item.label }}
              </a-select-option>
            </a-select>
            <a-input-search
              v-else
              v-model="chartSymbolInput"
              size="small"
              placeholder="输入台股代码，如 2357 / TW6290"
              enter-button="查看"
              style="width: 260px"
              @search="handleManualChartSymbolSearch"
            />
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
          <div class="selected-symbol-panel" v-if="chartSymbol">
            <div class="selected-symbol-main">
              <strong>{{ selectedChartSymbolTitle }}</strong>
              <template v-if="selectedTrendItem">
                <a-tag :color="trendTagColor(selectedTrendItem)">{{ selectedTrendItem.trend && selectedTrendItem.trend.label }}</a-tag>
                <span>Score {{ selectedTrendItem.trend && selectedTrendItem.trend.score }}</span>
              </template>
              <a-tag v-else color="blue">K 线查看</a-tag>
            </div>
            <div class="selected-symbol-stats">
              <template v-if="selectedTrendItem">
                <span>5D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_5d) }}</span>
                <span>20D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_20d) }}</span>
                <span>60D {{ formatPercent(selectedTrendItem.returns && selectedTrendItem.returns.ret_60d) }}</span>
                <span>Vol {{ formatPercent(selectedTrendItem.risk && selectedTrendItem.risk.volatility_20d_annualized) }}</span>
                <span>量比 {{ formatNumber(selectedTrendItem.volume && selectedTrendItem.volume.ratio_to_avg20, 2) }}</span>
              </template>
              <span v-if="latestPriceBar">最新 {{ latestPriceBar.date }} · C {{ formatNumber(latestPriceBar.close, 2) }}</span>
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
          <div class="chart-footnote chart-footnote-actions">
            <span>日線 K 線來自只讀行情接口；非盤中即時行情，僅供人工復盤，不產生任何委託。</span>
            <a-button size="small" ghost :loading="loadingSimTradeMarkers" @click="loadSimTradeMarkers">
              <a-icon type="flag" /> 加载模拟成交标记
            </a-button>
            <span v-if="chartSimTradeMarkers.length">模拟成交标记 {{ chartSimTradeMarkers.length }} 笔，仅来自模拟账户成交记录。</span>
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

    <a-collapse v-show="advancedResearchVisible" id="daov-section-maintenance" class="monitor-tools-collapse" :bordered="false">
      <a-collapse-panel key="monitor-tools" header="高级维护工具与提醒记录（默认折叠，只读）">
        <div class="monitor-tools-actions">
          <a-button size="small" @click="refreshMonitorReadonly" :loading="scanning">
            <a-icon type="reload" /> 刷新监控状态
          </a-button>
        </div>
    <a-row :gutter="16" class="content-row">
      <a-col :xs="24" :xl="15">
        <a-card title="趋势列表" :bordered="false">
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
          <a-select :value="row.decision_status || 'pending'" size="small" style="width: 116px" :disabled="readonlyWorkbenchMode" @change="status => updateAlertStatus(row, status)">
            <a-select-option value="pending">pending</a-select-option>
            <a-select-option value="watch">watch</a-select-option>
            <a-select-option value="ignored">ignored</a-select-option>
            <a-select-option value="acted">acted</a-select-option>
          </a-select>
        </template>
      </a-table>
    </a-card>
      </a-collapse-panel>
    </a-collapse>

    <a-drawer title="監控配置（只读）" :visible="configDrawerVisible" width="420" data-testid="monitor-config-drawer" @close="configDrawerVisible = false">
      <a-form layout="vertical">
        <a-form-item label="Name">
          <a-input v-model="configForm.name" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Symbols">
          <a-textarea v-model="configForm.symbolsText" data-testid="monitor-config-symbols" :rows="4" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Limit bars">
          <a-input-number v-model="configForm.limit_bars" :min="20" :max="500" style="width: 100%" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Refresh interval sec">
          <a-input-number v-model="configForm.refresh_interval_sec" :min="0" :max="86400" style="width: 100%" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Score change threshold">
          <a-input-number v-model="configForm.score_change_threshold" :min="0" :max="100" style="width: 100%" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Enabled">
          <a-switch v-model="configForm.enabled" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
        <a-form-item label="Notes">
          <a-textarea v-model="configForm.notes" :rows="3" :disabled="readonlyWorkbenchMode" />
        </a-form-item>
      </a-form>
      <div class="drawer-actions">
        <a-alert v-if="readonlyWorkbenchMode" type="info" show-icon message="当前策略工作台只读展示配置；不在前端保存监控配置。" />
        <a-button @click="configDrawerVisible = false">关闭</a-button>
        <a-button v-if="!readonlyWorkbenchMode" type="primary" @click="saveConfig" :loading="savingConfig">保存</a-button>
      </div>
    </a-drawer>
  </div>
</template>

<script>
import moment from 'moment'
import ReadonlyStrategySnapshotPanel from './components/ReadonlyStrategySnapshotPanel.vue'
import ReadonlyReplayWindowPanel from './components/ReadonlyReplayWindowPanel.vue'
import ReadonlyModelStrategyComparisonPanel from './components/ReadonlyModelStrategyComparisonPanel.vue'
import PaperPortfolioPanel from './components/PaperPortfolioPanel.vue'
import ReadonlyShadowExposurePanel from './components/ReadonlyShadowExposurePanel.vue'
import TradingAgentsReadonlyPanel from './components/TradingAgentsReadonlyPanel.vue'
import { useAgentContext } from './composables/useAgentContext'
import { useReadonlyReplay } from './composables/useReadonlyReplay'
import { useDailyOpsStatus } from './composables/useDailyOpsStatus'
import { useSignalContext } from './composables/useSignalContext'
// getTwStockAgentContext and simpleChatTwStockAgent are delegated by useAgentContext to keep the page boundary readonly.
import {
  getTwStockTrends,
  getTwStockLTRReadonlyExplanation,
  getTwStockReadonlyStrategySnapshot,
  getTwStockReadonlyShadowExposure,
  getTwStockTradingAgentsReadonlyAnalysisLatest,
  getTwStockPhaseYZProductizationStatus,
  getTwStockReadonlyModelStrategyComparison,
  getTwStockLTROptionalSimStrategies,
  getTwStockMonitorConfig,
  getTwStockAlerts,
  getTwStockScanLogs,
  getTwStockHistory,
  getTwStockKline,
  getTwStockBacktestTemplates,
  getLatestQlibOptionCSignals,
  getQlibOptionCHealth,
  getQlibOptionCRuns,
  getQlibOptionCRunDetail,
  getQlibOptionCRankChanges,
  getQlibOptionCJob,
  getQlibOptionCJobLog,
  getQlibOptionCLatestJob,
  getQlibOptionCScheduler,
  getTwStockCrossAnalysisLatest,
  getTwStockCrossAnalysisSymbol,
  getTwStockRankTechCrossLatest,
  getTwStockObservationReplay,
  getTwStockCrossAnalysisReviews,
  getTwStockSimAccounts,
  getTwStockSimTrades
} from '@/api/tw-stock-readonly'
import { runTwStockReadonlyBacktest } from '@/api/tw-stock-action'

export default {
  name: 'TWStockMonitor',
  components: {
    ReadonlyStrategySnapshotPanel,
    ReadonlyReplayWindowPanel,
    ReadonlyModelStrategyComparisonPanel,
    PaperPortfolioPanel,
    ReadonlyShadowExposurePanel,
    TradingAgentsReadonlyPanel
  },
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
      loadingRankChanges: false,
      loadingQlibOps: false,
      runningQlibOpsDryRun: false,
      loadingQlibOpsLog: false,
      loadingDailyAutoUpdateStatus: false,
      loadingReadonlyOpsStatus: false,
      loadingCrossAnalysis: false,
      loadingCrossAnalysisDetail: false,
      loadingRankTechCross: false,
      loadingReadonlyStrategySnapshot: false,
      loadingReadonlyShadowExposure: false,
      loadingTradingAgentsReadonly: false,
      loadingCurrentStrategyContext: false,
      loadingPhaseYZProductization: false,
      loadingReadonlyReplayWindowIndex: false,
      loadingReadonlyReplayWindow: false,
      loadingReadonlyModelStrategyComparison: false,
      loadingLtrReadonlyExplanation: false,
      loadingLtrOptionalSimStrategies: false,
      runningPortfolioReplay: false,
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
      chartSymbolInput: '',
      chartSymbolSource: 'top30',
      loadingChartSymbols: false,
      chartSignalPayloads: { top30: null, top50: null },
      priceChartMode: 'candles',
      chartRangeBars: 120,
      showMovingAverages: true,
      showVolume: true,
      historyItems: [],
      priceCandles: [],
      simTradeMarkers: [],
      loadingSimTradeMarkers: false,
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
      rankChangesPayload: null,
      rankChangesError: '',
      rankChangesActiveTab: 'entered',
      selectedQlibRunId: '',
      qlibOpsJob: null,
      qlibScheduler: {},
      qlibOpsLogStream: 'stdout',
      qlibOpsLogTail: '',
      qlibOpsError: '',
      dailyAutoUpdateStatus: null,
      dailyAutoUpdateError: '',
      readonlyOpsStatus: null,
      readonlyOpsStatusError: '',
      qlibOpsForm: {
        asof: moment('2026-06-01', 'YYYY-MM-DD')
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
      crossBacktestValidation: this.emptyCrossBacktestValidation(),
      crossBacktestValidationCache: {},
      rankTechBucket: 'top30',
      rankTechRange: 'half_year',
      rankTechVariant: 'all',
      rankTechLatestPayload: null,
      rankTechLatestError: '',
      readonlyStrategySnapshotPayload: null,
      readonlyStrategySnapshotError: '',
      readonlyShadowExposurePayload: null,
      readonlyShadowExposureError: '',
      tradingAgentsReadonlyPayload: null,
      tradingAgentsReadonlyError: '',
      currentStrategyContextPayload: null,
      currentStrategyContextError: '',
      phaseYZProductizationPayload: null,
      phaseYZProductizationError: '',
      readonlyReplayWindowIndexPayload: null,
      readonlyReplayWindowIndexError: '',
      readonlyReplayWindowSelectedKey: '2026_ytd',
      readonlyReplayWindowPayload: null,
      readonlyReplayWindowError: '',
      readonlyModelStrategyComparisonPayload: null,
      readonlyModelStrategyComparisonError: '',
      readonlyReplayWindowForm: {
        model_id: 'e4_frozen_qlib_2018_2022',
        strategy_rule: 'top50_exit_one_worst_sell',
        start: moment('2026-01-01', 'YYYY-MM-DD'),
        end: moment('2026-05-07', 'YYYY-MM-DD')
      },
      ltrReadonlyExplanationPayload: null,
      ltrReadonlyExplanationError: '',
      ltrOptionalSimPayload: null,
      ltrOptionalSimError: '',
      ltrOptionalSimSelected: 'phase1c_ltr_simple_daily',
      portfolioReplayPayload: null,
      portfolioReplayError: '',
      agentContext: null,
      agentContextComposable: null,
      readonlyReplayComposable: null,
      dailyOpsComposable: null,
      signalContextComposable: null,
      agentContextError: '',
      agentQuestion: '',
      agentResponse: null,
      agentError: '',
      agentSuggestedQuestions: [
        '当前 asof top30 是哪些？',
        '当前数据新鲜度和口径是什么？'
      ],
      configDrawerVisible: false,
      advancedResearchVisible: false,
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
        { title: '排名', dataIndex: 'rank', width: 80 },
        { title: '标的', dataIndex: 'symbol', scopedSlots: { customRender: 'symbol' }, width: 150 },
        { title: '模型分数', dataIndex: 'qlib_score', scopedSlots: { customRender: 'qlib_score' }, width: 140 },
        { title: '最新价 / 行情日期', dataIndex: 'trend.latest_close', scopedSlots: { customRender: 'latest' }, width: 180 },
        { title: '操作', dataIndex: 'action', scopedSlots: { customRender: 'action' }, width: 330 }
      ],
      rankChangeColumns: [
        { title: '标的', dataIndex: 'symbol', scopedSlots: { customRender: 'rank_change_symbol' }, width: 150 },
        { title: '排名变化', dataIndex: 'rank_delta', scopedSlots: { customRender: 'rank_change_delta' }, width: 150 },
        { title: '模型分数变化', dataIndex: 'score_delta', scopedSlots: { customRender: 'rank_change_score' }, width: 150 },
        { title: '连续在榜', dataIndex: 'streak_days', scopedSlots: { customRender: 'rank_change_streak' }, width: 110 },
        { title: '状态', dataIndex: 'change_label', scopedSlots: { customRender: 'rank_change_label' } }
      ],
      crossAnalysisColumns: [
        { title: '排名', dataIndex: 'qlib.rank', scopedSlots: { customRender: 'cross_rank' }, width: 90 },
        { title: '标的', dataIndex: 'symbol', scopedSlots: { customRender: 'cross_symbol' }, width: 130 },
        { title: 'qlib 模型分数', dataIndex: 'qlib.score', scopedSlots: { customRender: 'cross_score' }, width: 130 },
        { title: 'QuantDinger 趋势', dataIndex: 'quantdinger.trend_label', scopedSlots: { customRender: 'cross_trend' }, width: 190 },
        { title: '综合分组', dataIndex: 'cross.category', scopedSlots: { customRender: 'cross_category' }, width: 160 },
        { title: '综合结论', dataIndex: 'cross.summary', scopedSlots: { customRender: 'cross_summary' } },
        { title: '数据提示', dataIndex: 'data_basis.data_basis_status', scopedSlots: { customRender: 'cross_basis' }, width: 170 },
        { title: '模拟验证', dataIndex: 'cross_sim_draft', scopedSlots: { customRender: 'cross_sim_draft' }, width: 150 }
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
    readonlyWorkbenchMode () {
      return true
    },
    pageRailItems () {
      return [
        { id: 'daov-section-freshness', label: '状态', tone: 'status' },
        { id: 'daov-section-strategy', label: '策略', tone: 'primary' },
        { id: 'daov-section-snapshot', label: '候选', tone: 'primary' },
        { id: 'daov-section-replay', label: '回放', tone: 'primary' },
        { id: 'daov-section-research', label: '排名', tone: 'research' },
        { id: 'daov-section-agent', label: 'Agent', tone: 'agent' },
        { id: 'daov-section-maintenance', label: '诊断', tone: 'muted' }
      ]
    },
    b19ShadowSummary () { return (this.readonlyOpsStatus && this.readonlyOpsStatus.b19r2r_shadow) || {} },
    b19ShadowStatusText () {
      const labels = { NOT_OBSERVED: '尚未观察到运行', NOT_ATTEMPTED: '尚未尝试', READY: '影子信号已就绪', READY_RESEARCH_SHADOW: '影子信号已就绪', BLOCKED: '影子信号阻断' }
      return labels[this.b19ShadowSummary.state] || '尚未观察到运行'
    },
    b19ShadowAsOf () { return this.b19ShadowSummary.asof || '-' },
    b19ShadowLastReadyAsOf () { return this.b19ShadowSummary.last_ready_asof || '-' },
    currentStrategyContext () {
      return (this.currentStrategyContextPayload && this.currentStrategyContextPayload.context) || {}
    },
    currentStrategyRankings () {
      return (this.currentStrategyContextPayload && this.currentStrategyContextPayload.rankings) || {}
    },
    currentStrategyAsofAudit () {
      return (this.currentStrategyContextPayload && this.currentStrategyContextPayload.consistency_audit && this.currentStrategyContextPayload.consistency_audit.asof_alignment) || {}
    },
    currentStrategyContextReady () {
      return this.currentStrategyContextPayload && this.currentStrategyContextPayload.ok === true
    },
    currentStrategyContextStatusText () {
      if (this.currentStrategyContextError) return '读取异常'
      if (!this.currentStrategyContextPayload) return '待读取'
      if (this.currentStrategyAsofAudit.status === 'pass') return '一致'
      return '部分来源待同步'
    },
    currentStrategyContextTagColor () {
      if (this.currentStrategyContextError) return 'red'
      if (!this.currentStrategyContextPayload) return 'default'
      return this.currentStrategyAsofAudit.status === 'pass' ? 'green' : 'orange'
    },
    currentStrategyContextBrief () {
      if (!this.currentStrategyContextPayload) return '统一读取 Model A（E4 Qlib）信号，供候选观察、策略快照和只读回放共用。'
      return `当前只读 strategy snapshot latest asof ${this.freshnessSnapshotDateText}，目标交易日 ${this.currentContextTargetDate}。`
    },
    currentStrategyContextMismatchText () {
      const audit = this.currentStrategyAsofAudit
      const checks = Array.isArray(audit.checks) ? audit.checks : []
      const mismatches = checks.filter(item => item && item.status !== 'pass')
      if (!mismatches.length) return ''
      return mismatches.map(item => `${item.name}: ${item.actual_asof || item.details || '-'}，期望 ${item.expected_signal_asof || this.currentContextSignalAsOf}`).join('；')
    },
    currentContextSignalAsOf () {
      return this.currentStrategyContext.signal_asof || '-'
    },
    currentContextTargetDate () {
      return this.currentStrategyContext.target_date || '-'
    },
    currentContextModelText () {
      const model = this.currentStrategyContext.default_model_id || '-'
      const display = this.currentStrategyContext.display_model_id || ''
      return display && display !== model ? `${display}` : model
    },
    currentContextStrategyRule () {
      return this.currentStrategyContext.strategy_rule || '-'
    },
    currentContextLTRCoverageText () {
      return '未启用'
    },
    currentContextSnapshotCoverageText () {
      const rows = Array.isArray(this.currentStrategyRankings.qlib_top50) ? this.currentStrategyRankings.qlib_top50 : []
      return `${rows.length}/50`
    },
    currentContextQlibCoverageText () {
      const top50 = Array.isArray(this.currentStrategyRankings.qlib_top50) ? this.currentStrategyRankings.qlib_top50.length : 0
      const top150 = Array.isArray(this.currentStrategyRankings.qlib_top150) ? this.currentStrategyRankings.qlib_top150.length : 0
      return `${top50}/50 · ${top150}/150`
    },
    currentContextLTRTopSymbol () {
      const qlibRows = Array.isArray(this.currentStrategyRankings.qlib_top50) ? this.currentStrategyRankings.qlib_top50 : []
      return qlibRows.length ? (qlibRows[0].instrument || qlibRows[0].symbol || '-') : '-'
    },
    currentContextMode () {
      return this.currentStrategyContext.context_mode || 'model_a_only'
    },
    workbenchContextModeText () {
      if (this.currentContextMode === 'model_a_only') return 'Model-A-only 候选模式'
      if (this.currentContextMode === 'candidate_only_snapshot') return 'Model-A-only 候选快照'
      return '历史 LTR 参考模式'
    },
    workbenchModelOptions () {
      const map = new Map()
      const add = (id, label) => {
        if (!id || map.has(id)) return
        map.set(id, { model_id: id, display_name: label || this.shortModelLabel(id) })
      }
      add(this.currentStrategyContext.default_model_id, this.shortModelLabel(this.currentStrategyContext.default_model_id))
      return Array.from(map.values())
    },
    workbenchSelectedModelId () {
      const preset = this.readonlyReplayWindowSelectedPreset || {}
      return preset.model_id || this.currentStrategyContext.default_model_id || ''
    },
    workbenchStrategyOptions () {
      const map = new Map()
      const add = (id, label) => {
        if (!id || map.has(id)) return
        map.set(id, { strategy_id: id, display_name: label || this.strategyDisplayName(id) })
      }
      add(this.currentContextStrategyRule, this.strategyDisplayName(this.currentContextStrategyRule))
      return Array.from(map.values())
    },
    workbenchSelectedStrategyId () {
      return this.currentContextStrategyRule
    },
    workbenchSelectionResultText () {
      const optional = this.ltrOptionalSimSelectedStrategy || {}
      const optionalReturn = optional.metrics && optional.metrics.fee_tax_adjusted_net_return != null ? this.formatReplayPercent(optional.metrics.fee_tax_adjusted_net_return) : '-'
      return `回放净收益 ${this.readonlyReplayWindowNetReturnText}；可选策略历史模拟 ${optionalReturn}。`
    },
    phaseYZProductizationPending () {
      const payload = this.phaseYZProductizationPayload || {}
      return payload.execution_price_status === 'execution_price_unavailable' || payload.paper_apply_allowed === false
    },
    phaseYZProductizationTagColor () { return this.phaseYZProductizationPending ? 'orange' : 'green' },
    phaseYZProductizationStateText () { return this.phaseYZProductizationPending ? 'execution_price_unavailable' : 'ready' },
    phaseYZPaperApplyDisabled () {
      const payload = this.phaseYZProductizationPayload || {}
      return payload.paper_apply_allowed !== true
    },
    phaseYZSignalAsOf () { return (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.signal_asof) || '-' },
    phaseYZExecutionPriceMode () { return (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.execution_price_mode) || 'next_open' },
    phaseYZExecutionPriceMessage () { return (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.execution_price_message) || '成交口径：次一交易日开盘价。行情暂不可用，等待下一轮数据更新。' },
    phaseYZTargetNextTradingDay () {
      const readiness = (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.execution_price_readiness) || {}
      return readiness.target_next_trading_day || '-'
    },
    phaseYZModelNames () {
      const models = (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.models) || []
      return (models[0] && models[0].model_id) || 'e4_frozen_qlib_2018_2022 (Model A)'
    },
    phaseYZStrategyNames () {
      const strategies = (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.production_strategies) || []
      return strategies.map(item => item.strategy_rule_id).join(' / ') || 'top50_exit_one_worst_sell'
    },
    phaseYZSelectedStrategy () { return (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.selected_strategy_rule_id) || 'top50_exit_one_worst_sell' },
    phaseYZPaperApplyText () { return this.phaseYZPaperApplyDisabled ? '等待 next_open 成交价' : '可应用到模拟账户' },
    phaseYZBlockedReasonText () { return (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.paper_apply_blocked_reason) || '-' },
    workbenchOverviewStatusText () {
      if (this.currentStrategyContextError || this.phaseYZProductizationError) return '需复核'
      if (!this.currentStrategyContextPayload && !this.phaseYZProductizationPayload) return '待读取'
      return '只读查看'
    },
    workbenchOverviewStatusColor () {
      if (this.currentStrategyContextError || this.phaseYZProductizationError) return 'red'
      if (!this.currentStrategyContextPayload && !this.phaseYZProductizationPayload) return 'default'
      return 'blue'
    },
    workbenchTargetTradingDay () {
      return this.phaseYZTargetNextTradingDay !== '-' ? this.phaseYZTargetNextTradingDay : this.currentContextTargetDate
    },
    workbenchOverviewStatusMessage () {
      if (this.currentStrategyContextError) return this.currentStrategyContextError
      if (this.phaseYZProductizationError) return this.phaseYZProductizationError
      if (this.phaseYZPaperApplyDisabled) return '模拟链路仍在等待目标交易日开盘价；本页面只读，不写入模拟账户。'
      return `只读策略信息已就绪，snapshot asof ${this.freshnessSnapshotDateText}；本页面不写入模拟账户。`
    },
    workbenchBaseModelId () {
      const models = (this.phaseYZProductizationPayload && this.phaseYZProductizationPayload.models) || []
      return (models[0] && models[0].model_id) || this.currentStrategyContext.default_model_id || '-'
    },
    workbenchTreatmentModelId () {
      return '- (Model B 仅历史参考)'
    },
    workbenchModelDisplayText () {
      const text = this.currentContextModelText || ''
      if (!text || text === '-') return 'E4 Qlib Model A'
      return text.toLowerCase().includes('e4_frozen_qlib') ? 'E4 Qlib Model A' : text
    },
    workbenchStrategyDisplayText () {
      const rule = this.currentContextStrategyRule || this.phaseYZSelectedStrategy || ''
      if (rule === 'candidate_only_no_strategy_replay') return '候选快照，无同日策略回放'
      if (rule === 'top50_exit_one_worst_sell') return '跌出 Top50 后最多替换一支'
      return rule || '-'
    },
    workbenchCandidateCoverageText () {
      if (this.currentContextMode === 'candidate_only_snapshot') return `Model A Snapshot ${this.currentContextSnapshotCoverageText}`
      return `Model A Qlib ${this.currentContextQlibCoverageText}`
    },
    workbenchPaperApplyStatusText () {
      return '只读查看'
    },
    workbenchPaperApplyReasonText () {
      return '此工作台不写入模拟账户'
    },
    workbenchRankingSource () {
      return this.currentStrategyContext.ranking_source || '-'
    },
    workbenchCandidateBoundary () {
      return this.currentStrategyContext.candidate_boundary || '-'
    },

    unreadCount () {
      return this.alertItems.filter(item => !item.is_read).length
    },
    healthClass () {
      return `health-${this.scanHealth.status || 'unknown'}`
    },
    chartSymbolOptions () {
      const source = this.chartSymbolSource === 'top50' ? 'top50' : 'top30'
      const payload = this.chartSignalPayloads[source] || {}
      const rows = Array.isArray(payload.signals) ? payload.signals : []
      const seen = new Set()
      const out = []
      rows.forEach(row => {
        const symbol = this.normalizeTwSymbol(row && row.symbol)
        if (!symbol || seen.has(symbol)) return
        seen.add(symbol)
        const name = row.name || row.symbol_name || ''
        const rank = row.rank ? `#${row.rank}` : ''
        out.push({
          symbol,
          name,
          rank,
          label: [symbol, name, rank].filter(Boolean).join(' · ')
        })
      })
      ;(this.trendItems || []).forEach(item => {
        const symbol = this.normalizeTwSymbol(item && item.symbol)
        if (!symbol || seen.has(symbol)) return
        seen.add(symbol)
        out.push({ symbol, name: '', rank: '监控', label: `${symbol} · 监控` })
      })
      const current = this.normalizeTwSymbol(this.chartSymbol)
      if (current && !seen.has(current)) out.unshift({ symbol: current, name: '', rank: '当前', label: `${current} · 当前` })
      return out
    },
    chartSymbols () {
      const symbols = this.chartSymbolOptions.map(item => item.symbol).filter(Boolean)
      if (symbols.length) return symbols
      const trendSymbols = this.trendItems.filter(item => item && item.ok !== false).map(item => item.symbol).filter(Boolean)
      return trendSymbols.length ? trendSymbols : (this.config.symbols || [])
    },
    selectedTrendItem () {
      return this.trendItems.find(item => this.normalizeTwSymbol(item.symbol) === this.normalizeTwSymbol(this.chartSymbol)) || null
    },
    selectedChartSymbolTitle () {
      const option = this.chartSymbolOptions.find(item => item.symbol === this.normalizeTwSymbol(this.chartSymbol))
      if (option && option.name) return `${option.symbol} ${option.name}`
      return this.chartSymbol || '-'
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
    chartSimTradeMarkers () {
      const symbol = this.normalizeTwSymbol(this.chartSymbol)
      if (!symbol) return []
      const dates = new Set(this.displayedPriceCandles.map(item => item.date).filter(Boolean))
      return this.simTradeMarkers
        .filter(item => this.normalizeTwSymbol(item.symbol) === symbol)
        .filter(item => !dates.size || dates.has(String(item.price_date || '').slice(0, 10)))
        .map(item => ({
          date: String(item.price_date || '').slice(0, 10),
          price: Number(item.price || 0),
          side: item.side,
          quantity: item.quantity,
          source_type: item.source_type || 'manual'
        }))
        .filter(item => item.date && Number.isFinite(item.price) && item.price > 0)
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
    crossValidationStateText () {
      if (this.crossBacktestValidation.loading) return '验证中'
      if (this.crossBacktestValidation.error) return '验证失败'
      if (this.crossBacktestValidation.best) return this.crossBacktestValidation.actionLabel || '已验证'
      return '未验证'
    },
    crossValidationStateColor () {
      const type = this.crossBacktestValidation.actionType
      if (this.crossBacktestValidation.loading) return 'blue'
      if (this.crossBacktestValidation.error || type === 'error') return 'red'
      if (type === 'sim_buy_candidate') return 'green'
      if (type === 'avoid_new_buy' || type === 'risk_review_if_holding') return 'orange'
      if (type === 'manual_review') return 'purple'
      if (type === 'watch_only') return 'blue'
      return 'default'
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
    dailyAutoUpdateData () {
      return this.dailyAutoUpdateStatus || {}
    },
    readonlyOpsData () {
      return this.readonlyOpsStatus || {}
    },
    readonlyOpsProviderRawLatest () {
      return this.readonlyOpsData.provider_raw_latest || {}
    },
    readonlyOpsQlibAcceptedLatest () {
      return this.readonlyOpsData.qlib_accepted_latest || {}
    },
    readonlyOpsControlledSignalLatest () {
      return this.readonlyOpsData.controlled_signal_latest || {}
    },
    readonlyOpsSnapshotLatest () {
      return this.readonlyOpsData.readonly_strategy_snapshot_latest || {}
    },
    readonlyOpsAgentPromptLatest () {
      return this.readonlyOpsData.agent_prompt_latest || {}
    },
    readonlyOpsNaturalCronJob () {
      return this.readonlyOpsData.latest_natural_cron_job || {}
    },
    readonlyOpsDapr18EvidenceJob () {
      return this.readonlyOpsData.latest_dapr18_evidence_job || {}
    },
    readonlyOpsDapr18Controls () {
      return this.readonlyOpsData.dapr18_controls || {}
    },
    readonlyOpsProtectedPointers () {
      return this.readonlyOpsData.protected_pointers || {}
    },
    readonlyOpsNaturalCronText () {
      const job = this.readonlyOpsNaturalCronJob
      const status = job.status || job.daily_chain_state || this.dailyAutoUpdateData.last_job_status || 'no-job'
      const asof = job.asof || this.dailyAutoUpdateData.pending_asof || this.dailyAutoUpdateData.latest_asof || '-'
      return `${status} · asof ${asof}`
    },
    readonlyOpsNaturalCronDetailText () {
      const job = this.readonlyOpsNaturalCronJob
      const jobId = job.job_id || '-'
      const state = job.daily_chain_state || '-'
      return `job_id=${jobId} / chain=${state}`
    },
    readonlyOpsDapr18EvidenceText () {
      const job = this.readonlyOpsDapr18EvidenceJob
      const status = job.dapr18_status || job.readiness_state || job.job_status || 'missing'
      const asof = job.asof || '-'
      return `${status} · asof ${asof}`
    },
    readonlyOpsDapr18EvidenceDetailText () {
      const job = this.readonlyOpsDapr18EvidenceJob
      return `job_id=${job.job_id || '-'} / evidence_dir=${job.evidence_dir || '-'}`
    },
    readonlyOpsDapr18FlagsText () {
      const controls = this.readonlyOpsDapr18Controls
      const dryRun = controls.dry_run === true ? 'dry-run on' : controls.dry_run === false ? 'dry-run off' : 'dry-run unknown'
      const publishFlags = [
        controls.publish_controlled_signal_latest,
        controls.publish_readonly_snapshot_latest,
        controls.publish_agent_prompt_latest
      ]
      const publishAllOff = publishFlags.every(value => value === false)
      const publishAnyOn = publishFlags.some(value => value === true)
      const publish = publishAllOff ? 'publish off' : publishAnyOn ? 'publish partially on' : 'publish unknown'
      return `${dryRun} / ${publish}`
    },
    readonlyOpsDapr18PointerText () {
      const controls = this.readonlyOpsDapr18Controls
      const protectedPointers = this.readonlyOpsProtectedPointers
      return `latest_pointer_write_performed=${String(controls.latest_pointer_write_performed === true)} / protected_pointers_all_unchanged=${String(protectedPointers.all_unchanged)}`
    },
    readonlyOpsBlockerText () {
      const blocker = (this.readonlyOpsNaturalCronJob.blocker || {})
      const status = blocker.status || this.readonlyOpsDapr18EvidenceJob.readiness_state || this.readonlyOpsNaturalCronJob.daily_chain_state || '-'
      const reason = blocker.reason || (Array.isArray(blocker.blockers) && blocker.blockers.length ? blocker.blockers.join(', ') : '')
      return reason ? `${status}: ${reason}` : status
    },
    readonlyOpsNextActionHint () {
      return this.readonlyOpsData.next_action_hint || this.dailyAutoUpdateData.next_retry_hint || '当前只读状态可查看；无需从前端执行写入动作。'
    },
    dailyAutoUpdateFreshWait () {
      const status = this.readonlyOpsNaturalCronJob.status || this.readonlyOpsNaturalCronJob.daily_chain_state
      return this.dailyAutoUpdateData.fresh_data_wait === true || status === 'today_data_window_wait' || status === 'fresh_data_wait'
    },
    dailyAutoUpdateWarnings () {
      const warnings = this.dailyAutoUpdateData.warnings
      const readonlyWarnings = this.readonlyOpsData.warnings
      return Array.from(new Set([]
        .concat(Array.isArray(readonlyWarnings) ? readonlyWarnings : [])
        .concat(Array.isArray(warnings) ? warnings : [])
        .filter(Boolean)))
    },
    dailyAutoUpdateTradingFlags () {
      return this.readonlyOpsData.trading || this.dailyAutoUpdateData.trading || {}
    },
    dailyAutoUpdateStatusColor () {
      const status = this.readonlyOpsNaturalCronJob.status || this.readonlyOpsNaturalCronJob.daily_chain_state || this.dailyAutoUpdateData.last_job_status || this.dailyAutoUpdateData.latest_status
      if (status === 'daily_auto_update_passed' || status === 'already_up_to_date' || status === 'accepted') return 'green'
      if (status === 'fresh_data_wait' || status === 'today_data_window_wait') return 'orange'
      if (status === 'provider_publish_failed' || status === 'accepted_latest_failed') return 'red'
      return 'default'
    },
    dailyAutoUpdateCronHintText () {
      if (this.readonlyOpsNaturalCronJob.job_id) return 'natural cron evidence'
      return this.dailyAutoUpdateData.cron_installed_hint ? 'auto schedule hint detected' : 'no schedule hint'
    },
    dailyAutoUpdateCronExplainText () {
      if (this.readonlyOpsNaturalCronJob.job_id) return '最近自然 cron job 来自 DAOV1 readonly-status；只展示 evidence，不手动运行。'
      return this.dailyAutoUpdateData.cron_installed_hint
        ? '检测到自动更新计划配置或日志，系统会继续按配置重试。'
        : '未检测到自动更新计划配置或日志，请检查 cron/systemd 安装。'
    },
    dailyAutoUpdateNoTradingText () {
      const flags = this.dailyAutoUpdateTradingFlags
      return `orders_enabled=${String(flags.orders_enabled === true)} / connects_to_broker=${String(flags.connects_to_broker === true)} / research_signal_not_order=${String(flags.research_signal_not_order === true)}`
    },
    freshnessRawDateText () {
      const raw = this.readonlyOpsProviderRawLatest
      if (raw.source_max_date) return raw.source_max_date
      if (raw.asof) return raw.asof
      const data = this.dailyAutoUpdateData || {}
      if (data.raw_latest_asof) return data.raw_latest_asof
      if (data.provider_raw_latest_asof) return data.provider_raw_latest_asof
      if (data.yahoo_date_max) return data.yahoo_date_max
      if (data.finmind_latest_asof) return data.finmind_latest_asof
      const rawMax = this.crossFreshnessQuant && this.crossFreshnessQuant.latest_date_max
      if (rawMax) return rawMax
      const healthData = this.qlibHealth && this.qlibHealth.dataAvailability
      if (healthData && (healthData.latest_date_max || healthData.raw_latest_asof)) return healthData.latest_date_max || healthData.raw_latest_asof
      if (this.rankingRawDateText && this.rankingRawDateText !== '-') {
        const parts = String(this.rankingRawDateText).split('~').map(item => item.trim()).filter(Boolean)
        return parts.length ? parts[parts.length - 1] : this.rankingRawDateText
      }
      return 'unknown'
    },
    freshnessRawSourceText () {
      const raw = this.readonlyOpsProviderRawLatest
      if (raw.source || raw.raw_status) return `${raw.source || 'provider/raw evidence'} · ${raw.raw_status || 'readonly'}`
      const data = this.dailyAutoUpdateData || {}
      if (data.raw_latest_asof || data.provider_raw_latest_asof || data.yahoo_date_max || data.finmind_latest_asof) return 'provider/raw evidence'
      if (this.crossFreshnessQuant && this.crossFreshnessQuant.source) return this.crossFreshnessQuant.source
      const healthData = this.qlibHealth && this.qlibHealth.dataAvailability
      if (healthData && (healthData.latest_date_max || healthData.raw_latest_asof)) return 'qlib health raw/trading data'
      if (this.rankingRawDateText && this.rankingRawDateText !== '-') return '本地日线行情'
      return 'unknown provider/raw latest'
    },
    freshnessAcceptedDateText () {
      return this.readonlyOpsQlibAcceptedLatest.asof || this.dailyAutoUpdateData.latest_asof || (this.qlibPayload && this.qlibPayload.asof) || (this.qlibHealthLatest && this.qlibHealthLatest.asof) || 'unknown'
    },
    freshnessAcceptedSourceText () {
      const accepted = this.readonlyOpsQlibAcceptedLatest
      const status = accepted.status || this.dailyAutoUpdateData.latest_status || (this.qlibPayload && this.qlibPayload.status) || this.qlibHealthStatusText || 'unknown'
      const run = accepted.run_id || this.dailyAutoUpdateData.latest_run_id || (this.qlibHealthLatest && this.qlibHealthLatest.run_id) || ''
      if (accepted.asof) return run ? `${status} · ${run}` : status
      if (this.dailyAutoUpdateData.latest_asof) return run ? `${status} · ${run}` : status
      if (this.qlibPayload && this.qlibPayload.asof) return run ? `qlib signal payload · ${run}` : 'qlib signal payload'
      if (this.qlibHealthLatest && this.qlibHealthLatest.asof) return run ? `qlib health fallback · ${run}` : 'qlib health fallback'
      return 'unknown qlib accepted latest'
    },
    freshnessControlledSignalDateText () {
      const controlled = this.readonlyOpsControlledSignalLatest
      return controlled.signal_asof || controlled.asof || 'unknown'
    },
    freshnessControlledSignalSourceText () {
      const controlled = this.readonlyOpsControlledSignalLatest
      if (controlled.run_id || controlled.evidence_path) return `run_id=${controlled.run_id || '-'} / evidence_path=${controlled.evidence_path || '-'}`
      return 'unknown controlled signal latest'
    },
    freshnessSnapshotDateText () {
      const readonlyLatest = this.readonlyOpsSnapshotLatest
      if (readonlyLatest.signal_asof || readonlyLatest.target_date) return readonlyLatest.signal_asof || readonlyLatest.target_date
      const snapshot = this.readonlyStrategySnapshot || {}
      const manifest = this.readonlyStrategyManifest || {}
      const context = this.currentStrategyContext || {}
      const source = this.currentStrategyContextPayload || {}
      return snapshot.signal_asof || snapshot.asof || manifest.signal_asof || manifest.asof || context.snapshot_signal_asof || context.readonly_snapshot_asof || source.snapshot_asof || source.signal_asof || (this.currentContextSignalAsOf !== '-' ? this.currentContextSignalAsOf : '') || 'unknown'
    },
    freshnessSnapshotSourceText () {
      const readonlyLatest = this.readonlyOpsSnapshotLatest
      if (readonlyLatest.evidence_path || readonlyLatest.checksum) return `readonly-status · ${readonlyLatest.evidence_path || readonlyLatest.checksum}`
      const snapshot = this.readonlyStrategySnapshot || {}
      const manifest = this.readonlyStrategyManifest || {}
      if (snapshot.signal_asof || snapshot.asof || manifest.signal_asof || manifest.asof) return '候选名单/只读策略快照'
      if (this.currentContextSignalAsOf !== '-') return 'derived/fallback from current-strategy-context'
      return 'unknown readonly snapshot latest'
    },
    freshnessAgentDateText () {
      const agentLatest = this.readonlyOpsAgentPromptLatest
      if (agentLatest.signal_asof || agentLatest.target_date) return agentLatest.signal_asof || agentLatest.target_date
      return this.agentSignalAsof && this.agentSignalAsof !== '-' ? this.agentSignalAsof : 'unknown'
    },
    freshnessAgentSourceText () {
      const agentLatest = this.readonlyOpsAgentPromptLatest
      if (agentLatest.evidence_path || agentLatest.checksum) return `readonly-status · ${agentLatest.evidence_path || agentLatest.checksum}`
      if (this.agentResponseDigest.signal_asof || this.agentResponseDigest.qlib_asof) return 'simple-chat context_digest'
      if (this.agentContextQlib.asof) return 'Agent prompt context'
      if (this.crossAnalysisQlib && this.crossAnalysisQlib.asof) return 'derived/fallback from cross-analysis'
      return 'unknown Agent prompt latest'
    },
    freshnessAcceptedLagging () {
      return this.dateLooksAhead(this.freshnessRawDateText, this.freshnessAcceptedDateText)
    },
    freshnessSnapshotLagging () {
      return this.dateLooksAhead(this.freshnessAcceptedDateText, this.freshnessSnapshotDateText)
    },
    freshnessAgentLagging () {
      return this.dateLooksAhead(this.freshnessAcceptedDateText, this.freshnessAgentDateText)
    },
    freshnessAnyLagging () {
      return this.freshnessAcceptedLagging || this.freshnessSnapshotLagging || this.freshnessAgentLagging
    },
    freshnessOverviewStatusText () {
      if (this.readonlyOpsStatusError || this.dailyAutoUpdateError || this.qlibHealthError || this.currentStrategyContextError || this.readonlyStrategySnapshotError || this.agentContextError) return '需复核'
      if (this.readonlyOpsData.status === 'readonly_status_available' && (this.dailyAutoUpdateFreshWait || this.readonlyOpsBlockerText !== '-')) return '等待或阻塞'
      if (this.qlibHealthFreshness && this.qlibHealthFreshness.stale) return '策略待推进'
      if (this.freshnessAnyLagging) return '日期不一致'
      if (this.freshnessAcceptedDateText === 'unknown' && this.freshnessRawDateText === 'unknown') return 'degraded'
      return '链路一致'
    },
    freshnessOverviewStatusColor () {
      if (this.freshnessOverviewStatusText === '链路一致') return 'green'
      if (this.freshnessOverviewStatusText === 'degraded') return 'default'
      if (this.freshnessOverviewStatusText === '需复核') return 'red'
      return 'orange'
    },
    freshnessOverviewMessage () {
      if (this.readonlyOpsStatusError) return this.readonlyOpsStatusError
      if (this.dailyAutoUpdateError) return this.dailyAutoUpdateError
      if (this.qlibHealthError) return this.qlibHealthError
      if (this.readonlyOpsData.status === 'readonly_status_available') return this.readonlyOpsNextActionHint
      if (this.freshnessAcceptedLagging) {
        return `provider/raw latest 已到 ${this.freshnessRawDateText}，qlib accepted latest 仍为 ${this.freshnessAcceptedDateText}；等待桥接验证通过后才会推进。`
      }
      if (this.freshnessSnapshotLagging || this.freshnessAgentLagging) {
        return `qlib accepted latest 为 ${this.freshnessAcceptedDateText}，readonly snapshot 或 Agent prompt latest 尚未对齐。`
      }
      if (this.qlibHealthFreshness && this.qlibHealthFreshness.stale) {
        return `qlib accepted latest 已标记 stale：${this.qlibHealthFreshness.stale_reason || 'asof_age_gt_threshold'}。`
      }
      return `首屏使用 readonly snapshot latest ${this.freshnessSnapshotDateText}；qlib accepted latest ${this.freshnessAcceptedDateText} 与 Agent prompt latest ${this.freshnessAgentDateText} 分开展示。`
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
    qlibOpsPermissionAllowed () {
      const user = this.readLocalJson('User-Info') || {}
      const role = user.role && typeof user.role === 'object' ? user.role : { id: user.role }
      const roleId = role.id || user.role || user.role_id || user.roleId
      const permissions = []
        .concat(Array.isArray(user.permissions) ? user.permissions : [])
        .concat(Array.isArray(role.permissions) ? role.permissions : [])
        .concat(Array.isArray(role.permissionList) ? role.permissionList : [])
      return roleId === 'admin' || permissions.includes('tw_stock_qlib_ops') || permissions.includes('tw_stock_ops')
    },
    qlibOpsCanTrigger () {
      return !this.readonlyWorkbenchMode && this.qlibOpsPermissionAllowed
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
    rankingBucketText () {
      const bucket = (this.qlibPayload && this.qlibPayload.bucket) || this.qlibBucket || 'top30'
      return String(bucket).replace('top', 'Top ')
    },
    rankingDateText () {
      return (this.qlibPayload && this.qlibPayload.asof) || (this.qlibHealthLatest && this.qlibHealthLatest.asof) || '-'
    },
    rankingRawDateText () {
      const dates = this.qlibSignals
        .map(row => row && row.trend && row.trend.latest_date)
        .filter(Boolean)
      if (!dates.length) return '-'
      const sorted = Array.from(new Set(dates)).sort()
      return sorted.length === 1 ? sorted[0] : `${sorted[0]} ~ ${sorted[sorted.length - 1]}`
    },
    qlibTopRow () {
      return this.qlibSignals.length ? this.qlibSignals[0] : null
    },
    qlibTopSymbol () {
      return (this.qlibTopRow && this.qlibTopRow.symbol) || '-'
    },
    qlibTopScoreText () {
      if (!this.qlibTopRow || this.qlibTopRow.qlib_score == null) return 'score -'
      return 'score ' + this.formatNumber(this.qlibTopRow.qlib_score, 6)
    },
    qlibTrendUnknownCount () {
      return this.qlibSignals.filter(row => {
        const trend = row && row.trend
        return !trend || trend.ok === false || trend.trend_label === 'unknown'
      }).length
    },
    qlibQualityWarningCounts () {
      const counts = {}
      this.qlibSignals.forEach(row => {
        const warnings = row && row.trend && Array.isArray(row.trend.quality_warnings) ? row.trend.quality_warnings : []
        warnings.forEach(warning => {
          const key = String(warning || '').trim()
          if (key) counts[key] = (counts[key] || 0) + 1
        })
      })
      return counts
    },
    rankingQualityStatus () {
      if (!this.qlibSignals.length) return '-'
      const warningTotal = Object.values(this.qlibQualityWarningCounts).reduce((sum, count) => sum + Number(count || 0), 0)
      if (warningTotal || this.qlibTrendUnknownCount) return '需留意'
      return '正常'
    },
    rankingQualityBrief () {
      if (!this.qlibSignals.length) return '尚未载入'
      const warnings = Object.entries(this.qlibQualityWarningCounts)
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .slice(0, 1)
      if (warnings.length) return this.qualityWarningLabel(warnings[0][0]) + ' x ' + String(warnings[0][1])
      if (this.qlibTrendUnknownCount) return 'trend unknown x ' + String(this.qlibTrendUnknownCount)
      return '无集中警告'
    },
    rankingDataNote () {
      if (!this.qlibSignals.length) return ''
      const notes = []
      if (this.qlibTrendUnknownCount >= Math.ceil(this.qlibSignals.length * 0.8)) {
        notes.push('多数标的的趋势标签为 unknown，逐行展示价值不高，已从排名表中隐藏；可在交叉分析或个股详情中查看原始趋势分数。')
      }
      const warnings = Object.entries(this.qlibQualityWarningCounts).sort((a, b) => Number(b[1]) - Number(a[1]))
      if (warnings.length && Number(warnings[0][1]) >= Math.ceil(this.qlibSignals.length * 0.5)) {
        notes.push('主要数据提示为 ' + this.qualityWarningLabel(warnings[0][0]) + '，影响 ' + String(warnings[0][1]) + ' 支，已汇总展示而不是在每行重复。')
      }
      return notes.join(' ')
    },
    rankChangesAccepted () {
      return !!(this.rankChangesPayload && this.rankChangesPayload.ok)
    },
    rankChangesSummary () {
      return (this.rankChangesPayload && this.rankChangesPayload.summary) || {}
    },
    rankChangesDateText () {
      if (!this.rankChangesPayload) return '-'
      return `${this.rankChangesPayload.asof || '-'} vs ${this.rankChangesPayload.previous_asof || '-'}`
    },
    rankChangesEntered () {
      const items = this.rankChangesPayload && this.rankChangesPayload.entered
      return Array.isArray(items) ? items : []
    },
    rankChangesExited () {
      const items = this.rankChangesPayload && this.rankChangesPayload.exited
      return Array.isArray(items) ? items : []
    },
    rankChangesStayed () {
      const items = this.rankChangesPayload && this.rankChangesPayload.stayed
      return Array.isArray(items) ? items : []
    },
    rankChangesGainers () {
      const items = this.rankChangesPayload && this.rankChangesPayload.top_gainers
      return Array.isArray(items) ? items : []
    },
    rankChangesDecliners () {
      const items = this.rankChangesPayload && this.rankChangesPayload.top_decliners
      return Array.isArray(items) ? items : []
    },
    rankChangesCandidates () {
      const items = this.rankChangesPayload && this.rankChangesPayload.watch_candidates
      return Array.isArray(items) ? items : []
    },
    rankChangesCurrentItems () {
      const map = {
        entered: this.rankChangesEntered,
        exited: this.rankChangesExited,
        stayed: this.rankChangesStayed,
        gainers: this.rankChangesGainers,
        decliners: this.rankChangesDecliners,
        candidates: this.rankChangesCandidates
      }
      return map[this.rankChangesActiveTab] || []
    },
    qlibWarnings () {
      const warnings = this.qlibPayload && this.qlibPayload.warnings
      if (!Array.isArray(warnings)) return []
      return warnings.map(this.qualityWarningLabel).filter(Boolean)
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

    readonlyStrategySnapshot () {
      return (this.readonlyStrategySnapshotPayload && this.readonlyStrategySnapshotPayload.snapshot) || {}
    },
    readonlyStrategyManifest () {
      return (this.readonlyStrategySnapshotPayload && this.readonlyStrategySnapshotPayload.manifest) || {}
    },
    readonlyStrategyValidation () {
      return (this.readonlyStrategySnapshotPayload && this.readonlyStrategySnapshotPayload.validation) || {}
    },
    readonlyStrategyChecksum () {
      return (this.readonlyStrategySnapshotPayload && this.readonlyStrategySnapshotPayload.checksum) || {}
    },
    readonlyTopCandidates () {
      const items = this.readonlyStrategySnapshot.top_candidates
      return Array.isArray(items) ? items.slice(0, 10) : []
    },
    readonlyExitCandidates () {
      const items = this.readonlyStrategySnapshot.exit_candidates
      return Array.isArray(items) ? items : []
    },
    readonlyStrategyGatePass () {
      const payload = this.readonlyStrategySnapshotPayload || {}
      return payload.ok === true &&
        payload.readonly_only === true &&
        payload.production_trade_enabled === false &&
        payload.not_order === true &&
        payload.no_order_action === true &&
        payload.not_target_position === true &&
        payload.not_investment_advice === true &&
        this.readonlyStrategyValidation.ok === true &&
        this.readonlyStrategyChecksum.ok === true
    },
    readonlyStrategyStatusText () {
      if (this.readonlyStrategySnapshotError) return '读取异常'
      if (!this.readonlyStrategySnapshotPayload) return '待读取'
      return this.readonlyStrategyGatePass ? '通过' : '需复核'
    },
    readonlyStrategyStatusColor () {
      if (this.readonlyStrategyGatePass) return 'green'
      if (this.readonlyStrategySnapshotError) return 'red'
      return 'orange'
    },
    readonlyStrategyValidationText () {
      const validation = this.readonlyStrategyValidation
      return validation.status || (validation.ok === true ? 'pass' : '-')
    },
    readonlyStrategyChecksumText () {
      const checksum = this.readonlyStrategyChecksum
      if (checksum.ok === true) return 'pass'
      if (checksum.ok === false) return 'fail'
      return '-'
    },
    readonlyStrategySourceManifest () {
      const sources = (this.readonlyStrategySnapshotPayload && this.readonlyStrategySnapshotPayload.sources) || {}
      return sources.manifest || this.readonlyStrategyManifest.snapshot || '-'
    },
    readonlyStrategyFlagText () {
      const payload = this.readonlyStrategySnapshotPayload || {}
      return [
        `readonly=${String(payload.readonly_only === true)}`,
        `production=${String(payload.production_trade_enabled === true)}`
      ].join(' / ')
    },

    readonlyReplayWindowOptions () {
      const items = this.readonlyReplayWindowIndexPayload && this.readonlyReplayWindowIndexPayload.windows
      if (!Array.isArray(items)) return []
      // The active runtime is Model-A-only. Keep Model B replay artifacts
      // available in the backend as research references, but do not expose
      // them as the primary workbench selection.
      const modelA = this.currentStrategyContext.default_model_id || 'e4_frozen_qlib_2018_2022'
      return items.filter(item => !item || !item.model_id || item.model_id === modelA)
    },
    readonlyReplayWindowSelectedPreset () {
      return this.readonlyReplayWindowOptions.find(item => item && item.window_key === this.readonlyReplayWindowSelectedKey) || this.readonlyReplayWindowOptions[0] || null
    },
    readonlyReplayWindowPresetText () {
      const preset = this.readonlyReplayWindowSelectedPreset || {}
      if (preset.window_type === 'generated_readonly') return 'D6 已审计非固定窗口'
      if (preset.window_type === 'fixed_standard') return 'D4 固定标准窗口'
      return '索引窗口'
    },
    readonlyReplayWindowPresetColor () {
      const preset = this.readonlyReplayWindowSelectedPreset || {}
      if (preset.window_type === 'generated_readonly') return 'purple'
      if (preset.window_type === 'fixed_standard') return 'blue'
      return 'default'
    },
    readonlyReplayWindowSummary () {
      return (this.readonlyReplayWindowPayload && this.readonlyReplayWindowPayload.summary) || {}
    },
    readonlyReplayWindowText () {
      const window = (this.readonlyReplayWindowPayload && this.readonlyReplayWindowPayload.window) || {}
      return window.start && window.end ? `${window.start}..${window.end}` : '-'
    },
    readonlyReplayWindowNetReturnText () {
      const summary = this.readonlyReplayWindowSummary || {}
      return summary.fee_tax_adjusted_net_return == null ? '-' : this.formatReplayPercent(summary.fee_tax_adjusted_net_return)
    },
    readonlyReplayWindowChecksumText () {
      const checksum = (this.readonlyReplayWindowPayload && this.readonlyReplayWindowPayload.checksum) || {}
      if (checksum.ok === true) return 'pass'
      if (checksum.ok === false) return 'fail'
      return '-'
    },
    readonlyReplayWindowStatusText () {
      if (this.readonlyReplayWindowError) return '后端拒绝'
      if (!this.readonlyReplayWindowPayload) return '待读取'
      return this.readonlyReplayWindowPayload.ok === true && this.readonlyReplayWindowPayload.readonly_only === true ? '通过' : '需复核'
    },
    readonlyDailyRunRegistryItems () {
      const items = this.readonlyDailyRunRegistryPayload && this.readonlyDailyRunRegistryPayload.items
      return Array.isArray(items) ? items : []
    },
    readonlyDailyRunRegistrySource () {
      const sources = this.readonlyDailyRunRegistryPayload && this.readonlyDailyRunRegistryPayload.sources
      return (sources && sources.run_registry_root) || '-'
    },
    readonlyProviderReadinessStatus () {
      return (this.readonlyProviderReadinessPayload && this.readonlyProviderReadinessPayload.status) || '-'
    },
    readonlyDailyUpdateRunItems () {
      const items = this.readonlyDailyUpdateRunsPayload && this.readonlyDailyUpdateRunsPayload.items
      return Array.isArray(items) ? items : []
    },
    readonlyDailyUpdateLatestRun () {
      const current = this.readonlyDailyUpdateRunPayload
      const latest = this.readonlyDailyUpdateRunItems[0] || null
      if (current && current.run_id) return current
      return latest
    },
    readonlyDailyUpdateRunId () {
      return (this.readonlyDailyUpdateLatestRun && this.readonlyDailyUpdateLatestRun.run_id) || '-'
    },
    readonlyDailyTriggerStatus () {
      if (this.runningReadonlyDailyUpdate) return 'running'
      if (this.loadingReadonlyProviderReadiness || this.loadingReadonlyDailyUpdateRuns || !this.readonlyProviderReadinessPayload) return 'loading'
      const run = this.readonlyDailyUpdateLatestRun || {}
      const readiness = this.readonlyProviderReadinessPayload || {}
      const status = run.status || this.readonlyProviderReadinessStatus
      if (status === 'success' && this.readonlyDailyManualTriggerRunId && run.run_id === this.readonlyDailyManualTriggerRunId) return 'success_after_trigger'
      if (readiness.triggerable === false || status === 'already_latest') return 'already_latest'
      if (status === 'success') return 'already_latest'
      if (status === 'running') return 'running'
      if (status === 'already_latest') return 'already_latest'
      if (status === 'no_new_data') return 'no_data_after_trigger'
      if (status === 'provider_failed') return 'provider_failed_after_trigger'
      if (['validator_failed', 'partial_data_pending', 'deadline_missed_keep_previous_latest', 'selected_model_strategy_unavailable'].includes(status)) return 'failed_after_trigger'
      return 'triggerable'
    },
    readonlyDailyTriggerDisabled () {
      return this.runningReadonlyDailyUpdate || this.readonlyDailyTriggerStatus === 'loading' || this.readonlyDailyTriggerStatus === 'running' || this.readonlyDailyTriggerStatus === 'already_latest'
    },
    readonlyDailyTriggerStateText () {
      const map = {
        already_latest: '已是最新',
        loading: '检查中',
        running: '正在更新',
        triggerable: '可更新',
        no_data_after_trigger: 'current-asof 数据暂不可用',
        success_after_trigger: '只读 dry-run 完成',
        provider_failed_after_trigger: '数据源暂不可用',
        failed_after_trigger: '更新失败'
      }
      return map[this.readonlyDailyTriggerStatus] || '可更新'
    },
    readonlyDailyTriggerTagColor () {
      const map = {
        already_latest: 'green',
        loading: 'default',
        running: 'blue',
        triggerable: 'gold',
        no_data_after_trigger: 'orange',
        success_after_trigger: 'green',
        provider_failed_after_trigger: 'orange',
        failed_after_trigger: 'red'
      }
      return map[this.readonlyDailyTriggerStatus] || 'default'
    },
    readonlyDailyTriggerMessage () {
      const run = this.readonlyDailyUpdateLatestRun || {}
      if (this.readonlyDailyTriggerStatus === 'loading') return '正在检查当前 asof 是否已有只读结果。'
      if (this.readonlyDailyTriggerStatus === 'running') return `正在执行只读 dry-run 观察 / ${run.run_id || '-'}`
      if (this.readonlyDailyTriggerStatus === 'already_latest') return '当前 asof 已有只读结果，继续展示现有只读口径。'
      if (this.readonlyDailyTriggerStatus === 'no_data_after_trigger') return 'current-asof 数据暂不可用，保留旧结果，等待自动重试。'
      if (this.readonlyDailyTriggerStatus === 'success_after_trigger') return `只读 dry-run 观察完成，current asof ${run.target_asof || this.readonlyDailyDataAsOf || '-'}；不表示 latest pointer 已自动推进。`
      if (this.readonlyDailyTriggerStatus === 'provider_failed_after_trigger') {
        if (run.user_message) return run.user_message
        const provider = run.provider_user_status || {}
        return provider.user_message || '外部行情源暂时不可用，旧策略结果已保留，系统会等待下一轮重试。'
      }
      if (this.readonlyDailyTriggerStatus === 'failed_after_trigger') {
        if (run.user_message) return run.user_message
        return '旧结果已保留，可稍后重试。'
      }
      return `数据就绪状态 ${this.readonlyProviderReadinessStatus}；只读 dry-run 完成后展示 current-asof 观察结果，失败或没数据时保留旧结果。`
    },
    readonlyReplayWindowSourceManifest () {
      const sources = (this.readonlyReplayWindowPayload && this.readonlyReplayWindowPayload.sources) || {}
      return sources.readonly_replay_manifest || sources.standard_artifact_index_manifest || '-'
    },
    readonlyReplayWindowIndexManifest () {
      const sources = (this.readonlyReplayWindowPayload && this.readonlyReplayWindowPayload.sources) || {}
      return sources.window_index_manifest || (this.readonlyReplayWindowIndexPayload && this.readonlyReplayWindowIndexPayload.sources && this.readonlyReplayWindowIndexPayload.sources.manifest) || '-'
    },

    ltrReadonlyExplanationMethods () {
      const methods = this.ltrReadonlyExplanationPayload && this.ltrReadonlyExplanationPayload.methods
      return Array.isArray(methods) ? methods : []
    },
    ltrOptionalSimStrategies () {
      const strategies = this.ltrOptionalSimPayload && this.ltrOptionalSimPayload.strategies
      return Array.isArray(strategies) ? strategies : []
    },
    ltrOptionalSimSelectedStrategy () {
      return this.ltrOptionalSimStrategies.find(item => item.method_key === this.ltrOptionalSimSelected) || this.ltrOptionalSimStrategies[0] || null
    },
    ltrOptionalSimBoundaryText () {
      return (this.ltrOptionalSimPayload && this.ltrOptionalSimPayload.boundary_text) || '仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。'
    },
    rankTechAccepted () {
      return !!(this.rankTechLatestPayload && this.rankTechLatestPayload.ok && this.rankTechLatestPayload.status === 'accepted')
    },
    rankTechItems () {
      const items = this.rankTechLatestPayload && this.rankTechLatestPayload.items
      return Array.isArray(items) ? items : []
    },
    rankTechPriorityItems () {
      const priority = {
        new_watch: 1,
        continue_watch: 2,
        risk_review: 3,
        manual_review: 4,
        observe_only: 5,
        data_insufficient: 6
      }
      return this.rankTechItems.slice().sort((a, b) => {
        const ac = a && a.decision && a.decision.code
        const bc = b && b.decision && b.decision.code
        const ar = Number(a && (a.rank || (a.qlib && a.qlib.rank)) || 999)
        const br = Number(b && (b.rank || (b.qlib && b.qlib.rank)) || 999)
        return (priority[ac] || 9) - (priority[bc] || 9) || ar - br
      }).slice(0, 8)
    },
    rankTechStatusText () {
      if (this.rankTechLatestError) return '读取异常'
      if (!this.rankTechLatestPayload) return '待读取'
      if (this.rankTechAccepted) return '已载入'
      return this.rankTechLatestPayload.status || '暂不可用'
    },
    rankTechBucketLabel () {
      return this.rankTechBucket === 'top50' ? 'Top50' : 'Top30'
    },
    rankTechDateText () {
      const qlib = (this.rankTechLatestPayload && this.rankTechLatestPayload.qlib) || {}
      return qlib.asof || this.rankingDateText || '-'
    },
    portfolioReplayComparisonItems () {
      const comparison = (this.portfolioReplayPayload && this.portfolioReplayPayload.comparison) || {}
      return ['qlib_only', 'qlib_plus_trend', 'qlib_plus_trend_indicators', 'qlib_plus_trend_position_risk']
        .filter(variant => this.rankTechVariant === 'all' || this.rankTechVariant === variant)
        .map(variant => ({ variant, payload: comparison[variant] || {}, metrics: (comparison[variant] && comparison[variant].metrics) || {} }))
        .filter(item => item.payload && Object.keys(item.payload).length)
    },
    portfolioReplayStrategyItems () {
      const comparison = (this.portfolioReplayPayload && this.portfolioReplayPayload.strategyComparison) || {}
      const profiles = {
        rank_rotate_top30: { key: 'rank_rotate_top30', label: '跌出 Top30 轮动', description: '10 支上限；持仓跌出 Top30 时卖出排名最低的一支，再从 Top10 最高排名补一支。' },
        rank_rotate_top50: { key: 'rank_rotate_top50', label: '跌出 Top50 轮动', description: '10 支上限；持仓跌出 Top50 时才卖出排名最低的一支，再从 Top10 最高排名补一支。' },
        rank_rotate_top50_adaptive_score: { key: 'rank_rotate_top50_adaptive_score', label: 'Top50 自适应 score', description: '继承 Top50 轮动；正常市况不干预，谨慎/下跌市况只从 qlib score 0.04-0.08 的 Top10 候选补仓。' },
        rank_rotate_top50_adaptive_score_risk_control: { key: 'rank_rotate_top50_adaptive_score_risk_control', label: 'Top50 自适应 score + 风控', description: '继承 Top50 自适应 score；市场谨慎/下跌且组合回撤扩大时暂停补仓。' },
        confirmed_exit: { key: 'confirmed_exit', label: '连续转弱才复盘', description: '10 支上限；不因单日排名波动退出，连续转弱后才做风险复盘。' }
      }
      return ['confirmed_exit', 'rank_rotate_top50_adaptive_score', 'rank_rotate_top50_adaptive_score_risk_control', 'rank_rotate_top50', 'rank_rotate_top30']
        .map(key => ({ key, payload: comparison[key] || {}, profile: (comparison[key] && comparison[key].profile) || profiles[key] || { key, label: key, description: '' }, metrics: (comparison[key] && comparison[key].metrics) || {} }))
        .filter(item => item.payload && Object.keys(item.payload).length)
    },
    portfolioReplayRangeText () {
      const range = this.portfolioReplayDateRange()
      return `${range.startDate || '-'} 至 ${range.endDate || '-'}`
    },
    portfolioReplayExecutionText () {
      const execution = (this.portfolioReplayPayload && this.portfolioReplayPayload.execution) || {}
      return execution.label ? `成交口径：${execution.label}` : ''
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
    crossAnalysisBucketLabel () {
      if (this.crossAnalysisBucket === 'top30') return 'Top30'
      if (this.crossAnalysisBucket === 'top50') return 'Top50'
      return '全部'
    },
    crossAnalysisCategoryLabel () {
      if (this.crossAnalysisCategory === 'all') return '全部分组'
      const labels = {
        focus_watch: '重点观察',
        secondary_watch: '次级观察',
        model_trend_divergence: '模型趋势分歧',
        data_review_required: '需要数据复核',
        trend_unavailable: '趋势不可用',
        model_watch_trend_neutral: '中性观察'
      }
      return labels[this.crossAnalysisCategory] || this.crossAnalysisCategory
    },
    crossFreshnessUserText () {
      const status = this.crossFreshness.status
      if (status === 'fresh') return '正常'
      if (status === 'historical') return '历史数据'
      if (status === 'stale') return '可能延迟'
      if (status === 'blocked') return '暂不可用'
      return '待确认'
    },
    crossModelRawDateText () {
      const model = (this.crossFreshnessQlib && this.crossFreshnessQlib.asof) || (this.crossAnalysisQlib && this.crossAnalysisQlib.asof) || '-'
      return `${model} / ${this.crossRawDateRangeText}`
    },
    crossCategorySummaryText () {
      const counts = this.crossCategoryCounts
      const entries = Object.entries(counts).sort((a, b) => Number(b[1]) - Number(a[1]))
      if (!entries.length) return '-'
      return entries.slice(0, 2).map(([category, count]) => `${this.crossCategoryLabel(category)} ${count}`).join(' / ')
    },
    crossCategoryCounts () {
      const counts = {}
      this.filteredCrossAnalysisItems.forEach(item => {
        const category = (item && item.cross && item.cross.category) || 'uncategorized'
        counts[category] = (counts[category] || 0) + 1
      })
      return counts
    },
    crossTrendSummaryText () {
      const items = this.filteredCrossAnalysisItems
      if (!items.length) return '-'
      const unknown = items.filter(item => this.isUnknownTrend(item && item.quantdinger && item.quantdinger.trend_label)).length
      const unavailable = items.filter(item => item && item.quantdinger && item.quantdinger.ok === false).length
      const scored = items.map(item => Number(item && item.quantdinger && item.quantdinger.trend_score)).filter(Number.isFinite)
      const avg = scored.length ? scored.reduce((sum, value) => sum + value, 0) / scored.length : null
      const shortHistory = items.filter(item => {
        const warnings = item && item.quantdinger && Array.isArray(item.quantdinger.quality_warnings) ? item.quantdinger.quality_warnings : []
        return warnings.includes('short_history_below_60_bars')
      }).length
      if (unavailable === items.length) return '趋势不可用'
      if (shortHistory >= Math.ceil(items.length * 0.8)) return `多数样本不足，均分 ${avg == null ? '-' : this.formatNumber(avg, 1)}`
      if (unknown >= Math.ceil(items.length * 0.8)) return `多为中性/未知，均分 ${avg == null ? '-' : this.formatNumber(avg, 1)}`
      return `已读取 ${items.length} 支，均分 ${avg == null ? '-' : this.formatNumber(avg, 1)}`
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
      return this.agentSignalAsof
    },
    agentSignalAsof () {
      return this.agentResponseDigest.signal_asof || this.agentResponseDigest.qlib_asof || this.agentContextQlib.asof || this.crossAnalysisQlib.asof || '-'
    },
    agentTargetDate () {
      return this.agentResponseDigest.target_date || '-'
    },
    agentChecksumText () {
      const checksum = this.agentResponseDigest.checksum || ''
      return checksum ? checksum.slice(0, 18) + '...' : '-'
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
    agentSkills () {
      const skills = this.agentResponse && this.agentResponse.invoked_skills
      return Array.isArray(skills) ? skills : []
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
    this.loadQlibRuns()
    this.loadQlibScheduler()
    this.refreshAll()
    window.addEventListener('resize', this.redrawCharts)
  },
  beforeDestroy () {
    this.stopAutoRefresh()
    window.removeEventListener('resize', this.redrawCharts)
  },
  methods: {
    emptyCrossBacktestValidation () {
      return {
        symbol: '',
        loading: false,
        error: '',
        results: [],
        best: null,
        actionLabel: '待验证',
        actionType: 'pending',
        reason: ''
      }
    },

    qualityWarningLabel (warning) {
      const key = String(warning || '').trim()
      const labels = {
        short_history_below_60_bars: '历史不足60日',
        target_date_unavailable: '目标日数据未完全到齐',
        run_metadata_missing_research_only_flags_verified_by_latest_and_summary: ''
      }
      return Object.prototype.hasOwnProperty.call(labels, key) ? labels[key] : key
    },
    dateLooksAhead (left, right) {
      const a = this.parseDateOnly(left)
      const b = this.parseDateOnly(right)
      return !!(a && b && a > b)
    },
    parseDateOnly (value) {
      const match = String(value || '').match(/\d{4}-\d{2}-\d{2}/)
      if (!match) return 0
      const parsed = new Date(`${match[0]}T00:00:00Z`).getTime()
      return Number.isFinite(parsed) ? parsed : 0
    },
    displayInstrument (row) {
      const instrument = row && row.instrument ? String(row.instrument).trim().toUpperCase() : ''
      if (instrument) return instrument
      const symbol = row && row.symbol ? String(row.symbol).trim().toUpperCase() : ''
      return symbol ? `TW${symbol.replace(/^TW/, '')}` : '-'
    },
    displayReadonlySymbol (row) {
      const symbol = row && row.symbol ? String(row.symbol).trim().toUpperCase() : ''
      return symbol || '-'
    },
    displayStockName (row) {
      const name = row && (row.name || row.symbol_name || row.stock_name)
      if (name) return String(name).trim()
      return row && row.symbol ? String(row.symbol).trim().toUpperCase() : '-'
    },
    unwrap (response) {
      if (response && Object.prototype.hasOwnProperty.call(response, 'code') && Object.prototype.hasOwnProperty.call(response, 'data')) {
        return response.data
      }
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
    scrollToSection (sectionId) {
      if (!sectionId || typeof document === 'undefined') return
      if (['daov-section-research', 'daov-section-maintenance'].includes(sectionId)) this.advancedResearchVisible = true
      this.$nextTick(() => {
        const element = document.getElementById(sectionId)
        if (!element || typeof element.scrollIntoView !== 'function') return
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    },
    buildReadonlyStatusSummaryPayload () {
      return {
        exported_at: new Date().toISOString(),
        page: 'tw-stock-monitor',
        freshness: {
          overview_status: this.freshnessOverviewStatusText,
          overview_message: this.freshnessOverviewMessage,
          raw_latest: {
            asof: this.freshnessRawDateText,
            source: this.freshnessRawSourceText
          },
          qlib_accepted_latest: {
            asof: this.freshnessAcceptedDateText,
            source: this.freshnessAcceptedSourceText
          },
          controlled_signal_latest: {
            asof: this.freshnessControlledSignalDateText,
            source: this.freshnessControlledSignalSourceText
          },
          readonly_strategy_snapshot_latest: {
            asof: this.freshnessSnapshotDateText,
            source: this.freshnessSnapshotSourceText
          },
          agent_prompt_latest: {
            asof: this.freshnessAgentDateText,
            source: this.freshnessAgentSourceText
          }
        },
        readonly_ops: {
          status: this.readonlyOpsData.status || 'unknown',
          blocker: this.readonlyOpsBlockerText,
          next_action_hint: this.readonlyOpsNextActionHint,
          natural_cron_job: {
            job_id: this.readonlyOpsNaturalCronJob.job_id || null,
            asof: this.readonlyOpsNaturalCronJob.asof || null,
            status: this.readonlyOpsNaturalCronJob.status || null,
            daily_chain_state: this.readonlyOpsNaturalCronJob.daily_chain_state || null
          },
          dapr18_controls: {
            enabled: this.readonlyOpsDapr18Controls.enabled,
            dry_run: this.readonlyOpsDapr18Controls.dry_run,
            build_candidates: this.readonlyOpsDapr18Controls.build_candidates,
            publish_controlled_signal_latest: this.readonlyOpsDapr18Controls.publish_controlled_signal_latest,
            publish_readonly_snapshot_latest: this.readonlyOpsDapr18Controls.publish_readonly_snapshot_latest,
            publish_agent_prompt_latest: this.readonlyOpsDapr18Controls.publish_agent_prompt_latest
          },
          protected_pointers: this.readonlyOpsProtectedPointers
        },
        strategy_context: {
          signal_asof: this.currentContextSignalAsOf,
          target_trading_day: this.workbenchTargetTradingDay,
          model: this.workbenchModelDisplayText,
          strategy: this.workbenchStrategyDisplayText
        },
        ui_status: {
          workbench_status: this.workbenchOverviewStatusText,
          agent_mode: this.agentModeText
        }
      }
    },
    readonlyStatusSummaryText () {
      const payload = this.buildReadonlyStatusSummaryPayload()
      return [
        '台股研究工作台只读摘要',
        `导出时间: ${payload.exported_at}`,
        `数据状态: ${payload.freshness.overview_status}`,
        `状态说明: ${payload.freshness.overview_message}`,
        `Raw/行情: ${payload.freshness.raw_latest.asof}`,
        `qlib accepted latest: ${payload.freshness.qlib_accepted_latest.asof}`,
        `readonly snapshot latest: ${payload.freshness.readonly_strategy_snapshot_latest.asof}`,
        `Agent prompt latest: ${payload.freshness.agent_prompt_latest.asof}`,
        `信号日期: ${payload.strategy_context.signal_asof}`,
        `目标交易日: ${payload.strategy_context.target_trading_day}`,
        `模型: ${payload.strategy_context.model}`,
        `策略: ${payload.strategy_context.strategy}`,
        `blocker: ${payload.readonly_ops.blocker}`,
        `next_action_hint: ${payload.readonly_ops.next_action_hint}`,
        '边界: 只读展示；不拉取数据、不发布 provider、不切换 latest、不连接券商、不产生订单。'
      ].join('\n')
    },
    copyTextToClipboard (text) {
      if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        return navigator.clipboard.writeText(text)
      }
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', 'readonly')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      return Promise.resolve()
    },
    async copyReadonlyStatusSummary () {
      try {
        await this.copyTextToClipboard(this.readonlyStatusSummaryText())
        this.$message.success('已复制当前只读摘要')
      } catch (error) {
        this.$message.warning('复制失败，请改用导出摘要')
      }
    },
    downloadReadonlyStatusSummary () {
      const payload = this.buildReadonlyStatusSummaryPayload()
      const fileDate = payload.exported_at.slice(0, 10)
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `tw-stock-monitor-status-${fileDate}.json`
      link.click()
      window.setTimeout(() => window.URL.revokeObjectURL(url), 1500)
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
    async loadDailyAutoUpdateStatus () {
      this.loadingDailyAutoUpdateStatus = true
      this.dailyAutoUpdateError = ''
      try {
        // Legacy call shape: getTwStockDailyAutoUpdateStatus()
        if (!this.dailyOpsComposable) this.dailyOpsComposable = useDailyOpsStatus()
        const bundle = await this.dailyOpsComposable.load()
        if (bundle.errors && bundle.errors.daily) throw bundle.errors.daily
        const data = this.unwrap(bundle && bundle.daily)
        this.dailyAutoUpdateStatus = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.dailyAutoUpdateStatus = response && response.data ? response.data : null
        this.dailyAutoUpdateError = (response && response.msg) || error.message || '每日自动更新状态读取失败。'
      } finally {
        this.loadingDailyAutoUpdateStatus = false
      }
    },
    async loadReadonlyOpsStatus () {
      this.loadingReadonlyOpsStatus = true
      this.readonlyOpsStatusError = ''
      try {
        // Legacy call shape: getTwStockReadonlyOpsStatus()
        if (!this.dailyOpsComposable) this.dailyOpsComposable = useDailyOpsStatus()
        const bundle = await this.dailyOpsComposable.load()
        if (bundle.errors && bundle.errors.readonly) throw bundle.errors.readonly
        const data = this.unwrap(bundle && bundle.readonly)
        this.readonlyOpsStatus = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyOpsStatus = response && response.data ? response.data : null
        this.readonlyOpsStatusError = (response && response.msg) || error.message || 'DAOV1 readonly-status 读取失败。'
      } finally {
        this.loadingReadonlyOpsStatus = false
      }
    },
    refreshFreshnessOverview () {
      return Promise.all([
        this.loadReadonlyOpsStatus(),
        this.loadDailyAutoUpdateStatus(),
        this.loadQlibHealth(),
        this.loadCurrentStrategyContext(),
        this.loadReadonlyStrategySnapshot(),
        this.loadTwStockAgentContext()
      ])
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
    async loadRankChanges () {
      this.loadingRankChanges = true
      this.rankChangesError = ''
      try {
        const data = this.unwrap(await getQlibOptionCRankChanges({ bucket: this.qlibBucket, lookback: 10 }))
        this.rankChangesPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.rankChangesPayload = response && response.data ? response.data : null
        this.rankChangesError = (response && response.msg) || error.message || '排名变化读取失败'
      } finally {
        this.loadingRankChanges = false
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
      this.loadRankChanges()
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
        // Legacy call shape: getTwStockAgentContext({ maxItems: 10 })
        if (!this.agentContextComposable) this.agentContextComposable = useAgentContext()
        const data = this.unwrap(await this.agentContextComposable.load({ maxItems: 10 }))
        this.agentContext = data || null
        this.refreshAgentSuggestedQuestions(data)
      } catch (error) {
        const response = error && error.response && error.response.data
        this.agentContext = response && response.data ? response.data : null
        this.agentContextError = (response && response.msg) || error.message || '策略解释助手上下文读取失败。'
      } finally {
        this.loadingAgentContext = false
      }
    },
    async loadTradingAgentsReadonlyAnalysis () {
      this.loadingTradingAgentsReadonly = true
      this.tradingAgentsReadonlyError = ''
      try {
        const data = this.unwrap(await getTwStockTradingAgentsReadonlyAnalysisLatest())
        this.tradingAgentsReadonlyPayload = data && data.ok === true ? data : null
        if (!this.tradingAgentsReadonlyPayload) this.tradingAgentsReadonlyError = '外部研究摘要暂不可用。'
      } catch (error) {
        const response = error && error.response && error.response.data
        const data = response && response.data
        this.tradingAgentsReadonlyPayload = data && data.ok === true ? data : null
        this.tradingAgentsReadonlyError = (response && response.msg) || error.message || '外部研究摘要暂不可用。'
      } finally {
        this.loadingTradingAgentsReadonly = false
      }
    },
    handleAgentEnter (event) {
      if (event && event.shiftKey) return
      if (event && typeof event.preventDefault === 'function') event.preventDefault()
      this.askTwStockAgent()
    },
    refreshAgentSuggestedQuestions () {
      this.agentSuggestedQuestions = [
        '当前 asof 策略是什么？',
        '排名第一是谁？',
        '当前 asof 有哪些候选调入？',
        '当前 asof 有哪些调出复核？',
        '2330 当前状态如何？',
        '为什么模拟账户不能应用？',
        '数据新鲜度如何？'
      ].slice(0, 7)
    },
    useAgentSuggestion (question) {
      this.agentQuestion = question
      this.askTwStockAgent(question)
    },
    askAgentFromWorkbench (question) {
      const text = String(question || '为什么模拟账户不能应用？').trim()
      this.agentQuestion = text
      this.askTwStockAgent(text)
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
        // Legacy call shape: simpleChatTwStockAgent({ question, symbol, maxItems })
        if (!this.agentContextComposable) this.agentContextComposable = useAgentContext()
        const data = this.unwrap(await this.agentContextComposable.ask({
          question: text,
          symbol: this.chartSymbol || '',
          maxItems: 10
        }))
        this.agentResponse = data || null
        if (data && data.context_digest && !this.agentContext) {
          this.agentContext = { qlib: { asof: data.context_digest.signal_asof || data.context_digest.qlib_asof, run_id: data.context_digest.qlib_run_id }, freshness: { status: data.context_digest.freshness_status } }
          this.refreshAgentSuggestedQuestions(this.agentContext)
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        this.agentResponse = response && response.data ? response.data : null
        this.agentError = (response && response.msg) || error.message || '策略解释助手回答失败。'
      } finally {
        this.sendingAgentQuestion = false
      }
    },
    portfolioReplayDateRange () {
      const end = new Date()
      const start = new Date(end.getTime())
      if (this.rankTechRange === 'one_year') start.setFullYear(start.getFullYear() - 1)
      else start.setMonth(start.getMonth() - 6)
      return {
        startDate: this.formatDateOnly(start),
        endDate: this.formatDateOnly(end)
      }
    },
    formatDateOnly (date) {
      const parsed = date instanceof Date ? date : new Date(date)
      if (Number.isNaN(parsed.getTime())) return ''
      const year = parsed.getFullYear()
      const month = String(parsed.getMonth() + 1).padStart(2, '0')
      const day = String(parsed.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },
    async loadRankTechCrossLatest () {
      this.loadingRankTechCross = true
      this.rankTechLatestError = ''
      try {
        const maxItems = this.rankTechBucket === 'top50' ? 50 : 30
        const data = this.unwrap(await getTwStockRankTechCrossLatest({
          bucket: this.rankTechBucket,
          limit: 120,
          maxItems,
          includeTechnicalStrategies: true,
          technicalStrategies: ['ma', 'rsi', 'macd', 'bollinger']
        }))
        this.rankTechLatestPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.rankTechLatestPayload = response && response.data ? response.data : null
        this.rankTechLatestError = (response && response.msg) || error.message || '当前 asof 复盘读取失败；历史模拟区仍保持只读。'
      } finally {
        this.loadingRankTechCross = false
      }
    },

    async loadLtrReadonlyExplanation () {
      this.loadingLtrReadonlyExplanation = true
      this.ltrReadonlyExplanationError = ''
      try {
        const data = this.unwrap(await getTwStockLTRReadonlyExplanation())
        this.ltrReadonlyExplanationPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.ltrReadonlyExplanationPayload = response && response.data ? response.data : null
        this.ltrReadonlyExplanationError = (response && response.msg) || error.message || '只读解释暂不可用。'
      } finally {
        this.loadingLtrReadonlyExplanation = false
      }
    },
    async loadLtrOptionalSimStrategies () {
      this.loadingLtrOptionalSimStrategies = true
      this.ltrOptionalSimError = ''
      try {
        const data = this.unwrap(await getTwStockLTROptionalSimStrategies())
        this.ltrOptionalSimPayload = data || null
        if (data && data.default_method_key) this.ltrOptionalSimSelected = data.default_method_key
      } catch (error) {
        const response = error && error.response && error.response.data
        this.ltrOptionalSimPayload = response && response.data ? response.data : null
        this.ltrOptionalSimError = (response && response.msg) || error.message || '可选模拟策略暂不可用。'
      } finally {
        this.loadingLtrOptionalSimStrategies = false
      }
    },
    async loadCurrentStrategyContext () {
      this.loadingCurrentStrategyContext = true
      this.currentStrategyContextError = ''
      try {
        // Legacy call shape: getTwStockCurrentStrategyContext()
        if (!this.signalContextComposable) this.signalContextComposable = useSignalContext()
        const bundle = await this.signalContextComposable.load()
        const data = this.unwrap(bundle && bundle.context)
        this.currentStrategyContextPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.currentStrategyContextPayload = response && response.data ? response.data : null
        this.currentStrategyContextError = (response && response.msg) || error.message || '当前只读策略口径读取失败。'
      } finally {
        this.loadingCurrentStrategyContext = false
      }
    },
    shortModelLabel (modelId) {
      const id = String(modelId || '')
      if (!id) return '-'
      if (id.includes('orthogonal_ltr')) return 'Model B/LTR 历史参考'
      if (id === 'e4_frozen_qlib_2018_2022') return 'E4 Qlib baseline'
      return id
    },
    strategyDisplayName (strategyId) {
      const id = String(strategyId || '')
      if (!id) return '-'
      if (id === 'top50_exit_one_worst_sell') return '跌出 Top50 后最多替换一支'
      if (id === 'candidate_only_no_strategy_replay') return '候选快照，无同日策略回放'
      return id
    },
    handleWorkbenchModelSelect (modelId) {
      const match = this.readonlyReplayWindowOptions.find(item => item && item.model_id === modelId)
      if (match) {
        this.handleReadonlyReplayWindowSelect(match.window_key)
      }
    },
    handleWorkbenchStrategySelect (strategyId) {
      if (this.ltrOptionalSimStrategies.find(item => item.method_key === strategyId)) {
        this.ltrOptionalSimSelected = strategyId
      }
    },
    async loadReadonlyModelStrategyComparison (params = {}) {
      this.loadingReadonlyModelStrategyComparison = true
      this.readonlyModelStrategyComparisonError = ''
      try {
        const query = {}
        ;['model_id', 'strategy_id', 'window_id'].forEach(key => {
          if (params && params[key]) query[key] = params[key]
        })
        const data = this.unwrap(await getTwStockReadonlyModelStrategyComparison(query))
        this.readonlyModelStrategyComparisonPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyModelStrategyComparisonPayload = response && response.data ? response.data : null
        this.readonlyModelStrategyComparisonError = (response && response.msg) || error.message || '模型与策略只读比较暂不可用。'
      } finally {
        this.loadingReadonlyModelStrategyComparison = false
      }
    },
    async loadReadonlyReplayWindowIndex () {
      this.loadingReadonlyReplayWindowIndex = true
      this.readonlyReplayWindowIndexError = ''
      try {
        // Legacy call shape: getTwStockReadonlyReplayWindowIndex()
        if (!this.readonlyReplayComposable) this.readonlyReplayComposable = useReadonlyReplay()
        const data = this.unwrap(await this.readonlyReplayComposable.loadIndex())
        this.readonlyReplayWindowIndexPayload = data || null
        if (!this.readonlyReplayWindowSelectedPreset && this.readonlyReplayWindowOptions.length) {
          this.readonlyReplayWindowSelectedKey = this.readonlyReplayWindowOptions[0].window_key
        }
        if (this.readonlyReplayWindowSelectedPreset) {
          this.applyReadonlyReplayWindowPreset()
          await this.loadReadonlyReplayWindow()
        } else {
          this.readonlyReplayWindowPayload = null
          this.readonlyReplayWindowError = '等待 clean E4 只读回放窗口索引。'
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyReplayWindowIndexPayload = response && response.data ? response.data : null
        this.readonlyReplayWindowIndexError = (response && response.msg) || error.message || '只读回放窗口索引读取失败。'
      } finally {
        this.loadingReadonlyReplayWindowIndex = false
      }
    },
    handleReadonlyReplayWindowSelect (windowKey) {
      this.readonlyReplayWindowSelectedKey = windowKey
      this.$nextTick(() => this.applyReadonlyReplayWindowPreset())
    },
    applyReadonlyReplayWindowPreset () {
      const preset = this.readonlyReplayWindowSelectedPreset
      if (!preset) return false
      this.readonlyReplayWindowForm = {
        model_id: preset.model_id,
        strategy_rule: preset.strategy_rule,
        start: moment(preset.start, 'YYYY-MM-DD'),
        end: moment(preset.end, 'YYYY-MM-DD')
      }
      return true
    },
    async loadReadonlyStrategySnapshot () {
      this.loadingReadonlyStrategySnapshot = true
      this.readonlyStrategySnapshotError = ''
      try {
        const data = this.unwrap(await getTwStockReadonlyStrategySnapshot())
        this.readonlyStrategySnapshotPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyStrategySnapshotPayload = response && response.data ? response.data : null
        this.readonlyStrategySnapshotError = (response && response.msg) || error.message || '策略快照读取失败。'
      } finally {
        this.loadingReadonlyStrategySnapshot = false
      }
    },
    async loadReadonlyShadowExposure () {
      this.loadingReadonlyShadowExposure = true
      this.readonlyShadowExposureError = ''
      try {
        const data = this.unwrap(await getTwStockReadonlyShadowExposure({
          strategy_rule: 'top50_hold_rank_buffer_100',
          include_rows: true
        }))
        this.readonlyShadowExposurePayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyShadowExposurePayload = response && response.data ? response.data : null
        this.readonlyShadowExposureError = (response && response.msg) || error.message || '影子观察读取失败。'
      } finally {
        this.loadingReadonlyShadowExposure = false
      }
    },
    async loadReadonlyReplayWindow () {
      if (!this.readonlyReplayWindowSelectedPreset) {
        this.readonlyReplayWindowPayload = null
        this.readonlyReplayWindowError = '等待 clean E4 只读回放窗口索引。'
        return
      }
      this.applyReadonlyReplayWindowPreset()
      this.loadingReadonlyReplayWindow = true
      this.readonlyReplayWindowError = ''
      const start = this.readonlyReplayWindowForm.start && this.readonlyReplayWindowForm.start.format ? this.readonlyReplayWindowForm.start.format('YYYY-MM-DD') : this.readonlyReplayWindowForm.start
      const end = this.readonlyReplayWindowForm.end && this.readonlyReplayWindowForm.end.format ? this.readonlyReplayWindowForm.end.format('YYYY-MM-DD') : this.readonlyReplayWindowForm.end
      try {
        // Legacy call shape: getTwStockReadonlyReplayWindow({ model_id, strategy_rule, start, end })
        if (!this.readonlyReplayComposable) this.readonlyReplayComposable = useReadonlyReplay()
        const data = this.unwrap(await this.readonlyReplayComposable.loadWindow({
          model_id: this.readonlyReplayWindowForm.model_id,
          strategy_rule: this.readonlyReplayWindowForm.strategy_rule,
          start,
          end
        }))
        this.readonlyReplayWindowPayload = data || null
      } catch (error) {
        const response = error && error.response && error.response.data
        this.readonlyReplayWindowPayload = response && response.data ? response.data : null
        const details = response && response.data && response.data.allowed_replay_start_min ? `；最早允许 ${response.data.allowed_replay_start_min}` : ''
        this.readonlyReplayWindowError = ((response && response.msg) || error.message || '只读回放窗口读取失败。') + details
      } finally {
        this.loadingReadonlyReplayWindow = false
      }
    },
    ltrOptionalSimMetricText (item, key, type) {
      const metric = item && item.metrics && item.metrics[key]
      const values = metric !== null && metric !== undefined && metric !== ''
        ? [metric]
        : ((item && Array.isArray(item.walk_forward) ? item.walk_forward : []).map(row => row && row[key]).filter(value => value !== null && value !== undefined && value !== ''))
      if (!values.length) return '-'
      if (type === 'percent') return values.map(value => this.formatReplayPercent(value)).join(' / ')
      if (type === 'number') return values.map(value => Number.isFinite(Number(value)) ? this.formatNumber(value, 2) : '-').join(' / ')
      return values.map(value => Number.isFinite(Number(value)) ? String(Number(value)) : '-').join(' / ')
    },
    observationReplayReader () {
      return getTwStockObservationReplay
    },
    async loadPortfolioReplay () {
      this.runningPortfolioReplay = true
      this.portfolioReplayError = ''
      try {
        // Legacy call shape: runTwStockPortfolioReplay({ ...range, persist: false })
        const range = this.portfolioReplayDateRange()
        const maxItems = this.rankTechBucket === 'top50' ? 50 : 30
        if (!this.readonlyReplayComposable) this.readonlyReplayComposable = useReadonlyReplay()
        const data = this.unwrap(await this.readonlyReplayComposable.simulate({
          ...range,
          bucket: this.rankTechBucket,
          maxItems,
          variant: this.rankTechVariant,
          initialCash: 1000000,
          maxHoldings: 10,
          lotSize: 10,
          maxAddPerDay: 1,
          maxRiskActionPerDay: 1,
          technicalStrategies: ['ma', 'rsi', 'macd', 'bollinger'],
          executionMode: 'next_trading_day_close',
          persist: false
        }))
        this.portfolioReplayPayload = data || null
        const flags = data && data.trading
        if (data && (data.persist !== false || data.writes_business_db !== false || data.simulation_only !== true || (flags && flags.connects_to_broker === true))) {
          this.portfolioReplayError = '历史模拟返回的只读标记异常，已仅展示状态。'
        }
      } catch (error) {
        const response = error && error.response && error.response.data
        this.portfolioReplayPayload = response && response.data ? response.data : null
        this.portfolioReplayError = (response && response.msg) || error.message || '过去表现暂不可用；当前 asof 复盘可继续查看。'
      } finally {
        this.runningPortfolioReplay = false
      }
    },
    async loadRankTechPortfolioPanel () {
      await Promise.all([this.loadRankTechCrossLatest(), this.loadPortfolioReplay()])
    },
    handleRankTechReplayControlChange () {
      this.rankTechVariant = this.rankTechVariant || 'all'
      this.loadRankTechCrossLatest()
    },
    handlePortfolioReplayControlChange () {
      this.portfolioReplayPayload = null
      this.portfolioReplayError = '参数已变更，请手动运行只读历史模拟。'
    },
    rankTechDecisionLabel (item) {
      const code = item && item.decision && item.decision.code
      const labels = {
        new_watch: '新增观察',
        continue_watch: '继续观察',
        risk_review: '风险复盘',
        manual_review: '人工复核',
        observe_only: '仅观察',
        data_insufficient: '数据不足'
      }
      return labels[code] || '人工复核'
    },
    rankTechDecisionColor (item) {
      const code = item && item.decision && item.decision.code
      if (code === 'new_watch' || code === 'continue_watch') return 'green'
      if (code === 'risk_review') return 'orange'
      if (code === 'manual_review') return 'purple'
      if (code === 'data_insufficient') return 'red'
      return 'blue'
    },
    rankTechActionPayload (item) {
      return (item && item.actionPlan) || {}
    },
    rankTechActionLabel (item) {
      const action = this.rankTechActionPayload(item)
      const labels = {
        simulate_watch: '可模拟观察',
        wait_pullback: '等回调',
        chasing_review: '追高复核',
        continue_observe: '继续观察',
        risk_review: '风险复盘',
        data_review: '资料复核'
      }
      return action.label || labels[action.code] || this.rankTechDecisionLabel(item)
    },
    rankTechActionColor (item) {
      const code = this.rankTechActionPayload(item).code
      if (code === 'simulate_watch') return 'green'
      if (code === 'wait_pullback' || code === 'continue_observe') return 'blue'
      if (code === 'chasing_review') return 'orange'
      if (code === 'risk_review') return 'red'
      if (code === 'data_review') return 'default'
      return this.rankTechDecisionColor(item)
    },
    rankTechTierLabel (value) {
      const rank = Number(value)
      const key = String(value || '').toLowerCase()
      if (key === 'top10' || rank <= 10) return 'Top10'
      if (key === 'top30' || rank <= 30) return 'Top30'
      if (key === 'top50' || rank <= 50) return 'Top50'
      return 'Top50 外'
    },
    rankTechTechnicalLabel (status) {
      const labels = {
        technical_strong: '技术状态偏强',
        technical_neutral: '技术状态中性',
        technical_weak: '技术状态偏弱',
        technical_data_insufficient: '技术数据不足'
      }
      return labels[status] || '技术状态待确认'
    },
    rankTechTrendLabel (label) {
      const value = String(label || '').toLowerCase()
      if (value === 'uptrend' || value === 'rebound') return '偏强'
      if (value === 'downtrend' || value === 'pullback') return '偏弱'
      if (value === 'sideways' || value === 'unknown') return '中性'
      return '数据不足'
    },
    positionRiskPayload (item) {
      return (item && item.positionRisk) || (item && item.technical && item.technical.positionRisk) || {}
    },
    positionRiskLabel (item) {
      const risk = this.positionRiskPayload(item)
      const labels = {
        reasonable: '位置合理',
        elevated: '强势但偏高',
        overheated: '过热谨慎',
        pullback_watch: '回调观察',
        data_insufficient: '数据不足'
      }
      return risk.label || labels[risk.status] || '位置待确认'
    },
    positionRiskColor (item) {
      const status = this.positionRiskPayload(item).status
      if (status === 'reasonable') return 'green'
      if (status === 'elevated' || status === 'pullback_watch') return 'gold'
      if (status === 'overheated') return 'orange'
      return 'default'
    },
    positionRiskReason (item) {
      const risk = this.positionRiskPayload(item)
      return risk.reason || '暂未计算价格位置。'
    },
    rankTechIndicatorSummary (item) {
      const summary = item && item.technical && item.technical.summary
      if (!summary) return '指标：数据不足'
      const supportive = Number(summary.supportive_count || summary.supportive || 0)
      const neutral = Number(summary.neutral_count || summary.neutral || 0)
      const caution = Number(summary.caution_count || summary.caution || 0)
      const insufficient = Number(summary.data_insufficient_count || summary.data_insufficient || 0)
      return `指标：支持 ${supportive} / 中性 ${neutral} / 谨慎 ${caution} / 数据不足 ${insufficient}`
    },
    rankTechQualityBrief (item) {
      const warnings = []
        .concat((item && item.trend && item.trend.warnings) || [])
        .concat((item && item.technical && item.technical.warnings) || [])
        .map(this.qualityWarningLabel)
        .filter(Boolean)
      return warnings.length ? `数据提示：${Array.from(new Set(warnings)).slice(0, 2).join(' / ')}` : '数据提示：无集中提示'
    },
    rankTechReasonText (item) {
      const reason = item && item.technical && item.technical.reason
      if (reason) return reason
      const decisionReason = item && item.decision && item.decision.reason
      return decisionReason || this.rankTechQualityBrief(item)
    },
    rankTechUserConclusion (item) {
      return `结论：${this.rankTechActionLabel(item)}`
    },
    rankTechUserReason (item) {
      const action = this.rankTechActionPayload(item)
      if (action.reason) return `原因：${action.reason}`
      const risk = this.positionRiskPayload(item)
      const riskStatus = risk && risk.status
      if (riskStatus === 'overheated') return '原因：趋势或排名不错，但当前价格位置偏热。'
      if (riskStatus === 'elevated') return '原因：仍值得看，但追高风险比位置合理的标的更高。'
      if (riskStatus === 'reasonable') return '原因：排名、趋势和价格位置相对更容易复盘。'
      if (riskStatus === 'pullback_watch') return '原因：正在回调，适合先确认趋势有没有破坏。'
      const decisionReason = item && item.decision && item.decision.reason
      return `原因：${decisionReason || '资料还不完整，先不要提高优先级。'}`
    },
    rankTechUserEvidence (item) {
      const rank = this.rankTechTierLabel(item && (item.rankTier || (item.qlib && item.qlib.rank)))
      const trend = this.rankTechTrendLabel(item && item.trend && item.trend.label)
      const technical = this.rankTechTechnicalLabel(item && item.technical && item.technical.status)
      return `依据：${rank}，趋势${trend}，${technical}`
    },
    portfolioVariantLabel (variant) {
      const labels = {
        qlib_only: '只看模型排名',
        qlib_plus_trend: '加入趋势确认',
        qlib_plus_trend_indicators: '加入技术指标确认',
        qlib_plus_trend_position_risk: '加入追高风险过滤'
      }
      return labels[variant] || variant || '-'
    },
    formatReplayPercent (value) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      const percent = Math.abs(num) <= 1 ? num * 100 : num
      return `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`
    },
    portfolioPositionRiskText (item) {
      const summary = item && item.payload && item.payload.positionRiskSummary
      if (!summary) return '未启用'
      const blocked = Number(summary.blocked_overheated_adds || 0)
      const lowered = Number(summary.deprioritized_elevated_adds || 0)
      const review = Number(summary.risk_review_events || 0)
      if (!blocked && !lowered && !review) return '无明显追高降级'
      return "避开 " + blocked + " 次过热新增，" + lowered + " 次候选降级，" + review + " 次风险复盘提示"
    },
    portfolioReplayWarningText (item) {
      const warnings = (item && item.payload && item.payload.dataQuality && item.payload.dataQuality.warnings) || []
      const normalized = Array.isArray(warnings) ? warnings.slice(0, 2) : []
      return normalized.length ? `数据提示：${normalized.join(' / ')}` : '数据提示：无集中提示'
    },
    portfolioStrategyBrief (item) {
      const metrics = (item && item.metrics) || {}
      const actions = Number(metrics.actionCount || 0)
      const drawdown = metrics.maxDrawdown == null ? '-' : this.formatReplayPercent(metrics.maxDrawdown)
      if (item && item.profile && item.profile.key === 'confirmed_exit') return `默认低频策略：动作 ${actions} 次，回撤 ${drawdown}，重点减少过度交易。`
      if (item && item.profile && item.profile.key === 'rank_rotate_top50_adaptive_score') {
        const summary = (item.payload && item.payload.adaptiveScoreSummary) || {}
        const blocked = Number(summary.blocked_adds || 0)
        return `继承 Top50：动作 ${actions} 次，回撤 ${drawdown}，谨慎市况过滤 ${blocked} 次补仓候选。`
      }
      if (item && item.profile && item.profile.key === 'rank_rotate_top50_adaptive_score_risk_control') {
        const summary = (item.payload && item.payload.portfolioRiskSummary) || {}
        const blocked = Number(summary.blocked_adds || 0)
        return `高级风控对照：动作 ${actions} 次，回撤 ${drawdown}，暂停补仓 ${blocked} 次。`
      }
      if (item && item.profile && item.profile.key === 'rank_rotate_top50') return `进阶高收益策略：动作 ${actions} 次，回撤 ${drawdown}，换手更高。`
      if (item && item.profile && item.profile.key === 'rank_rotate_top30') return `中间参考策略：动作 ${actions} 次，回撤 ${drawdown}，反应更快但交易更频繁。`
      return `10 支上限策略：动作 ${actions} 次，回撤 ${drawdown}。`
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
          includeRawTrend: true
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
        this.restoreCrossBacktestValidation(row.symbol)
      } catch (error) {
        const response = error && error.response && error.response.data
        this.selectedCrossAnalysisDetail = (response && response.data) || { ok: false, status: 'read_error', symbol: row.symbol }
        this.prepareCrossReviewForm()
        this.restoreCrossBacktestValidation(row.symbol)
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
      this.crossReviewError = ''
      this.crossReviewNotice = '当前策略工作台为只读模式，不在前端保存复盘状态。'
    },
    restoreCrossBacktestValidation (symbol) {
      const normalized = this.normalizeTwSymbol(symbol)
      if (!normalized) {
        this.crossBacktestValidation = this.emptyCrossBacktestValidation()
        return
      }
      const cached = this.crossBacktestValidationCache[normalized]
      this.crossBacktestValidation = cached ? Object.assign(this.emptyCrossBacktestValidation(), cached) : Object.assign(this.emptyCrossBacktestValidation(), { symbol: normalized })
    },

    crossDetailItemForValidation () {
      const detail = this.selectedCrossAnalysisDetail || {}
      if (detail.item) return detail.item
      const symbol = this.normalizeTwSymbol(detail.symbol)
      return this.crossAnalysisItems.find(item => this.normalizeTwSymbol(item && item.symbol) === symbol) || null
    },

    async runCrossHistoricalValidation () {
      const detail = this.selectedCrossAnalysisDetail || {}
      const symbol = this.normalizeTwSymbol(detail.symbol || (detail.item && detail.item.symbol))
      if (!symbol || this.crossBacktestValidation.loading) return
      const cached = this.crossBacktestValidationCache[symbol]
      if (cached && cached.results && cached.results.length) {
        this.crossBacktestValidation = Object.assign(this.emptyCrossBacktestValidation(), cached)
        return
      }
      this.crossBacktestValidation = Object.assign(this.emptyCrossBacktestValidation(), { symbol, loading: true, actionLabel: '验证中' })
      try {
        if (!this.backtestTemplates.length) await this.loadBacktestTemplates()
        const templates = (this.backtestTemplates || []).slice(0, 4)
        if (!templates.length) throw new Error('没有可用的台股回测模板。')
        const results = []
        for (const template of templates) {
          try {
            const data = this.unwrap(await runTwStockReadonlyBacktest({
              symbol,
              strategyId: template.id,
              startDate: this.formatPickerDate(this.backtestForm.startDate),
              endDate: this.formatPickerDate(this.backtestForm.endDate),
              initialCapital: Number(this.backtestForm.initialCapital || 1000000),
              strategyConfig: { template: {} }
            }))
            const result = data && data.result ? data.result : data
            results.push(this.normalizeCrossBacktestResult(template, result, null))
          } catch (error) {
            const response = error && error.response && error.response.data
            results.push(this.normalizeCrossBacktestResult(template, null, (response && response.msg) || error.message || '回测失败'))
          }
        }
        const best = this.pickBestCrossBacktest(results)
        const decision = this.buildCrossBacktestDecision(best, this.crossDetailItemForValidation())
        const payload = Object.assign(this.emptyCrossBacktestValidation(), {
          symbol,
          loading: false,
          results,
          best,
          actionLabel: decision.label,
          actionType: decision.type,
          reason: decision.reason
        })
        this.crossBacktestValidation = payload
        this.$set(this.crossBacktestValidationCache, symbol, payload)
      } catch (error) {
        this.crossBacktestValidation = Object.assign(this.emptyCrossBacktestValidation(), {
          symbol,
          error: error.message || '历史验证失败',
          actionLabel: '验证失败',
          actionType: 'error'
        })
      }
    },

    normalizeCrossBacktestResult (template, result, error) {
      const metrics = (result && (result.metrics || result)) || {}
      const totalReturn = Number(metrics.totalReturn)
      const maxDrawdown = Number(metrics.maxDrawdown)
      const winRate = Number(metrics.winRate)
      const totalTrades = Number(metrics.totalTrades)
      const ok = !error && Number.isFinite(totalReturn)
      const robustScore = ok
        ? totalReturn - Math.abs(Number.isFinite(maxDrawdown) ? maxDrawdown : 0) * 0.8 + (Number.isFinite(winRate) ? winRate : 0) * 0.05 - (Number.isFinite(totalTrades) && totalTrades < 2 ? 10 : 0)
        : -Infinity
      return {
        ok,
        error: error || '',
        strategyId: template.id,
        strategyName: template.name || template.id,
        totalReturn: Number.isFinite(totalReturn) ? totalReturn : null,
        maxDrawdown: Number.isFinite(maxDrawdown) ? maxDrawdown : null,
        winRate: Number.isFinite(winRate) ? winRate : null,
        totalTrades: Number.isFinite(totalTrades) ? totalTrades : null,
        robustScore
      }
    },

    pickBestCrossBacktest (results) {
      const valid = (results || []).filter(item => item && item.ok)
      if (!valid.length) return null
      const scoreOf = item => Number.isFinite(Number(item && item.robustScore)) ? Number(item.robustScore) : -Infinity
      return valid.slice().sort((a, b) => scoreOf(b) - scoreOf(a))[0]
    },

    buildCrossBacktestDecision (best, item) {
      if (!best) return { type: 'manual_review', label: '人工复盘', reason: '没有可用的历史验证结果，不能据此做模拟动作。' }
      const category = item && item.cross && item.cross.category
      const alignment = item && item.cross && item.cross.alignment
      const trend = item && item.quantdinger && item.quantdinger.trend_label
      const totalReturn = Number(best.totalReturn || 0)
      const maxDrawdown = Math.abs(Number(best.maxDrawdown || 0))
      const trades = Number(best.totalTrades || 0)
      if (trades < 2) return { type: 'manual_review', label: '人工复盘', reason: '历史交易次数太少，样本不足。' }
      if (totalReturn <= 0) return { type: 'avoid_new_buy', label: '不新增模拟买入', reason: '较优策略历史收益不为正，先观察。' }
      if (maxDrawdown >= Math.max(20, Math.abs(totalReturn) * 1.2)) return { type: 'manual_review', label: '人工复盘', reason: '历史回撤相对收益偏大，不适合自动进入候选。' }
      if (category === 'focus_watch' && alignment === 'aligned' && ['uptrend', 'rebound'].includes(trend)) {
        return { type: 'sim_buy_candidate', label: '模拟买入候选', reason: '模型、趋势与历史验证相对一致，可放入模拟账户观察。' }
      }
      if (category === 'model_trend_divergence' || alignment === 'divergent') return { type: 'manual_review', label: '人工复盘', reason: '模型和趋势存在分歧，即使历史验证较好也不直接给动作。' }
      if (['downtrend', 'pullback'].includes(trend)) return { type: 'risk_review_if_holding', label: '若已持有则复盘风险', reason: '趋势偏弱，历史验证只能作为风险参考，不直接给减仓指令。' }
      return { type: 'watch_only', label: '观察/保留', reason: '历史验证可用，但当前交叉信号还不足以进入模拟买入候选。' }
    },

    async openCrossAnalysisHistoricalSimulation () {
      const detail = this.selectedCrossAnalysisDetail
      const symbol = detail && detail.symbol
      if (!symbol || this.runningBacktest) return
      await this.selectTrendSymbol(symbol)
      this.backtestForm = Object.assign({}, this.backtestForm, {
        strategyId: 'ma_cross_builtin',
        initialCapital: 1000000
      })
      this.backtestPanelVisible = true
      this.backtestResult = null
      this.backtestError = ''
      if (!this.backtestTemplates.length) await this.loadBacktestTemplates()
      await this.$nextTick()
      this.scrollToBacktestPanel()
      await this.runReadonlyBacktest()
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
    isUnknownTrend (label) {
      const value = String(label || '').trim().toLowerCase()
      return !value || value === 'unknown' || value === 'trend_unavailable'
    },
    crossTrendLabel (label) {
      const labels = {
        uptrend: '上升趋势',
        rebound: '反弹',
        sideways: '震荡',
        downtrend: '下降趋势',
        pullback: '回落',
        unknown: '中性/未知',
        trend_unavailable: '趋势不可用'
      }
      const key = String(label || 'trend_unavailable').trim()
      return labels[key] || key || '趋势不可用'
    },
    crossTrendDisplayLabel (row) {
      const warnings = row && row.quantdinger && Array.isArray(row.quantdinger.quality_warnings) ? row.quantdinger.quality_warnings : []
      if (warnings.includes('short_history_below_60_bars')) return '样本不足'
      return this.crossTrendLabel(row && row.quantdinger && row.quantdinger.trend_label)
    },
    crossCategoryColor (category) {
      if (category === 'focus_watch') return 'green'
      if (category === 'secondary_watch') return 'blue'
      if (category === 'model_trend_divergence') return 'orange'
      if (category === 'data_review_required' || category === 'trend_unavailable') return 'red'
      return 'default'
    },
    crossCategoryLabel (category) {
      const labels = {
        focus_watch: '重点观察',
        secondary_watch: '次级观察',
        model_trend_divergence: '模型趋势分歧',
        data_review_required: '需要数据复核',
        trend_unavailable: '趋势不可用',
        model_watch_trend_neutral: '中性观察',
        low_priority_watch: '低优先观察',
        uncategorized: '未分类'
      }
      const key = String(category || 'uncategorized').trim()
      return labels[key] || key || '未分类'
    },
    crossActionLabel (action) {
      const labels = {
        manual_review_watchlist: '加入人工观察名单',
        manual_review_required: '人工复盘',
        data_review_required: '先复核数据',
        watch_only: '仅观察',
        avoid_until_data_ready: '等数据完整后再看'
      }
      return labels[action] || action || '人工复盘'
    },
    crossPriorityLabel (priority) {
      const labels = {
        high: '高优先级',
        medium: '中优先级',
        low: '低优先级',
        blocked: '先复核数据'
      }
      return labels[priority] || '人工复盘'
    },
    crossBasisLabel (status) {
      const labels = {
        ok: '口径正常',
        date_gap: '日期有落差',
        quantdinger_raw_unavailable: '趋势数据缺失'
      }
      return labels[status] || status || '待确认'
    },
    crossDateGapLabel (gap) {
      if (gap == null || gap === '') return '日期差 -'
      const value = Number(gap)
      if (!Number.isFinite(value)) return `日期差 ${gap}`
      if (value === 0) return '模型与行情同日'
      if (value < 0) return `行情比模型新 ${Math.abs(value)} 日`
      return `模型比行情新 ${value} 日`
    },
    crossQualityBrief (row) {
      const warnings = row && row.quantdinger && Array.isArray(row.quantdinger.quality_warnings) ? row.quantdinger.quality_warnings : []
      if (warnings.length) return warnings.map(this.qualityWarningLabel).filter(Boolean).slice(0, 2).join(' / ')
      const basis = row && row.data_basis
      if (basis && basis.date_gap_days != null) return `日期差 ${basis.date_gap_days}`
      return '无集中提示'
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

    rankChangeLabelColor (item) {
      const type = item && item.change_type
      const delta = Number(item && item.rank_delta)
      if (type === 'entered') return 'green'
      if (type === 'exited') return 'red'
      if (Number.isFinite(delta) && delta > 0) return 'green'
      if (Number.isFinite(delta) && delta < 0) return 'orange'
      return 'blue'
    },
    rankChangeRankText (item) {
      if (!item) return '-'
      const current = item.current_rank == null ? '-' : `#${item.current_rank}`
      const previous = item.previous_rank == null ? '-' : `#${item.previous_rank}`
      if (this.rankChangesActiveTab === 'candidates') return `Top50 ${current} / 昨日 ${previous}`
      return `${previous} → ${current}`
    },
    rankChangeDeltaText (item) {
      if (!item) return '-'
      if (item.rank_delta == null) {
        if (item.change_type === 'entered') return `昨日未入 ${this.rankingBucketText}`
        if (item.change_type === 'exited') return `当前 asof 未入 ${this.rankingBucketText}`
        if (this.rankChangesActiveTab === 'candidates') return '昨日不在 Top50'
        return '无可比排名'
      }
      const delta = Number(item.rank_delta)
      if (delta === 0) return '持平'
      return delta > 0 ? `上升 ${delta}` : `下降 ${Math.abs(delta)}`
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
      this.qlibOpsError = '当前策略工作台为只读模式，不在前端手动运行 qlib ops。'
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
    simDraftContextStorageKey () {
      return 'tw-stock-sim-draft-context'
    },
    prefillSimDraftFromQlib (row) {
      if (!row || !row.symbol) return
      this.writeSimDraftContext({ source_type: 'qlib_rank', symbol: String(row.symbol).trim().toUpperCase() })
    },
    canPrefillSimDraftFromCross (row) {
      const category = row && row.cross && row.cross.category
      const alignment = row && row.cross && row.cross.alignment
      return category === 'focus_watch' || alignment === 'aligned'
    },
    prefillSimDraftFromCross (row) {
      if (!this.canPrefillSimDraftFromCross(row) || !row || !row.symbol) return
      this.writeSimDraftContext({ source_type: 'cross_analysis', symbol: String(row.symbol).trim().toUpperCase() })
    },
    writeSimDraftContext (draft) {
      const symbol = draft && draft.symbol ? `：${draft.symbol}` : ''
      this.degradedNotice = `当前策略工作台为只读模式，不生成模拟交易草稿${symbol}；需要模拟账户时请单独进入模拟账户页面。`
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
      if (!row || !row.symbol || this.runningBacktest) return
      await this.selectTrendSymbol(row.symbol)
      this.backtestPanelVisible = true
      this.backtestResult = null
      this.backtestError = ''
      if (!this.backtestTemplates.length) await this.loadBacktestTemplates()
      await this.$nextTick()
      this.scrollToBacktestPanel()
    },
    qlibCustomRow (record) {
      return {
        on: {
          click: () => this.selectTrendSymbol(record.symbol)
        }
      }
    },
    normalizeTwSymbol (symbol) {
      let value = String(symbol || '').trim().toUpperCase()
      if (!value) return ''
      if (value.includes(':')) value = value.split(':').pop()
      if (value.startsWith('TW')) value = value.slice(2)
      if (value.includes('.')) value = value.split('.')[0]
      return /^\d{4,6}$/.test(value) ? value : ''
    },
    filterChartSymbolOption (input, option) {
      const text = String(option && option.componentOptions && option.componentOptions.children && option.componentOptions.children[0] && option.componentOptions.children[0].text || '').toUpperCase()
      return text.includes(String(input || '').toUpperCase())
    },
    async loadChartSymbolOptions (bucket) {
      const source = bucket || (this.chartSymbolSource === 'top50' ? 'top50' : 'top30')
      if (!['top30', 'top50'].includes(source)) return
      if (this.chartSignalPayloads[source] && Array.isArray(this.chartSignalPayloads[source].signals)) return
      this.loadingChartSymbols = true
      try {
        const data = this.unwrap(await getLatestQlibOptionCSignals({
          bucket: source,
          enrichTrend: false,
          trendLimit: this.config.limit_bars || 120
        }))
        this.$set(this.chartSignalPayloads, source, data || {})
        this.syncChartSymbol()
      } finally {
        this.loadingChartSymbols = false
      }
    },
    async handleChartSourceChange () {
      if (this.chartSymbolSource === 'custom') {
        this.chartSymbolInput = this.chartSymbol || ''
        return
      }
      await this.loadChartSymbolOptions(this.chartSymbolSource)
      const symbols = this.chartSymbols
      if (symbols.length && !symbols.includes(this.chartSymbol)) {
        this.chartSymbol = symbols[0]
        await this.handleChartSymbolChange()
      }
    },
    async handleManualChartSymbolSearch (value) {
      const symbol = this.normalizeTwSymbol(value || this.chartSymbolInput)
      if (!symbol) {
        this.$message.warning('请输入有效台股代码，例如 2357 或 TW6290')
        return
      }
      this.chartSymbol = symbol
      this.chartSymbolInput = symbol
      await this.handleChartSymbolChange()
    },
    scrollToBacktestPanel () {
      const panel = this.$refs.readonlyBacktestPanel
      const node = panel && (panel.$el || panel)
      if (node && typeof node.scrollIntoView === 'function') {
        node.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
      this.drawBacktestEquityChart()
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
      if (!this.chartSymbol || this.runningBacktest) return
      if (!this.backtestForm.strategyId && !this.backtestTemplates.length) {
        await this.loadBacktestTemplates()
      }
      if (!this.backtestForm.strategyId) {
        this.backtestError = '没有可用的台股回测模板。'
        return
      }
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
    async loadPhaseYZProductizationStatus () {
      this.loadingPhaseYZProductization = true
      this.phaseYZProductizationError = ''
      try {
        this.phaseYZProductizationPayload = this.unwrap(await getTwStockPhaseYZProductizationStatus())
      } catch (error) {
        this.phaseYZProductizationError = (error && error.message) || '模拟账户应用状态暂不可读。'
      } finally {
        this.loadingPhaseYZProductization = false
      }
    },
    async refreshAll () {
      this.loading = true
      try {
        const monitorReads = this.loadConfig()
          .then(() => Promise.allSettled([this.loadTrends(), this.loadAlerts(), this.loadScanLogs(), this.loadChartSymbolOptions()]))
          .catch(() => {
            this.degradedNotice = '监控配置暂不可读；模型信号、候选名单与历史比较仍独立加载。可稍后刷新重试。'
          })
        await Promise.allSettled([monitorReads, this.loadReadonlyOpsStatus(), this.loadQlibHealth(), this.loadQlibSignals(), this.loadRankChanges(), this.loadDailyAutoUpdateStatus(), this.loadQlibOpsLatest(), this.loadCrossAnalysis(), this.loadCurrentStrategyContext(), this.loadPhaseYZProductizationStatus(), this.loadReadonlyStrategySnapshot(), this.loadReadonlyShadowExposure(), this.loadReadonlyReplayWindowIndex(), this.loadReadonlyModelStrategyComparison(), this.loadRankTechCrossLatest(), this.loadLtrReadonlyExplanation(), this.loadLtrOptionalSimStrategies(), this.loadTwStockAgentContext()])
        this.lastRefreshedAt = new Date().toLocaleTimeString()
        this.syncAutoRefreshTimer()
      } finally {
        this.loading = false
      }
    },
    async loadConfig () {
      const data = this.unwrap(await getTwStockMonitorConfig({ name: this.config.name || 'default' }))
      this.config = Object.assign({}, this.config, data || {})
      this.degradedNotice = ''
      if (data && data.degraded) {
        this.degradedNotice = '資料庫暫不可用：已載入預設台股清單，可查看趨勢；提醒與歷史不會持久保存。'
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
        await this.loadChartSymbolOptions()
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
    async loadSimTradeMarkers () {
      this.loadingSimTradeMarkers = true
      try {
        const accountsPayload = this.unwrap(await getTwStockSimAccounts())
        const accounts = Array.isArray(accountsPayload && accountsPayload.items) ? accountsPayload.items : []
        if (!accounts.length) {
          this.simTradeMarkers = []
          return
        }
        const tradesPayload = this.unwrap(await getTwStockSimTrades(accounts[0].account_uid, { limit: 300 }))
        this.simTradeMarkers = Array.isArray(tradesPayload && tradesPayload.items) ? tradesPayload.items : []
      } catch (error) {
        this.simTradeMarkers = []
      } finally {
        this.loadingSimTradeMarkers = false
        this.$nextTick(this.drawPriceChart)
      }
    },
    async runScan () {
      await this.refreshMonitorReadonly()
    },
    async refreshMonitorReadonly () {
      this.scanning = true
      try {
        await Promise.all([this.loadTrends(), this.loadAlerts(), this.loadScanLogs()])
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
      this.degradedNotice = '当前策略工作台为只读模式，不在前端保存监控配置。'
      this.configDrawerVisible = false
    },
    async updateAlertStatus (row, status) {
      this.degradedNotice = '当前策略工作台为只读模式，不在前端写入提醒状态。'
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
    formatSignedNumber (value, digits = 2) {
      if (value == null || value === '') return '-'
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      if (num === 0) return num.toFixed(digits)
      return `${num > 0 ? '+' : ''}${num.toFixed(digits)}`
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
        markers: this.chartSimTradeMarkers,
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
      ;(options.markers || []).forEach(marker => {
        const index = points.findIndex(point => point.date === marker.date)
        if (index < 0) return
        const x = pad.left + (points.length > 1 ? xStep * index : plotW / 2)
        const py = y(Number(marker.price || 0))
        const isSell = marker.side === 'sell'
        const color = isSell ? '#d46b08' : '#2563eb'
        const label = isSell ? '模拟卖出' : '模拟买入'
        ctx.save()
        ctx.fillStyle = color
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 2
        ctx.beginPath()
        if (isSell) {
          ctx.moveTo(x, py + 9)
          ctx.lineTo(x - 7, py - 3)
          ctx.lineTo(x + 7, py - 3)
        } else {
          ctx.moveTo(x, py - 9)
          ctx.lineTo(x - 7, py + 3)
          ctx.lineTo(x + 7, py + 3)
        }
        ctx.closePath()
        ctx.fill()
        ctx.stroke()
        ctx.font = '11px sans-serif'
        ctx.textAlign = 'center'
        const textY = isSell ? Math.min(py + 22, pad.top + plotH - 4) : Math.max(py - 14, pad.top + 10)
        const textW = ctx.measureText(label).width + 8
        ctx.fillStyle = 'rgba(255, 255, 255, 0.92)'
        ctx.fillRect(x - textW / 2, textY - 11, textW, 15)
        ctx.strokeStyle = color
        ctx.strokeRect(x - textW / 2, textY - 11, textW, 15)
        ctx.fillStyle = color
        ctx.fillText(label, x, textY)
        ctx.restore()
      })
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

.chart-footnote-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.research-boundary-alert {
  margin-bottom: 16px;
}

.page-section-rail {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: 8px 0 14px;
  padding: 8px 10px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background: #f8fbff;
}

.page-section-rail-label {
  color: #475467;
  font-size: 12px;
  font-weight: 650;
}

.page-section-rail-button {
  border-radius: 6px;
  color: #344054;
  border-color: #d0d5dd;
  background: #fff;
}

.page-section-rail-button.rail-tone-status {
  color: #075985;
  border-color: #bae6fd;
  background: #f0f9ff;
}

.page-section-rail-button.rail-tone-primary {
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.page-section-rail-button.rail-tone-research {
  color: #047857;
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.page-section-rail-button.rail-tone-agent {
  color: #7c3aed;
  border-color: #ddd6fe;
  background: #f5f3ff;
}

.page-section-rail-button.rail-tone-muted {
  color: #667085;
  border-color: #e4e7ec;
  background: #ffffff;
}

.monitor-anchor-section {
  margin-bottom: 16px;
}

.strategy-workbench-overview-card {
  margin-bottom: 16px;
}
.workbench-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.workbench-title-block > span {
  color: #111827;
  font-weight: 650;
}
.workbench-title-block small {
  color: #667085;
  font-size: 12px;
  font-weight: 400;
}
.workbench-overview-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.workbench-status-copy {
  flex: 1;
  min-width: 220px;
  padding: 10px 12px;
  border: 1px solid #dbe7f3;
  border-left: 4px solid #2563eb;
  border-radius: 8px;
  background: #f8fbff;
  color: #1f2937;
  line-height: 1.5;
}
.workbench-overview-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.advanced-ops-collapse-contained {
  margin-top: 10px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fff;
}

.advanced-ops-intro {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  background: #f8fafc;
}

.advanced-ops-intro strong {
  color: #111827;
}

.advanced-ops-intro span {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}
.workbench-overview-alert {
  margin-bottom: 12px;
}
.workbench-selection-bar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(0, 2.4fr);
  gap: 12px;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}
.workbench-selection-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.workbench-selection-copy span,
.workbench-selection-controls label > span {
  color: #667085;
  font-size: 12px;
}
.workbench-selection-copy strong {
  color: #111827;
  font-size: 15px;
}
.workbench-selection-copy small {
  color: #475467;
  line-height: 1.45;
}
.workbench-selection-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 10px;
  min-width: 0;
}
.workbench-selection-controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.workbench-overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.workbench-overview-grid > div {
  min-height: 88px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #fff;
}
.workbench-overview-grid span,
.workbench-overview-grid small {
  color: #667085;
  font-size: 12px;
}
.workbench-overview-grid strong {
  color: #111827;
  font-size: 18px;
  line-height: 1.25;
  word-break: break-word;
}
.workbench-technical-collapse {
  margin-top: 10px;
  background: #fff;
}
.workbench-technical-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.workbench-technical-grid span {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #f8fafc;
  color: #667085;
  font-size: 12px;
}
.workbench-technical-grid strong {
  display: block;
  margin-top: 3px;
  color: #111827;
  word-break: break-word;
}

.phase-yz-productization-card { margin-bottom: 16px; }
.phase-yz-toolbar,
.phase-yz-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.phase-yz-toolbar { margin-bottom: 12px; }
.phase-yz-alert { margin-bottom: 12px; }
.phase-yz-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.phase-yz-grid > div {
  min-height: 76px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #fff;
}
.phase-yz-grid span,
.phase-yz-grid small { color: #667085; font-size: 12px; }
.phase-yz-grid strong { color: #111827; word-break: break-word; }

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

.data-freshness-overview {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background: #ffffff;
}

.monitor-anchor-section,
#daov-section-freshness,
#daov-section-strategy,
#daov-section-snapshot,
#daov-section-replay,
#daov-section-research,
#daov-section-agent,
#daov-section-maintenance {
  scroll-margin-top: 84px;
}

.data-freshness-header,
.data-freshness-actions,
.data-freshness-footnote {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.data-freshness-header {
  margin-bottom: 12px;
}

.data-freshness-header strong {
  display: block;
  color: #111827;
  font-size: 15px;
  margin-bottom: 3px;
}

.data-freshness-header span,
.data-freshness-footnote {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.data-freshness-actions {
  align-items: center;
  justify-content: flex-end;
}

.data-freshness-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.data-freshness-details summary {
  cursor: pointer;
  color: #475467;
  font-size: 12px;
  padding: 8px 0;
}

.data-freshness-details summary:focus-visible {
  outline: 2px solid #1890ff;
  outline-offset: 2px;
}

.data-freshness-shadow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 10px;
  color: #475467;
  font-size: 12px;
}

.data-freshness-ops-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.data-freshness-node,
.data-freshness-ops-item {
  min-width: 0;
  min-height: 92px;
  padding: 10px 12px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.data-freshness-ops-item {
  min-height: 78px;
  background: #ffffff;
}

.data-freshness-node.lagging {
  border-color: #fed7aa;
  background: #fff7ed;
}

.data-freshness-node span,
.data-freshness-node small,
.data-freshness-ops-item span,
.data-freshness-ops-item small {
  color: #667085;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.data-freshness-node strong,
.data-freshness-ops-item strong {
  color: #111827;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.data-freshness-node strong {
  font-size: 18px;
}

.data-freshness-ops-item strong {
  font-size: 13px;
}

.data-freshness-ops-hint {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 10px;
  color: #475467;
  font-size: 12px;
  line-height: 1.5;
}

.data-freshness-ops-hint span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.data-freshness-ops-hint strong {
  margin-right: 4px;
  color: #111827;
}

.data-freshness-footnote {
  justify-content: flex-start;
  margin-top: 10px;
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

.qlib-option-c-card .ant-table-wrapper,
.qlib-option-c-card .ant-table-content {
  max-width: 100%;
  overflow-x: auto;
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


.daily-auto-update-panel {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #e4ecf7;
  border-radius: 8px;
  background: #fbfdff;
}

.daily-auto-update-header,
.daily-auto-update-tags,
.daily-auto-update-warnings {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.daily-auto-update-header strong {
  display: block;
  margin-bottom: 3px;
}

.daily-auto-update-tags,
.daily-auto-update-warnings {
  justify-content: flex-start;
}

.daily-auto-update-grid,
.daily-auto-update-source-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.daily-auto-update-grid span,
.daily-auto-update-source-card {
  min-width: 0;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  color: #475467;
  overflow-wrap: anywhere;
}

.daily-auto-update-grid strong,
.daily-auto-update-source-card strong {
  color: #111827;
  font-weight: 600;
}

.daily-auto-update-source-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.daily-auto-update-source-card span,
.daily-auto-update-source-card small {
  color: #667085;
  font-size: 12px;
}

.daily-auto-update-alert {
  margin-top: 8px;
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
.agent-warning-list,
.agent-skill-list {
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
.agent-skill-list,
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


.symbol-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.symbol-name-cell strong {
  color: #111827;
  line-height: 1.25;
}

.instrument-code,
.symbol-name-cell .muted {
  font-size: 12px;
  line-height: 1.25;
}

.price-date-cell {
  display: flex;
  gap: 8px;
  align-items: baseline;
  white-space: nowrap;
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

.rank-change-card {
  margin-top: 16px;
}

.rank-change-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  color: #667085;
}

.rank-change-alert {
  margin-bottom: 12px;
}

.rank-change-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.rank-change-summary-item {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #f8fafc;
}

.rank-change-summary-item span,
.rank-change-rank-cell span,
.rank-change-score-cell span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.rank-change-summary-item strong,
.rank-change-rank-cell strong,
.rank-change-score-cell strong {
  color: #111827;
  font-weight: 600;
}

.rank-change-tabs {
  margin-bottom: 8px;
}

.rank-change-table /deep/ .ant-table-row {
  cursor: default;
}

.rank-change-delta.positive {
  color: #138a3d;
}

.rank-change-delta.negative {
  color: #b54708;
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
  .summary-grid,
  .workbench-overview-grid,
  .data-freshness-track,
  .data-freshness-ops-grid,
  .workbench-selection-bar,
  .workbench-technical-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .workbench-selection-controls {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .tw-stock-monitor {
    padding: 12px;
  }

  .topbar,
  .workbench-overview-toolbar {
    flex-direction: column;
  }

  .workbench-overview-actions {
    justify-content: flex-start;
  }

  .workbench-overview-grid,
  .data-freshness-track,
  .data-freshness-ops-grid,
  .workbench-selection-bar,
  .workbench-selection-controls,
  .workbench-technical-grid,
  .selected-symbol-panel,
  .backtest-metrics,
  .cross-validation-best,
  .cross-validation-list,
  .backtest-grid,
  .cross-analysis-summary,
  .cross-detail-grid,
  .rank-tech-grid,
  .portfolio-replay-grid,
  .readonly-candidate-layout,
  .readonly-replay-track {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-grid .metric-card {
    padding: 10px;
    min-height: 76px;
  }

  .summary-grid .metric-card strong {
    font-size: 18px;
  }

  .readonly-candidate-row {
    grid-template-columns: 44px minmax(0, 1fr);
  }

  .readonly-candidate-status {
    grid-column: 2;
    justify-self: start;
  }

  .readonly-replay-window,
  .paper-portfolio-panel {
    max-width: 100%;
  }
}


.current-strategy-context-card,
.readonly-strategy-snapshot,
.readonly-replay-window {
  margin-top: 16px;
}

.current-context-toolbar,
.current-context-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.current-context-toolbar {
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: #475467;
  font-size: 12px;
}

.current-context-alert {
  margin-bottom: 10px;
}

.current-context-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}

.current-context-grid > div {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
}

.current-context-grid span,
.current-context-grid small {
  display: block;
  color: #667085;
  font-size: 12px;
}

.current-context-grid strong {
  display: block;
  margin: 3px 0;
  color: #111827;
  font-size: 16px;
  overflow-wrap: anywhere;
}

.readonly-snapshot-toolbar,
.readonly-window-toolbar,
.readonly-section-head,
.readonly-candidate-row,
.readonly-source-grid {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.readonly-window-toolbar {
  margin-bottom: 10px;
}

.readonly-snapshot-toolbar {
  justify-content: space-between;
  margin-bottom: 10px;
  color: #475467;
  font-size: 12px;
}

.readonly-snapshot-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.readonly-snapshot-title-block strong {
  color: #111827;
  font-size: 13px;
}

.readonly-snapshot-title-block span {
  color: #667085;
}

.readonly-snapshot-alert {
  margin-bottom: 12px;
}

.readonly-snapshot-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.readonly-snapshot-grid,
.readonly-source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.readonly-snapshot-metric,
.readonly-source-grid span,
.readonly-candidate-section {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
  overflow-wrap: anywhere;
}

.readonly-snapshot-metric.primary {
  border-color: #91caff;
  background: #f0f7ff;
}

.readonly-snapshot-metric strong,
.readonly-snapshot-metric small,
.readonly-snapshot-metric span {
  display: block;
}

.readonly-snapshot-metric strong {
  margin-top: 4px;
  color: #111827;
  font-size: 16px;
  line-height: 1.35;
}

.readonly-snapshot-metric span,
.readonly-source-grid strong,
.readonly-candidate-row strong,
.readonly-section-head strong {
  color: #111827;
  font-weight: 600;
}

.readonly-snapshot-metric small,
.readonly-source-grid span,
.readonly-candidate-row span,
.readonly-snapshot-empty {
  color: #667085;
  font-size: 12px;
}

.readonly-candidate-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.readonly-candidate-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.readonly-section-head {
  justify-content: space-between;
}

.readonly-section-head > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.readonly-section-head small {
  color: #667085;
  font-size: 12px;
}

.readonly-candidate-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.readonly-candidate-row {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
}

.readonly-candidate-rank {
  color: #1d4ed8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.6;
}

.readonly-candidate-main,
.readonly-candidate-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.readonly-candidate-main strong {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  font-size: 14px;
}

.readonly-candidate-symbol {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 15px;
}

.readonly-candidate-name {
  color: #344054;
  font-size: 13px;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.readonly-candidate-status {
  margin-right: 0;
}

.readonly-candidate-meta {
  text-align: right;
}

.readonly-candidate-row.compact {
  justify-content: flex-start;
}

.readonly-window-note {
  color: #475467;
  font-size: 12px;
}

.readonly-replay-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.readonly-replay-track span {
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  background: #f8fbff;
  color: #1e3a8a;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.readonly-snapshot-empty {
  padding: 10px 0;
}

.rank-tech-replay-card {
  margin-top: 16px;
}

.rank-tech-toolbar,
.rank-tech-panel-head,
.rank-tech-symbol-line,
.rank-tech-reason-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rank-tech-toolbar {
  margin-bottom: 10px;
}

.rank-tech-readonly-note,
.rank-tech-alert {
  margin-bottom: 12px;
}

.rank-tech-grid,
.portfolio-replay-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.rank-tech-panel,
.portfolio-replay-section,
.portfolio-replay-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
}

.rank-tech-panel-head {
  justify-content: space-between;
  margin-bottom: 10px;
  color: #475467;
}

.rank-tech-panel-head strong {
  color: #111827;
}

.rank-tech-priority-list,
.rank-tech-why-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-tech-priority-item,
.rank-tech-why-item {
  min-width: 0;
  padding: 10px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fff;
}

.rank-tech-symbol-line strong,
.rank-tech-why-item strong,
.portfolio-replay-card strong {
  color: #111827;
}

.rank-tech-symbol-line span,
.rank-tech-reason-line,
.rank-tech-why-item span,
.rank-tech-why-item small,
.portfolio-warning-line,
.rank-tech-empty {
  color: #667085;
  font-size: 12px;
}

.rank-tech-reason-line,
.rank-tech-why-item {
  line-height: 1.5;
}

.portfolio-replay-section {
  margin-top: 12px;
}

.portfolio-replay-card {
  background: #fff;
}

.portfolio-metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
  color: #667085;
  font-size: 12px;
}

.portfolio-metric-row b {
  color: #111827;
}

.portfolio-warning-line {
  margin-top: 10px;
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

.cross-analysis-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.cross-summary-item {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #ffffff;
  overflow-wrap: anywhere;
}

.cross-summary-item span {
  display: block;
  margin-bottom: 3px;
  color: #667085;
  font-size: 12px;
}

.cross-summary-item strong {
  color: #111827;
  font-weight: 650;
}

.advanced-ops-collapse.compact {
  margin-bottom: 12px;
}

.monitor-tools-collapse {
  margin-top: 16px;
}

.monitor-tools-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
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

.cross-trend-cell,
.cross-summary-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #475467;
  font-size: 12px;
}

.cross-trend-cell .ant-tag,
.cross-summary-cell strong {
  align-self: flex-start;
}

.cross-trend-cell small {
  color: #98a2b3;
}

.cross-summary-cell strong {
  color: #111827;
  font-size: 12px;
}

.cross-summary-cell span {
  line-height: 1.45;
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

.cross-backtest-validation {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fbfdff;
}

.cross-validation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.cross-validation-best {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.cross-validation-best > div {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #edf2f7;
}

.cross-validation-best span,
.cross-validation-item span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.cross-validation-best strong,
.cross-validation-item strong {
  color: #111827;
}

.cross-validation-reason {
  margin-top: 10px;
  color: #475467;
  line-height: 1.55;
}

.cross-validation-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.cross-validation-item {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #edf2f7;
}

.cross-validation-empty {
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


.ltr-optional-sim-strategy {
  margin-top: 16px;
}
.ltr-optional-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ltr-optional-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: #475467;
  font-size: 13px;
}
.ltr-optional-card.active {
  border-color: #3b82f6;
  background: #f8fbff;
}
.ltr-optional-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}
.ltr-optional-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ltr-optional-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.ltr-optional-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}
.ltr-optional-metrics div {
  min-width: 0;
  padding: 8px;
  border: 1px solid #eef2f7;
  border-radius: 6px;
  background: #fff;
}
.ltr-optional-metrics small,
.ltr-optional-metrics b {
  display: block;
  overflow-wrap: anywhere;
}
.ltr-optional-metrics small {
  color: #667085;
  font-size: 12px;
}

.ltr-readonly-explanation {
  margin-top: 16px;
}
.ltr-explanation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}
.ltr-explanation-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
}
.ltr-explanation-card small {
  color: #666;
  line-height: 1.5;
}
.ltr-explanation-detail {
  margin-top: 4px;
}
.ltr-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}
.ltr-detail-wide {
  grid-column: 1 / -1;
}


</style>
