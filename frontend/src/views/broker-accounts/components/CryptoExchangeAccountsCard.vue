<template>
  <div class="crypto-card" :class="{ 'theme-dark': isDarkTheme }">
    <div class="crypto-card-header">
      <div class="crypto-card-title-block">
        <div class="crypto-card-title">
          <a-icon type="api" class="crypto-card-title-icon" />
          {{ $t('brokerAccounts.cryptoSection.title') }}
        </div>
        <div class="crypto-card-subtitle">
          {{ $t('brokerAccounts.cryptoSection.subtitle') }}
        </div>
      </div>
      <div class="crypto-card-actions">
        <a-button :loading="loading" @click="loadCredentials">
          <a-icon type="reload" /> {{ $t('brokerAccounts.refresh') }}
        </a-button>
        <a-button type="primary" @click="openAddModal">
          <a-icon type="plus" /> {{ $t('brokerAccounts.cryptoSection.addAccount') }}
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div v-if="!loading && filteredItems.length === 0" class="crypto-empty">
        <a-icon type="inbox" />
        <div class="crypto-empty-text">{{ $t('brokerAccounts.cryptoSection.empty') }}</div>
        <a-button type="link" @click="openAddModal">
          {{ $t('brokerAccounts.cryptoSection.emptyCta') }} →
        </a-button>
      </div>

      <div v-else class="crypto-grid">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="crypto-item"
        >
          <div class="crypto-item-icon" :style="{ background: iconBg(item.exchange_id) }">
            {{ exchangeInitial(item.exchange_id) }}
          </div>
          <div class="crypto-item-meta">
            <div class="crypto-item-name">
              {{ exchangeDisplayName(item.exchange_id) }}
              <span class="crypto-item-sep">·</span>
              <span class="crypto-item-alias">{{ item.name || $t('brokerAccounts.cryptoSection.unnamed') }}</span>
            </div>
            <div class="crypto-item-line">
              <span v-if="item.api_key_hint" class="crypto-item-hint">{{ item.api_key_hint }}</span>
              <span v-if="item.created_at" class="crypto-item-time">{{ formatTime(item.created_at) }}</span>
            </div>
          </div>
          <div class="crypto-item-actions">
            <a-popconfirm
              :title="$t('brokerAccounts.cryptoSection.confirmDelete', { name: item.name || exchangeDisplayName(item.exchange_id) })"
              :ok-text="$t('brokerAccounts.confirm')"
              :cancel-text="$t('brokerAccounts.cancel')"
              ok-type="danger"
              @confirm="deleteItem(item)"
            >
              <a-button size="small" type="link" class="crypto-item-delete">
                <a-icon type="delete" /> {{ $t('brokerAccounts.cryptoSection.delete') }}
              </a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>
    </a-spin>

    <exchange-account-modal
      :visible.sync="addModalVisible"
      @success="onCredentialSaved"
    />
  </div>
</template>

<script>
import { listExchangeCredentials, deleteExchangeCredential } from '@/api/credentials'
import ExchangeAccountModal from '@/components/ExchangeAccountModal/ExchangeAccountModal.vue'
import moment from 'moment'

const CRYPTO_EXCHANGE_IDS = new Set([
  'binance', 'okx', 'bitget', 'bybit', 'coinbaseexchange',
  'kraken', 'kucoin', 'gate', 'bitfinex', 'deepcoin', 'htx'
])

const DISPLAY_NAMES = {
  binance: 'Binance',
  okx: 'OKX',
  bitget: 'Bitget',
  bybit: 'Bybit',
  coinbaseexchange: 'Coinbase',
  kraken: 'Kraken',
  kucoin: 'KuCoin',
  gate: 'Gate.io',
  bitfinex: 'Bitfinex',
  deepcoin: 'Deepcoin',
  htx: 'HTX'
}

const ICON_COLORS = {
  binance: '#F0B90B',
  okx: '#000',
  bitget: '#00D1FF',
  bybit: '#F7A600',
  coinbaseexchange: '#1652F0',
  kraken: '#5741D9',
  kucoin: '#24AE8F',
  gate: '#17E1A4',
  bitfinex: '#16B157',
  deepcoin: '#7B61FF',
  htx: '#1B2C3B'
}

