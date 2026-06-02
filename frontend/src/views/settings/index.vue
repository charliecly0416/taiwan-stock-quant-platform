<template>
  <div class="settings-page" :class="{ 'theme-dark': isDarkTheme }">
    <!-- 重启提示 -->
    <a-alert
      v-if="showRestartTip"
      class="restart-alert"
      type="warning"
      showIcon
      closable
      @close="showRestartTip = false"
    >
      <template slot="message">
        <span>{{ $t('settings.restartRequired') }}</span>
        <a-button size="small" type="link" @click="copyRestartCommand">
          {{ $t('settings.copyRestartCmd') }}
        </a-button>
      </template>
    </a-alert>

    <div class="settings-header">
      <h2 class="page-title">
        <a-icon type="setting" />
        <span>{{ $t('settings.title') }}</span>
      </h2>
      <p class="page-desc">{{ $t('settings.description') }}</p>
    </div>

    <a-spin :spinning="loading">
      <div class="settings-layout">
        <!-- 左侧分组导航 -->
        <aside class="settings-nav">
          <div class="settings-search">
            <a-input
              v-model="searchKeyword"
              :placeholder="searchPlaceholder"
              allowClear
            >
              <a-icon slot="prefix" type="search" />
            </a-input>
          </div>
          <a-menu
            mode="inline"
            :selected-keys="[activeGroupKey]"
            class="settings-menu"
            @click="onMenuClick"
          >
            <a-menu-item
              v-for="(group, groupKey) in sortedSchema"
              :key="groupKey"
            >
              <a-icon :type="group.icon || getGroupIcon(groupKey)" />
              <span>{{ getGroupTitle(groupKey, group.title) }}</span>
            </a-menu-item>
          </a-menu>
        </aside>

        <!-- 右侧详情区 -->
        <section class="settings-detail">
          <!-- 搜索模式：摊平展示所有命中项 -->
          <div v-if="searchKeyword.trim()" class="settings-detail-inner">
            <div class="detail-header">
              <a-icon type="search" class="detail-icon" />
              <h3 class="detail-title">
                {{ searchResultsTitle }}
              </h3>
            </div>
            <a-empty
              v-if="searchResults.length === 0"
              :description="emptySearchLabel"
              style="margin-top: 48px;"
            />
            <a-form v-else :form="form" layout="vertical" class="settings-form">
              <a-row :gutter="24">
                <a-col
                  v-for="entry in searchResults"
                  :key="entry.item.key"
                  :xs="24"
                  :sm="24"
                  :md="12"
                  :lg="12"
                >
                  <div class="search-result-group-tag">
                    <a-icon :type="getGroupIcon(entry.groupKey)" />
                    {{ getGroupTitle(entry.groupKey, entry.groupTitle) }}
                  </div>
                  <a-form-item>
                    <template slot="label">
                      <span class="form-label-with-tooltip">
                        <span class="label-text">{{ getItemLabel(entry.groupKey, entry.item) }}</span>
                        <a-tooltip v-if="entry.item.description" placement="top">
                          <template slot="title">
                            {{ getItemDescription(entry.groupKey, entry.item) }}
                          </template>
                          <a-icon type="question-circle" class="help-icon" />
                        </a-tooltip>
                        <a
                          v-if="entry.item.link"
                          :href="entry.item.link"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="api-link"
                          @click.stop
                        >
                          <a-icon type="link" />
                          {{ getLinkText(entry.item.link_text) }}
                        </a>
                      </span>
                    </template>
                    <template v-if="entry.item.type === 'text'">
                      <a-input
                        v-decorator="[entry.item.key, { initialValue: getFieldValue(entry.groupKey, entry.item.key) }]"
                        :placeholder="entry.item.default ? `${$t('settings.default')}: ${entry.item.default}` : ''"
                        allowClear
                      />
                    </template>
                    <template v-else-if="entry.item.type === 'password'">
                      <div class="password-field">
                        <a-input
                          v-decorator="[entry.item.key, { initialValue: getFieldValue(entry.groupKey, entry.item.key) }]"
                          :type="passwordVisible[entry.item.key] ? 'text' : 'password'"
                          :placeholder="$t('settings.inputApiKey')"
                          allowClear
                        >
                          <a-icon
                            slot="suffix"
                            :type="passwordVisible[entry.item.key] ? 'eye' : 'eye-invisible'"
                            @click="togglePasswordVisible(entry.item.key)"
                            style="cursor: pointer"
                          />
                        </a-input>
                      </div>
                    </template>
                    <template v-else-if="entry.item.type === 'number'">
                      <a-input-number
                        v-decorator="[entry.item.key, { initialValue: getNumberValue(entry.groupKey, entry.item.key, entry.item.default) }]"
                        :placeholder="entry.item.default ? `${$t('settings.default')}: ${entry.item.default}` : ''"
                        style="width: 100%"
                      />
                    </template>
                    <template v-else-if="entry.item.type === 'boolean'">
                      <a-switch
                        v-decorator="[entry.item.key, { valuePropName: 'checked', initialValue: getBoolValue(entry.groupKey, entry.item.key, entry.item.default) }]"
                      />
                    </template>
                    <template v-else-if="entry.item.type === 'select'">
                      <a-select
                        v-decorator="[entry.item.key, { initialValue: getFieldValue(entry.groupKey, entry.item.key) || entry.item.default }]"
                        :placeholder="entry.item.default ? `${$t('settings.default')}: ${entry.item.default}` : $t('settings.pleaseSelect')"
                      >
                        <a-select-option
                          v-for="opt in getSelectOptions(entry.item)"
                          :key="opt.value"
                          :value="opt.value"
                        >
                          {{ opt.label }}
                        </a-select-option>
                      </a-select>
                    </template>
                    <div class="field-default" v-if="entry.item.default && entry.item.type !== 'boolean' && entry.item.type !== 'password'">
                      {{ $t('settings.default') }}: {{ entry.item.default }}
                    </div>
                  </a-form-item>
                </a-col>
              </a-row>
            </a-form>
          </div>

          <!-- 正常模式：只显示当前选中分组 -->
          <div v-else-if="currentGroup" class="settings-detail-inner">
            <div class="detail-header">
              <a-icon :type="currentGroup.icon || getGroupIcon(activeGroupKey)" class="detail-icon" />
              <h3 class="detail-title">
                {{ getGroupTitle(activeGroupKey, currentGroup.title) }}
              </h3>
            </div>

            <!-- AI 组特殊：显示 OpenRouter 余额查询卡片 -->
            <div v-if="activeGroupKey === 'ai'" class="openrouter-balance-card">
              <a-card size="small" :bordered="false">
                <div class="balance-header">
                  <span class="balance-title">
                    <a-icon type="wallet" style="margin-right: 6px;" />
                    {{ $t('settings.openrouterBalance') || 'OpenRouter 账户余额' }}
                  </span>
                  <a-button size="small" type="primary" ghost :loading="balanceLoading" @click="queryOpenRouterBalance">
                    <a-icon type="sync" />
                    {{ $t('settings.queryBalance') || '查询余额' }}
                  </a-button>
                </div>
                <div v-if="openrouterBalance" class="balance-info">
                  <a-row :gutter="16">
                    <a-col :span="8">
                      <a-statistic
                        :title="$t('settings.balanceUsage') || '已使用'"
                        :value="openrouterBalance.usage"
                        prefix="$"
                        :precision="4"
                        :value-style="{ color: '#cf1322' }"
                      />
                    </a-col>
                    <a-col :span="8">
                      <a-statistic
                        :title="$t('settings.balanceRemaining') || '剩余额度'"
                        :value="openrouterBalance.limit_remaining !== null ? openrouterBalance.limit_remaining : '∞'"
                        :prefix="openrouterBalance.limit_remaining !== null ? '$' : ''"
                        :precision="openrouterBalance.limit_remaining !== null ? 4 : 0"
                        :value-style="{ color: openrouterBalance.limit_remaining !== null && openrouterBalance.limit_remaining < 1 ? '#cf1322' : '#3f8600' }"
                      />
                    </a-col>
                    <a-col :span="8">
                      <a-statistic
                        :title="$t('settings.balanceLimit') || '总限额'"
                        :value="openrouterBalance.limit !== null ? openrouterBalance.limit : '∞'"
                        :prefix="openrouterBalance.limit !== null ? '$' : ''"
                        :precision="openrouterBalance.limit !== null ? 2 : 0"
                      />
                    </a-col>
                  </a-row>
                  <div v-if="openrouterBalance.is_free_tier" class="free-tier-badge">
                    <a-tag color="blue">{{ $t('settings.freeTier') }}</a-tag>
                  </div>
                </div>
                <div v-else class="balance-empty">
                  <a-icon type="info-circle" style="margin-right: 6px;" />
                  {{ $t('settings.balanceNotQueried') || '点击"查询余额"获取账户信息' }}
                </div>
              </a-card>
            </div>

            <a-form :form="form" layout="vertical" class="settings-form">
              <a-row :gutter="24">
                <a-col
                  :xs="24"
                  :sm="24"
                  :md="12"
                  :lg="12"
                  v-for="item in currentGroup.items"
                  :key="item.key"
                >
                  <a-form-item>
                    <template slot="label">
                      <span class="form-label-with-tooltip">
                        <span class="label-text">{{ getItemLabel(activeGroupKey, item) }}</span>
                        <a-tooltip v-if="item.description" placement="top">
                          <template slot="title">
                            {{ getItemDescription(activeGroupKey, item) }}
                          </template>
                          <a-icon type="question-circle" class="help-icon" />
                        </a-tooltip>
                        <a
                          v-if="item.link"
                          :href="item.link"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="api-link"
                          @click.stop
                        >
                          <a-icon type="link" />
                          {{ getLinkText(item.link_text) }}
                        </a>
                      </span>
                    </template>
                    <template v-if="item.type === 'text'">
                      <a-input
                        v-decorator="[item.key, { initialValue: getFieldValue(activeGroupKey, item.key) }]"
                        :placeholder="item.default ? `${$t('settings.default')}: ${item.default}` : ''"
                        allowClear
                      />
                    </template>
                    <template v-else-if="item.type === 'password'">
                      <div class="password-field">
                        <a-input
                          v-decorator="[item.key, { initialValue: getFieldValue(activeGroupKey, item.key) }]"
                          :type="passwordVisible[item.key] ? 'text' : 'password'"
                          :placeholder="$t('settings.inputApiKey')"
                          allowClear
                        >
                          <a-icon
                            slot="suffix"
                            :type="passwordVisible[item.key] ? 'eye' : 'eye-invisible'"
                            @click="togglePasswordVisible(item.key)"
                            style="cursor: pointer"
                          />
                        </a-input>
                      </div>
                    </template>
                    <template v-else-if="item.type === 'number'">
                      <a-input-number
                        v-decorator="[item.key, { initialValue: getNumberValue(activeGroupKey, item.key, item.default) }]"
                        :placeholder="item.default ? `${$t('settings.default')}: ${item.default}` : ''"
                        style="width: 100%"
                      />
                    </template>
                    <template v-else-if="item.type === 'boolean'">
                      <a-switch
                        v-decorator="[item.key, { valuePropName: 'checked', initialValue: getBoolValue(activeGroupKey, item.key, item.default) }]"
                      />
                    </template>
                    <template v-else-if="item.type === 'select'">
                      <a-select
                        v-decorator="[item.key, { initialValue: getFieldValue(activeGroupKey, item.key) || item.default }]"
                        :placeholder="item.default ? `${$t('settings.default')}: ${item.default}` : $t('settings.pleaseSelect')"
                      >
                        <a-select-option
                          v-for="opt in getSelectOptions(item)"
                          :key="opt.value"
                          :value="opt.value"
                        >
                          {{ opt.label }}
                        </a-select-option>
                      </a-select>
                    </template>
                    <div class="field-default" v-if="item.default && item.type !== 'boolean' && item.type !== 'password'">
                      {{ $t('settings.default') }}: {{ item.default }}
                    </div>
                  </a-form-item>
                </a-col>
              </a-row>
            </a-form>

            <!-- Brand group footer: commercial license notice. Shown only
                 under "Brand & Identity" so it's visible right where an
                 operator sets up their fork. Single official email channel
                 to avoid impersonation risk via informal IM handles. -->
            <div v-if="activeGroupKey === 'brand'" class="commercial-license-notice">
              <a-alert
                type="warning"
                show-icon
                :message="$t('settings.commercialLicense.title')"
              >
                <div slot="description" class="license-body">
                  <p>{{ $t('settings.commercialLicense.body') }}</p>
                  <p class="license-contact">
                    <span class="contact-label">{{ $t('settings.commercialLicense.contactLabel') }}:</span>
                    <a href="mailto:support@quantdinger.com" class="contact-link">
                      <a-icon type="mail" /> support@quantdinger.com
                    </a>
                  </p>
                </div>
              </a-alert>
            </div>
          </div>
        </section>
      </div>
    </a-spin>

    <div class="settings-footer">
      <a-button @click="handleReset" :disabled="saving">
        <a-icon type="undo" />
        {{ $t('settings.reset') }}
      </a-button>
      <a-button type="primary" @click="handleSave" :loading="saving">
        <a-icon type="save" />
        {{ $t('settings.save') }}
      </a-button>
    </div>
  </div>
