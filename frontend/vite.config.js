import { defineConfig, loadEnv } from 'vite'
import vue2 from '@vitejs/plugin-vue2'
import vue2Jsx from '@vitejs/plugin-vue2-jsx'
import svgLoader from 'vite-svg-loader'
import { viteMockServe } from 'vite-plugin-mock'
import { fileURLToPath, URL } from 'node:url'
import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8'))

const gitHash = (() => {
  try {
    return execSync('git rev-parse --short HEAD').toString().trim()
  } catch (e) {
    return 'unknown'
  }
})()

const buildDate = new Date().toLocaleString()

const proLayoutBasicLayoutShim = fileURLToPath(new URL('./src/shims/pro-layout/BasicLayout.less', import.meta.url))

function proLayoutLessShim () {
  return {
    name: 'pro-layout-less-shim',
    enforce: 'pre',
    resolveId (source, importer) {
      if (source === './BasicLayout.less' && importer && importer.includes(`${path.sep}@ant-design-vue${path.sep}pro-layout${path.sep}es${path.sep}BasicLayout.js`)) {
        return proLayoutBasicLayoutShim
      }
      return null
    }
  }
}


export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const enableMock = env.VITE_ENABLE_MOCK === 'true'

  return {
    base: './',
    resolve: {
      alias: [
        // webpack 风格的 ~package/... less @import → 直接命中 node_modules
        { find: /^~(.+)/, replacement: '$1' },
        // pro-layout 1.x 仍引用 webpack 专用插件 client，用 shim 兼容
        { find: 'webpack-theme-color-replacer/client', replacement: fileURLToPath(new URL('./src/shims/webpack-theme-color-replacer-client.js', import.meta.url)) },
        // moment 纯 CJS（module.exports = ctor），Vite 下 `import * as moment from 'moment'`
        // namespace 拿不到 isMoment 等静态方法 → 走 shim 平铺 named exports
        { find: /^moment$/, replacement: fileURLToPath(new URL('./src/shims/moment.js', import.meta.url)) },
        { find: /^store$/, replacement: 'store/dist/store.modern.js' },
        { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
        { find: '@$', replacement: fileURLToPath(new URL('./src', import.meta.url)) }
      ],
      // 兼容旧代码中省略 .vue 后缀的 import（如 `import App from './App'`）
      extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue']
    },
    define: {
      APP_VERSION: JSON.stringify(pkg.version),
      GIT_HASH: JSON.stringify(gitHash),
      BUILD_DATE: JSON.stringify(buildDate),
      // 兼容旧代码中的 process.env.VUE_APP_* 引用 —— 直接映射到 import.meta.env.VITE_*
      'process.env.VUE_APP_PREVIEW': JSON.stringify(env.VITE_PREVIEW || ''),
      'process.env.VUE_APP_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || ''),
      'process.env.VUE_APP_PYTHON_API_BASE_URL': JSON.stringify(env.VITE_PYTHON_API_BASE_URL || ''),
      'process.env.VUE_APP_PYODIDE_CDN_BASE': JSON.stringify(env.VITE_PYODIDE_CDN_BASE || ''),
      'process.env.VUE_APP_PYODIDE_LOCAL_BASE': JSON.stringify(env.VITE_PYODIDE_LOCAL_BASE || ''),
      'process.env.VUE_APP_PYODIDE_PREFER_CDN': JSON.stringify(env.VITE_PYODIDE_PREFER_CDN || '')
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          modifyVars: {
            'border-radius-base': '2px'
          }
        }
      }
    },
    plugins: [
      proLayoutLessShim(),
      vue2(),
      vue2Jsx(),
      svgLoader({ defaultImport: 'url' }),
      viteMockServe({
        mockPath: 'src/mock/services',
        enable: enableMock,
        watchFiles: true,
        logger: true
      })
    ],
    server: {
      port: 8000,
      proxy: {
        '/api': {
          target: env.VITE_DEV_PROXY_TARGET || 'http://localhost:5000',
          ws: true,
          changeOrigin: true,
          timeout: 600000,
          proxyTimeout: 600000
        }
      }
    },
    worker: {
      format: 'es'
    },
    optimizeDeps: {
      // pyodide 自己通过 Worker 内 importScripts 加载，不参与 Vite 预构建
      exclude: ['pyodide']
    },
    build: {
      target: 'es2020',
      sourcemap: false,
      chunkSizeWarningLimit: 1500,
      commonjsOptions: {
        transformMixedEsModules: true
      },
      rollupOptions: {
        output: {
          manualChunks (id) {
            if (!id.includes('node_modules')) return undefined
            if (/[\\/]node_modules[\\/](vue|vue-router|vuex|vue-i18n)[\\/]/.test(id)) return 'vue-core'
            if (id.includes(`${path.sep}ant-design-vue${path.sep}`) || id.includes(`${path.sep}@ant-design${path.sep}icons`)) return 'ant-design-vue'
            if (id.includes(`${path.sep}echarts${path.sep}`) || id.includes(`${path.sep}@antv${path.sep}data-set${path.sep}`) || id.includes(`${path.sep}viser-vue${path.sep}`)) return 'charts'
            if (id.includes(`${path.sep}klinecharts${path.sep}`)) return 'klinecharts'
            if (id.includes(`${path.sep}codemirror${path.sep}`)) return 'codemirror'
            if (id.includes(`${path.sep}moment${path.sep}`) || id.endsWith(`${path.sep}src${path.sep}shims${path.sep}moment.js`)) return 'moment'
            return undefined
          }
        }
      }
    }
  }
})
