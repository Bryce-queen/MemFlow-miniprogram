// 记忆外挂 — 我的页
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    stats: null,
    apiBase: '',
    apiHealth: null,
    tags: [],
  },

  onShow() {
    this.setData({ apiBase: app.globalData.apiBase })
    this.loadData()
  },

  async loadData() {
    try {
      const [stats, health, tags] = await Promise.all([
        api.getStats().catch(() => null),
        api.healthCheck().catch(() => null),
        api.getTags().catch(() => []),
      ])
      this.setData({
        stats,
        apiHealth: health,
        tags,
      })
    } catch (e) {
      // ignore
    }
  },

  // ── API 配置 ──
  onApiInput(e) {
    this.setData({ apiBase: e.detail.value })
  },

  onSaveApi() {
    const base = this.data.apiBase.trim().replace(/\/+$/, '')
    if (!base) return
    app.globalData.apiBase = base
    wx.setStorageSync('apiBase', base)
    this.setData({ apiHealth: null })
    wx.showToast({ title: '已保存', icon: 'success' })
    this.loadData()
  },

  // ── 离线同步 ──
  async onSyncOffline() {
    const offline = wx.getStorageSync('offline_memories') || []
    if (!offline.length) {
      wx.showToast({ title: '没有待同步的记忆', icon: 'none' })
      return
    }

    wx.showLoading({ title: `同步中 0/${offline.length}` })
    let synced = 0
    for (let i = 0; i < offline.length; i++) {
      try {
        await api.createMemory({
          content: offline[i].content,
          source: offline[i].source || 'text',
        })
        synced++
        wx.showLoading({ title: `同步中 ${synced}/${offline.length}` })
      } catch (e) {
        break
      }
    }

    wx.hideLoading()
    if (synced > 0) {
      const remaining = offline.slice(synced)
      wx.setStorageSync('offline_memories', remaining)
      wx.showToast({ title: `已同步 ${synced} 条`, icon: 'success' })
    } else {
      wx.showToast({ title: '同步失败', icon: 'none' })
    }
  },

  // ── 导出 ──
  onExport() {
    wx.showToast({ title: '导出功能开发中', icon: 'none' })
  },

  onTagTap(e) {
    const tag = e.currentTarget.dataset.tag
    app.globalData.searchTag = tag
    wx.switchTab({ url: '/pages/search/search' })
  },
})
