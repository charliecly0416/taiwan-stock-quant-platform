// Shim：原 webpack-theme-color-replacer/client 已下线（webpack 专用插件，无 Vite 等价物）。
// pro-layout 1.x 的 dynamicTheme.js 会导入它；这里提供一个 no-op 兼容层，避免构建失败。
const noop = () => {}
const client = {
  varyColor: {
    lighten: (color) => color,
    toNum3: () => [0, 0, 0]
  },
  changer: {
    changeColor: () => Promise.resolve()
  }
}
export default client
export { client, noop }
