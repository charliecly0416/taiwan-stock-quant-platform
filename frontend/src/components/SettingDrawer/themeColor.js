// 主色运行时换肤功能已下线（原依赖 webpack-theme-color-replacer，已随 Vite 迁移移除）。
// 当前主色由 vite.config.js 的 less modifyVars 在构建期固定。
// 此文件保留兼容导出，避免 SettingDrawer 引用断裂。
export default {
  getAntdSerials () {
    return []
  },
  changeColor () {
    return Promise.resolve()
  }
}
