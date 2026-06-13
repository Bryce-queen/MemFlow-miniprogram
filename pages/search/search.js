// 记忆外挂 — 搜索页
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    keyword: '',
    mode: 'keyword',
    results: [],
    searched: false,
    searching: false,
    history: [],
    inputFocus: false,
  },

  onLoad() {
    const history = wx.getStorageSync('search_history') || []
    this.setData({ history })
  },

  onShow() {
    // 从标签跳转过来的
    const tag = app.globalData.searchTag
    if (tag) {
      app.globalData.searchTag = null
      this.setData({ keyword: tag })
      this.doSearch()
    }
  },

  onInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  onConfirm() {
    this.doSearch()
  },

  onFocus() {
    this.setData({ inputFocus: true })
  },

  onBlur() {
    this.setData({ inputFocus: false })
  },

  onClear() {
    this.setData({ keyword: '', results: [], searched: false })
  },

  onModeChange(e) {
    const mode = e.currentTarget.dataset.mode
    this.setData({ mode })
    if (this.data.keyword.trim()) {
      this.doSearch()
    }
  },

  async doSearch() {
    const q = this.data.keyword.trim()
    if (!q) return

    this.setData({ searching: true })

    // 保存搜索历史
    let history = this.data.history.filter(h => h !== q)
    history.unshift(q)
    if (history.length > 10) history = history.slice(0, 10)
    wx.setStorageSync('search_history', history)
    this.setData({ history })

    try {
      const results = await api.searchMemories(q, this.data.mode, 20)
      const processed = (results || []).map(r => ({
        ...r,
        displayScore: r.score != null ? Math.round(r.score * 100) + '%' : '',
      }))
      this.setData({
        results: processed,
        searched: true,
        searching: false,
      })
    } catch (e) {
      this.setData({ searching: false })
      wx.showToast({ title: '搜索失败', icon: 'none' })
    }
  },

  onHistoryTap(e) {
    const q = e.currentTarget.dataset.q
    this.setData({ keyword: q })
    this.doSearch()
  },

  onClearHistory() {
    wx.removeStorageSync('search_history')
    this.setData({ history: [] })
  },

  onMemoryTap(e) {
    wx.navigateTo({ url: `/pages/detail/detail?id=${e.detail.id}` })
  },
})