export default {
  name: 'CryptoExchangeAccountsCard',
  components: { ExchangeAccountModal },
  props: {
    isDarkTheme: { type: Boolean, default: false }
  },
  data () {
    return {
      items: [],
      loading: false,
      addModalVisible: false
    }
  },
  computed: {
    filteredItems () {
      return this.items.filter(it => CRYPTO_EXCHANGE_IDS.has(String(it.exchange_id || '').toLowerCase()))
    }
  },
  mounted () {
    this.loadCredentials()
  },
  methods: {
    exchangeDisplayName (id) {
      return DISPLAY_NAMES[id] || (id ? id.toUpperCase() : '--')
    },
    exchangeInitial (id) {
      const name = this.exchangeDisplayName(id)
      return name.charAt(0).toUpperCase()
    },
    iconBg (id) {
      return ICON_COLORS[id] || '#1890ff'
    },
    formatTime (raw) {
      if (!raw) return ''
      const m = moment(raw)
      if (!m.isValid()) return ''
      return m.format('YYYY-MM-DD HH:mm')
    },
    async loadCredentials () {
      this.loading = true
      try {
        const res = await listExchangeCredentials()
        if (res && res.code === 1 && res.data && Array.isArray(res.data.items)) {
          this.items = res.data.items
        } else {
          this.items = []
        }
      } catch (_) {
        this.items = []
      } finally {
        this.loading = false
      }
    },
    openAddModal () {
      this.addModalVisible = true
    },
    onCredentialSaved () {
      this.loadCredentials()
    },
    async deleteItem (item) {
      try {
        const res = await deleteExchangeCredential(item.id)
        if (res && res.code === 1) {
          this.$message.success(this.$t('brokerAccounts.cryptoSection.deleteSuccess'))
          this.loadCredentials()
        } else {
          this.$message.error((res && res.msg) || this.$t('brokerAccounts.cryptoSection.deleteFailed'))
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('brokerAccounts.cryptoSection.deleteFailed'))
      }
    }
  }
}
</script>

<style lang="less" scoped>
.crypto-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  margin-bottom: 16px;
}
.crypto-card.theme-dark {
  background: #1f1f1f;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
}
.crypto-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.crypto-card-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f1f1f;
  display: flex;
  align-items: center;
  gap: 8px;
}
.crypto-card-title-icon { color: #1890ff; font-size: 18px; }
.crypto-card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
  max-width: 600px;
  line-height: 1.55;
}
.crypto-card.theme-dark {
  .crypto-card-title { color: rgba(255, 255, 255, 0.92); }
  .crypto-card-subtitle { color: rgba(255, 255, 255, 0.55); }
}
.crypto-card-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.crypto-empty {
  text-align: center;
  padding: 32px 16px;
  color: #8c8c8c;
  i { font-size: 28px; color: #d9d9d9; display: block; margin-bottom: 10px; }
}
.crypto-empty-text { font-size: 13px; margin-bottom: 6px; }
.crypto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 10px;
}
.crypto-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #eef0f3;
  border-radius: 10px;
  background: linear-gradient(135deg, #ffffff 0%, #fafbfd 100%);
  transition: border-color 0.2s, transform 0.12s;
}
.crypto-item:hover {
  border-color: rgba(24, 144, 255, 0.4);
  transform: translateY(-1px);
}
.crypto-card.theme-dark .crypto-item {
  background: linear-gradient(135deg, #262626 0%, #1f1f1f 100%);
  border-color: #303030;
  &:hover { border-color: rgba(88, 166, 255, 0.4); }
}
.crypto-item-icon {
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.crypto-item-meta {
  flex: 1;
  min-width: 0;
}
.crypto-item-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f1f1f;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.crypto-card.theme-dark .crypto-item-name { color: rgba(255, 255, 255, 0.92); }
.crypto-item-sep { color: #bfbfbf; }
.crypto-item-alias { color: #595959; font-weight: 500; }
.crypto-card.theme-dark .crypto-item-alias { color: rgba(255, 255, 255, 0.7); }
.crypto-item-line {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 11px;
  color: #8c8c8c;
}
.crypto-card.theme-dark .crypto-item-line { color: rgba(255, 255, 255, 0.55); }
.crypto-item-badge {
  margin: 0;
  font-size: 10px;
  line-height: 16px;
  padding: 0 6px;
}
.crypto-item-hint {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.crypto-item-time { color: #bfbfbf; font-size: 11px; }
.crypto-card.theme-dark .crypto-item-time { color: rgba(255, 255, 255, 0.4); }
.crypto-item-actions { flex-shrink: 0; }
.crypto-item-delete { color: #cf1322; }
</style>