</template>

<script>
import { getSettingsSchema, getSettingsValues, saveSettings, getOpenRouterBalance } from '@/api/settings'
import { baseMixin } from '@/store/app-mixin'

export default {
  name: 'Settings',
  mixins: [baseMixin],
  data () {
    return {
      loading: false,
      saving: false,
      schema: {},
      values: {},
      // The vertically-listed group currently selected in the left nav.
      // Defaults to the first group in ``sortedSchema`` once data arrives.
      activeGroupKey: '',
      // Free-text search across every group / item. Non-empty value switches
      // the right-side detail pane into "search results" mode.
      searchKeyword: '',
      passwordVisible: {},
      showRestartTip: false,
      // OpenRouter 余额
      balanceLoading: false,
      openrouterBalance: null
    }
  },
  computed: {
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    // 按 order 排序的 schema
    sortedSchema () {
      const entries = Object.entries(this.schema)
      entries.sort((a, b) => {
        const orderA = a[1].order || 999
        const orderB = b[1].order || 999
        return orderA - orderB
      })
      const sorted = {}
      for (const [key, value] of entries) {
        sorted[key] = value
      }
      return sorted
    },
    // Currently selected group object (right-side detail content).
    currentGroup () {
      return this.sortedSchema[this.activeGroupKey] || null
    },
    // Flattened, filtered search hits. Match is case-insensitive against the
    // localized label, the localized description and the raw ENV key, so
    // operators can search by either UI text or .env name.
    searchResults () {
      const kw = this.searchKeyword.trim().toLowerCase()
      if (!kw) return []
      const out = []
      for (const [groupKey, group] of Object.entries(this.sortedSchema)) {
        for (const item of (group.items || [])) {
          const label = (this.getItemLabel(groupKey, item) || '').toLowerCase()
          const desc = (this.getItemDescription(groupKey, item) || '').toLowerCase()
          const key = (item.key || '').toLowerCase()
          if (label.includes(kw) || desc.includes(kw) || key.includes(kw)) {
            out.push({ groupKey, groupTitle: group.title, item })
          }
        }
      }
      return out
    },
    // Localized strings — $t returns the key itself when missing, so we
    // detect that explicitly to fall back to English.
    searchPlaceholder () {
      const k = 'settings.search.placeholder'
      const t = this.$t(k)
      return (t && t !== k) ? t : 'Search settings…'
    },
    searchResultsTitle () {
      const k = 'settings.search.results'
      const t = this.$t(k)
      const tpl = (t && t !== k) ? t : 'Search results ({count})'
      return tpl.replace('{count}', String(this.searchResults.length))
    },
    emptySearchLabel () {
      const k = 'settings.search.empty'
      const t = this.$t(k)
      return (t && t !== k) ? t : 'No matching settings'
    }
  },
  beforeCreate () {
    this.form = this.$form.createForm(this)
  },
  mounted () {
    this.loadSettings()
  },
  methods: {
    // Left-nav click: switch the currently displayed group.  Clearing the
    // search keyword on group change matches user intent ("I navigated, I'm
    // not in search-mode anymore").
    onMenuClick ({ key }) {
      this.activeGroupKey = key
      this.searchKeyword = ''
    },
    // 兼容后端 schema options 两种格式：
    // - string[]: ['openrouter','openai', ...]
    // - {value,label}[]: [{value:'openrouter',label:'OpenRouter'}, ...]
    getSelectOptions (item) {
      const options = item && Array.isArray(item.options) ? item.options : []
      const arr = options
      return arr.map(opt => {
        const optObj = (opt && typeof opt === 'object')
          ? { value: opt.value != null ? String(opt.value) : '', label: opt.label != null ? String(opt.label) : String(opt.value || '') }
          : { value: String(opt), label: String(opt) }
        // Try i18n first: settings.option.<ITEM_KEY>.<value>
        const i18nKey = item && item.key ? `settings.option.${item.key}.${optObj.value}` : ''
        if (i18nKey) {
          const translated = this.$t(i18nKey)
          if (translated && translated !== i18nKey) {
            optObj.label = translated
          }
        }
        if (opt && typeof opt === 'object') {
          return optObj
        }
        return optObj
      }).filter(o => o.value !== '')
    },
    async loadSettings () {
      this.loading = true
      try {
        const [schemaRes, valuesRes] = await Promise.all([
          getSettingsSchema(),
          getSettingsValues()
        ])

        if (schemaRes.code === 1) {
          this.schema = schemaRes.data
        }

        if (valuesRes.code === 1) {
          this.values = valuesRes.data
        }

        // After a fresh load: if no group has been picked yet (first mount)
        // or the previously active key disappeared, fall back to the first
        // group in display order.  This avoids a blank right pane.
        const keys = Object.keys(this.sortedSchema)
        if (keys.length && (!this.activeGroupKey || !keys.includes(this.activeGroupKey))) {
          this.activeGroupKey = keys[0]
        }
      } catch (error) {
        this.$message.error(this.$t('settings.loadFailed'))
      } finally {
        this.loading = false
      }
    },

    // 查询 OpenRouter 余额
    async queryOpenRouterBalance () {
      this.balanceLoading = true
      try {
        const res = await getOpenRouterBalance()
        if (res.code === 1 && res.data) {
          this.openrouterBalance = res.data
          this.$message.success(this.$t('settings.balanceQuerySuccess') || '余额查询成功')
        } else {
          this.$message.error(res.msg || this.$t('settings.balanceQueryFailed') || '余额查询失败')
        }
      } catch (error) {
        this.$message.error(this.$t('settings.balanceQueryFailed') || '余额查询失败')
      } finally {
        this.balanceLoading = false
      }
    },

    getGroupIcon (groupKey) {
      const icons = {
        brand: 'crown',
        contact: 'customer-service',
        social: 'team',
        legal: 'safety-certificate',
        auth: 'lock',
        email: 'mail',
        sms: 'phone',
        network: 'global',
        app: 'appstore',
        ai: 'robot',
        trading: 'stock',
        data_source: 'database',
        search: 'search',
        agent: 'experiment',
        security: 'safety',
        billing: 'dollar'
      }
      return icons[groupKey] || 'setting'
    },

    getGroupTitle (groupKey, defaultTitle) {
      const key = `settings.group.${groupKey}`
      const translated = this.$t(key)
      return translated !== key ? translated : defaultTitle
    },

    getItemLabel (groupKey, item) {
      const key = `settings.field.${item.key}`
      const translated = this.$t(key)
      return translated !== key ? translated : item.label
    },

    getItemDescription (groupKey, item) {
      // 先尝试从多语言获取描述
      const key = `settings.desc.${item.key}`
      const translated = this.$t(key)
      if (translated !== key) {
        return translated
      }
      // 回退到后端返回的描述
      return item.description || ''
    },

    getLinkText (linkText) {
      if (!linkText) return this.$t('settings.getApi')
      // 如果是翻译键（以 settings.link. 开头），则翻译
      if (linkText.startsWith('settings.link.')) {
        const translated = this.$t(linkText)
        return translated !== linkText ? translated : linkText
      }
      return linkText
    },

    getFieldValue (groupKey, key) {
      const groupValues = this.values[groupKey] || {}
      return groupValues[key] || ''
    },

    togglePasswordVisible (key) {
      this.$set(this.passwordVisible, key, !this.passwordVisible[key])
    },

    getNumberValue (groupKey, key, defaultVal) {
      const val = this.getFieldValue(groupKey, key)
      if (val === '' || val === null || val === undefined) {
        return defaultVal ? parseFloat(defaultVal) : null
      }
      return parseFloat(val)
    },

    getBoolValue (groupKey, key, defaultVal) {
      const val = this.getFieldValue(groupKey, key)
      if (val === '' || val === null || val === undefined) {
        return defaultVal === 'True' || defaultVal === 'true' || defaultVal === true
      }
      return val === 'True' || val === 'true' || val === true
    },

    handleReset () {
      this.form.resetFields()
      this.loadSettings()
    },

    copyRestartCommand () {
      const cmd = 'cd backend && py run.py'
      navigator.clipboard.writeText(cmd).then(() => {
        this.$message.success(this.$t('settings.copySuccess'))
      }).catch(() => {
        this.$message.error(this.$t('settings.copyFailed'))
      })
    },

    async handleSave () {
      this.form.validateFields(async (err, formValues) => {
        if (err) {
          return
        }

        this.saving = true
        try {
          // 按组整理数据
          const data = {}
          for (const groupKey of Object.keys(this.schema)) {
            data[groupKey] = {}
            const group = this.schema[groupKey]
            for (const item of group.items) {
              if (item.key in formValues) {
                let value = formValues[item.key]
                // 布尔值转字符串
                if (item.type === 'boolean') {
                  value = value ? 'True' : 'False'
                }
                data[groupKey][item.key] = value
              }
            }
          }

          const res = await saveSettings(data)
          if (res.code === 1) {
            this.$message.success(res.msg || this.$t('settings.saveSuccess'))
            if (res.data && res.data.requires_restart) {
              this.showRestartTip = true
            }
            this.loadSettings()
            // Brand / contact / social / legal live under the same .env. Refresh
            // the global brand store so logo / footer / version label reflect
            // the change without a hard reload.
            this.$store.dispatch('LoadBrandConfig', { force: true }).catch(() => {})
          } else {
            this.$message.error(res.msg || this.$t('settings.saveFailed'))
          }
        } catch (error) {
          this.$message.error(this.$t('settings.saveFailed') + ': ' + error.message)
        } finally {
          this.saving = false
        }
      })
    }
  }
}
</script>

