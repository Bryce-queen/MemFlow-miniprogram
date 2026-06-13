// 记忆外挂 — 发现页
const api = require('../../utils/api')
const util = require('../../utils/util')

Page({
  data: {
    stats: null,
    tags: [],
    recentMemories: [],
    insight: '',
    loading: true,
  },

  onShow() {
    this.loadData()
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const [stats, allMemories] = await Promise.all([
        api.getStats().catch(() => null),
        api.getMemories({ limit: 5 }).catch(() => []),
      ])
      this.setData({
        stats,
        tags: stats ? stats.top_tags || [] : [],
        recentMemories: allMemories,
        insight: stats ? stats.ai_insight || '' : '',
        loading: false,
      })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  onTagTap(e) {
    const tag = e.currentTarget.dataset.tag
    const app = getApp()
    app.globalData.searchTag = tag
    wx.switchTab({ url: '/pages/search/search' })
  },

  onMemoryTap(e) {
    wx.navigateTo({ url: `/pages/detail/detail?id=${e.detail.id}` })
  },
})
