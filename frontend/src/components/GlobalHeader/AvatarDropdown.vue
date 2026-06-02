<template>
  <a-dropdown v-if="currentUser && currentUser.name" placement="bottomRight">
    <span class="ant-pro-account-avatar">
      <a-avatar size="small" :src="currentUser.avatar" class="antd-pro-global-header-index-avatar" />
      <span>{{ currentUser.name }}</span>
    </span>
    <!--
      ant-design-vue 1.x (Vue 2) only recognises the legacy ``slot="overlay"``
      attribute here; using the Vue 2.6 ``<template #overlay>`` shorthand
      silently degrades to a default slot, which renders the menu items
      inline next to the avatar inside the flex header. Keep this attribute
      style and the explicit ``mode="vertical"`` on the menu as a belt-and-
      braces guarantee the dropdown stays vertical.
    -->
    <a-menu slot="overlay" mode="vertical" class="ant-pro-drop-down menu" :selected-keys="[]">
      <a-menu-item key="profile" @click="handleProfile">
        <a-icon type="user" />
        {{ $t('menu.profile') || 'My Profile' }}
      </a-menu-item>
      <a-menu-item key="exchanges" @click="handleExchanges">
        <a-icon type="api" />
        {{ $t('menu.account.myExchanges') || $t('profile.exchange.title') || 'My Exchanges' }}
      </a-menu-item>
      <a-menu-divider />
      <a-menu-item key="logout" @click="handleLogout">
        <a-icon type="logout" />
        {{ $t('menu.account.logout') }}
      </a-menu-item>
    </a-menu>
  </a-dropdown>
  <span v-else>
    <a-spin size="small" :style="{ marginLeft: 8, marginRight: 8 }" />
  </span>
</template>

<script>
import { Modal } from 'ant-design-vue'

export default {
  name: 'AvatarDropdown',
  props: {
    currentUser: {
      type: Object,
      default: () => null
    },
    menu: {
      type: Boolean,
      default: true
    }
  },
  methods: {
    handleProfile () {
      this.$router.push({ name: 'Profile' })
    },
    handleExchanges () {
      // Deep-link straight to the Exchange Config tab inside Profile so
      // users don't have to hunt for it in the tab strip. Profile reads
      // ``$route.query.tab`` on mount and on subsequent navigations.
      this.$router.push({ name: 'Profile', query: { tab: 'exchange' } }).catch(() => {})
    },
    handleLogout (e) {
      Modal.confirm({
        title: this.$t('layouts.usermenu.dialog.title'),
        content: this.$t('layouts.usermenu.dialog.content'),
        onOk: () => {
          // return new Promise((resolve, reject) => {
          //   setTimeout(Math.random() > 0.5 ? resolve : reject, 1500)
          // }).catch(() => console.log('Oops errors!'))
          return this.$store.dispatch('Logout').then(() => {
            this.$router.push({ name: 'login' })
          })
        },
        onCancel () {}
      })
    }
  }
}
</script>

<style lang="less">
.ant-pro-drop-down {
  .action {
    margin-right: 8px;
  }
  .ant-dropdown-menu-item {
    min-width: 160px;
  }
}

/* 暗黑主题 - 下拉菜单样式 */
body.dark .ant-dropdown-menu,
body.realdark .ant-dropdown-menu,
.ant-layout.dark .ant-dropdown-menu,
.ant-layout.realdark .ant-dropdown-menu,
.ant-pro-layout.dark .ant-dropdown-menu,
.ant-pro-layout.realdark .ant-dropdown-menu {
  background-color: #1f1f1f;
  border: 1px solid #303030;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

  .ant-dropdown-menu-item {
    color: rgba(255, 255, 255, 0.85);

    &:hover,
    &.ant-dropdown-menu-item-selected {
      background-color: #262626;
      color: #1890ff;
    }

    .anticon {
      color: rgba(255, 255, 255, 0.85);
    }
  }

  .ant-dropdown-menu-item-divider {
    background-color: #303030;
  }
}
</style>
