// 记忆外挂 — 捕获页（首页）
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    inputText: '',
    inputFocus: false,
    recording: false,
    recordSeconds: 0,
    memories: [],
    loading: true,
    hasMore: true,
    page: 0,
    source: 'text',
    submitting: false,
  },

  // ── 生命周期 ──
  onLoad() {
    this._timer = null
    this.loadMemories()
  },

  onShow() {
    // 如果从离线缓存回来，刷新
    this.loadMemories(true)
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer)
  },

  onPullDownRefresh() {
    this.loadMemories(true)
    wx.stopPullDownRefresh()
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMemories()
    }
  },

  // ── 加载记忆列表 ──
  async loadMemories(refresh = false) {
    if (refresh) {
      this.setData({ page: 0, hasMore: true })
    }
    this.setData({ loading: true })

    try {
      const offset = refresh ? 0 : this.data.memories.length
      const res = await api.getMemories({ limit: 20, offset })
      const memories = refresh ? res : [...this.data.memories, ...res]
      this.setData({
        memories,
        loading: false,
        hasMore: res.length === 20,
        page: Math.ceil(memories.length / 20),
      })
    } catch (e) {
      this.setData({ loading: false })
      // 尝试加载离线缓存
      const offline = wx.getStorageSync('offline_memories') || []
      if (offline.length) {
        this.setData({ memories: offline, hasMore: false })
      }
    }
  },

  // ── 输入处理 ──
  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  // ── 提交记忆 ──
  async onSubmit() {
    const text = this.data.inputText.trim()
    if (!text || this.data.submitting) return
    if (text.length > 5000) {
      wx.showToast({ title: '内容超过5000字', icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    try {
      await api.createMemory({
        content: text,
        source: this.data.source,
      })
      this.setData({ inputText: '', submitting: false })
      wx.showToast({ title: '已记录', icon: 'success', duration: 1500 })
      this.loadMemories(true)
    } catch (e) {
      this.setData({ submitting: false })
      // 离线缓存
      const offline = wx.getStorageSync('offline_memories') || []
      offline.unshift({
        id: 'offline_' + Date.now(),
        content: text,
        source: this.data.source,
        tags: [],
        entities: [],
        summary: text.slice(0, 80),
        keywords: [],
        related_ids: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        _offline: true,
      })
      wx.setStorageSync('offline_memories', offline)
      wx.showToast({ title: '已缓存（离线）', icon: 'none' })
      this.setData({ memories: offline, hasMore: false })
    }
  },

  // ── 语音录制（占位） ──
  onRecordStart() {
    this.setData({ recording: true, recordSeconds: 0 })
    this._timer = setInterval(() => {
      this.setData({ recordSeconds: this.data.recordSeconds + 1 })
    }, 1000)
    wx.showToast({ title: '语音功能开发中', icon: 'none', duration: 2000 })
  },

  onRecordEnd() {
    this.setData({ recording: false })
    if (this._timer) {
      clearInterval(this._timer)
      this._timer = null
    }
  },

  // ── 来源切换 ──
  onSourceChange(e) {
    this.setData({ source: e.currentTarget.dataset.source })
  },

  // ── 记忆卡片事件 ──
  onMemoryTap(e) {
    wx.navigateTo({ url: `/pages/detail/detail?id=${e.detail.id}` })
  },

  onMemoryAction(e) {
    const { action, id, memory } = e.detail
    switch (action) {
      case 'copy':
        wx.setClipboardData({ data: memory.content })
        break
      case 'edit':
        wx.navigateTo({ url: `/pages/detail/detail?id=${id}&edit=1` })
        break
      case 'delete':
        this.onDelete(id)
        break
    }
  },

  onMemoryTagTap(e) {
    app.globalData.searchTag = e.detail.tag
    wx.switchTab({ url: '/pages/search/search' })
  },

  // ── 删除 ──
  async onDelete(id) {
    const res = await new Promise(r => {
      wx.showModal({ title: '确认删除', content: '删除后不可恢复', success: r })
    })
    if (!res.confirm) return
    try {
      await api.deleteMemory(id)
      this.setData({
        memories: this.data.memories.filter(m => m.id !== id)
      })
      wx.showToast({ title: '已删除', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: '删除失败', icon: 'none' })
    }
  },
})