<style lang="less" scoped>
@primary-color: #1890ff;
@success-color: #52c41a;
@border-radius: 12px;
@card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

.settings-page {
  padding: 24px;
  min-height: calc(100vh - 120px);
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);

  .restart-alert {
    margin-bottom: 16px;
    border-radius: 8px;
  }

  .settings-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #1e3a5f;
      display: flex;
      align-items: center;
      gap: 12px;

      .anticon {
        font-size: 28px;
        color: @primary-color;
      }
    }

    .page-desc {
      color: #64748b;
      font-size: 14px;
      margin: 0;
    }
  }

  .settings-layout {
    display: flex;
    gap: 20px;
    margin-bottom: 80px;
    align-items: flex-start;
  }

  .settings-nav {
    // Wide enough for the longest group label in any supported locale
    // (some Chinese / German / Russian group names ran over the previous
    // 240px and forced a horizontal scrollbar in the side rail).
    flex: 0 0 280px;
    position: sticky;
    top: 88px;
    background: #fff;
    border-radius: @border-radius;
    box-shadow: @card-shadow;
    padding: 16px 0;
    max-height: calc(100vh - 200px);
    // Allow vertical scroll for long lists, but never let the side rail
    // grow a horizontal scrollbar — overflow is handled by ellipsis on
    // the menu-item label instead.
    overflow-x: hidden;
    overflow-y: auto;

    .settings-search {
      padding: 0 16px 12px;

      /deep/ .ant-input-affix-wrapper {
        border-radius: 8px;
      }
    }

    .settings-menu {
      border: none;
      background: transparent;

      /deep/ .ant-menu-item {
        margin: 4px 8px;
        border-radius: 8px;
        height: 40px;
        line-height: 40px;
        padding-left: 16px !important;
        padding-right: 12px !important;
        color: #475569;
        font-weight: 500;
        // Ant Design's default for menu-item is to clip long labels,
        // which the browser turns into a horizontal scrollbar on the
        // parent. Force an ellipsis on the label span so overly long
        // group titles degrade gracefully without shifting layout.
        display: flex;
        align-items: center;

        .anticon {
          color: #94a3b8;
          flex: 0 0 auto;
        }

        > span:not(.anticon) {
          flex: 1 1 auto;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        &:hover {
          background: rgba(24, 144, 255, 0.06);
          color: @primary-color;
          .anticon { color: @primary-color; }
        }

        &.ant-menu-item-selected {
          background: linear-gradient(135deg, rgba(24, 144, 255, 0.10), rgba(19, 194, 194, 0.08));
          color: @primary-color;
          font-weight: 600;
          .anticon { color: @primary-color; }

          &::after { display: none; }
        }
      }
    }
  }

  .settings-detail {
    flex: 1 1 auto;
    min-width: 0;
    background: #fff;
    border-radius: @border-radius;
    box-shadow: @card-shadow;
    padding: 24px;

    .settings-detail-inner {
      width: 100%;
    }

    .detail-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid #f0f0f0;

      .detail-icon {
        font-size: 20px;
        color: @primary-color;
      }

      .detail-title {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #1e3a5f;
      }
    }

    .search-result-group-tag {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 4px;
      padding: 2px 8px;
      background: rgba(24, 144, 255, 0.08);
      color: @primary-color;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;

      .anticon {
        font-size: 11px;
      }
    }
  }

  // 商业授权提示（Brand 分组底部）
  .commercial-license-notice {
    margin-top: 24px;

    .license-body {
      margin-top: 4px;
      line-height: 1.7;
      color: #5c4a16;

      p {
        margin: 0 0 8px 0;
      }

      p:last-child {
        margin-bottom: 0;
      }
    }

    .license-contact {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    .contact-label {
      font-weight: 600;
    }

    .contact-link {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      color: #1890ff;
      text-decoration: none;

      &:hover {
        color: #096dd9;
        text-decoration: underline;
      }
    }
  }

  // OpenRouter 余额查询卡片
  .openrouter-balance-card {
    margin-bottom: 20px;

    .ant-card {
      background: linear-gradient(135deg, #e6f7ff 0%, #f0f5ff 100%);
      border: 1px solid #91d5ff;
      border-radius: 8px;
    }

    .balance-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .balance-title {
        font-size: 15px;
        font-weight: 600;
        color: #1890ff;
      }
    }

    .balance-info {
      padding: 8px 0;

      /deep/ .ant-statistic-title {
        font-size: 12px;
        color: #666;
      }

      /deep/ .ant-statistic-content {
        font-size: 18px;
      }

      .free-tier-badge {
        margin-top: 12px;
        text-align: right;
      }
    }

    .balance-empty {
      color: #8c8c8c;
      font-size: 13px;
      padding: 8px 0;
    }
  }

  .settings-form {
    /deep/ .ant-form-item-label {
      padding-bottom: 4px;

      label {
        color: #475569;
        font-weight: 500;
      }

      .form-label-with-tooltip {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;

        .label-text {
          color: #475569;
          font-weight: 500;
        }

        .help-icon {
          font-size: 14px;
          color: #94a3b8;
          cursor: help;
          transition: color 0.2s;

          &:hover {
            color: @primary-color;
          }
        }

        .api-link {
          font-size: 12px;
          font-weight: 400;
          color: @primary-color;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 2px 8px;
          background: rgba(24, 144, 255, 0.08);
          border-radius: 4px;
          transition: all 0.2s;
          margin-left: 4px;

          &:hover {
            background: rgba(24, 144, 255, 0.15);
            color: darken(@primary-color, 10%);
          }

          .anticon {
            font-size: 11px;
          }
        }
      }
    }

    /deep/ .ant-input,
    /deep/ .ant-input-number,
    /deep/ .ant-select-selection {
      border-radius: 8px;
    }

    /deep/ .ant-input-number {
      width: 100%;
    }

    .password-field {
      .field-hint {
        margin-top: 4px;
        font-size: 12px;
        color: @success-color;
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }

    .field-default {
      margin-top: 4px;
      font-size: 12px;
      color: #94a3b8;
    }
  }

  .settings-footer {
    position: fixed;
    bottom: 0;
    left: 208px;
    right: 0;
    padding: 16px 24px;
    background: #fff;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.08);
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    z-index: 100;

    .ant-btn {
      min-width: 100px;
      height: 40px;
      border-radius: 8px;
      font-weight: 500;
    }
  }

  // 暗黑主题
  &.theme-dark {
    background: linear-gradient(180deg, #141414 0%, #1c1c1c 100%);

    .restart-alert {
      background: #1c1c1c;
      border-color: #b08800;
    }

    .commercial-license-notice {
      .license-body {
        color: #f0d97a;
      }
      .contact-link {
        color: #69c0ff;
        &:hover { color: #91d5ff; }
      }
    }

    .settings-header {
      .page-title {
        color: #e0e6ed;
      }

      .page-desc {
        color: #8b949e;
      }
    }

    .settings-nav {
      background: #1c1c1c;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);

      /deep/ .ant-menu-item {
        color: #c9d1d9;
        .anticon { color: #8b949e; }

        &:hover {
          background: rgba(88, 166, 255, 0.12);
          color: #58a6ff;
          .anticon { color: #58a6ff; }
        }

        &.ant-menu-item-selected {
          background: linear-gradient(135deg, rgba(88, 166, 255, 0.18), rgba(19, 194, 194, 0.10));
          color: #58a6ff;
          .anticon { color: #58a6ff; }
        }
      }
    }

    .settings-detail {
      background: #1c1c1c;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);

      .detail-header {
        border-bottom-color: rgba(255, 255, 255, 0.08);

        .detail-icon { color: #58a6ff; }
        .detail-title { color: #e0e6ed; }
      }

      .search-result-group-tag {
        background: rgba(88, 166, 255, 0.18);
        color: #58a6ff;
      }
    }

    .settings-form {
      /deep/ .ant-form-item-label {
        label {
          color: #c9d1d9;
        }

        .form-label-with-tooltip {
          .label-text {
            color: #c9d1d9;
          }

          .help-icon {
            color: #6e7681;

            &:hover {
              color: #58a6ff;
            }
          }

          .api-link {
            background: rgba(24, 144, 255, 0.15);
            color: #58a6ff;

            &:hover {
              background: rgba(24, 144, 255, 0.25);
            }
          }
        }
      }

      /deep/ .ant-input,
      /deep/ .ant-input-password,
      /deep/ .ant-input-number,
      /deep/ .ant-select-selection {
        background: #141414;
        border-color: #2a2a2a;
        color: #c9d1d9;

        &:hover,
        &:focus {
          border-color: @primary-color;
        }
      }

      /deep/ .ant-input-number-input {
        background: transparent;
        color: #c9d1d9;
      }

      /deep/ .ant-select-arrow {
        color: #8b949e;
      }

      // Input trailing icons in dark mode (eye/clear/spinner) should stay readable
      /deep/ .ant-input-suffix .anticon,
      /deep/ .ant-input-clear-icon,
      /deep/ .ant-input-clear-icon .anticon,
      /deep/ .ant-input-number-handler-wrap {
        color: #8b949e;
      }

      /deep/ .ant-input-suffix .anticon:hover,
      /deep/ .ant-input-clear-icon:hover,
      /deep/ .ant-input-number-handler:hover .ant-input-number-handler-up-inner,
      /deep/ .ant-input-number-handler:hover .ant-input-number-handler-down-inner {
        color: #58a6ff;
      }

      .field-default {
        color: #6e7681;
      }
    }

    .settings-footer {
      background: #1c1c1c;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.25);
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .settings-page {
    padding: 16px;

    .settings-layout {
      flex-direction: column;
      gap: 12px;
    }

    .settings-nav {
      flex: 0 0 auto;
      position: static;
      width: 100%;
      max-height: 280px;
    }

    .settings-detail {
      padding: 16px;
    }

    .settings-footer {
      left: 0;
      padding: 12px 16px;
    }
  }
}
</style>
