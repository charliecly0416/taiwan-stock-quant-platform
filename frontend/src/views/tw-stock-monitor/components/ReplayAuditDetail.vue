<template>
  <a-collapse class="readonly-audit-detail" :bordered="false" :default-active-key="defaultExpanded ? ['audit'] : []" data-testid="readonly-audit-detail">
    <a-collapse-panel key="audit" :header="title">
      <div class="readonly-audit-grid">
        <span v-for="row in normalizedRows" :key="row.label">
          <strong>{{ row.label }}</strong>{{ row.value }}
        </span>
      </div>
    </a-collapse-panel>
  </a-collapse>
</template>

<script>
export default {
  name: 'ReplayAuditDetail',
  props: {
    title: { type: String, default: '查看审计详情' },
    rows: { type: Array, default: () => [] },
    defaultExpanded: { type: Boolean, default: false }
  },
  computed: {
    normalizedRows () {
      return this.rows
        .filter(row => row && row.label)
        .map(row => ({ label: row.label, value: row.value === null || row.value === undefined || row.value === '' ? '-' : row.value }))
    }
  }
}
</script>

<style scoped>
.readonly-audit-detail {
  margin-top: 10px;
  background: #fbfdff;
  border: 1px solid #eef2f7;
  border-radius: 6px;
}
.readonly-audit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 12px;
  font-size: 12px;
}
.readonly-audit-grid span {
  min-width: 0;
  color: #475467;
  overflow-wrap: anywhere;
}
.readonly-audit-grid strong {
  display: block;
  color: #111827;
  font-weight: 600;
}
</style>
