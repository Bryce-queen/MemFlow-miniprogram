// 记忆外挂 — 详情页
const api = require('../../utils/api')
const util = require('../../utils/util')

Page({
  data: {
    id: '',
    memory: null,
    related: [],
    editing: false,
    editContent: '',
    editTags: '',
    loading: true,
    enriching: false,
  },

  onLoad(options) {
    this.setData({
      id: options.id,
      editing: options.edit === '1',
    })
    this.loadMemory()
  },

  async loadMemory() {
    try {
      const [memory, related] = await Promise.all([
        api.getMemory(this.data.id),
        api.getRelated(this.data.id).catch(() => []),
      ])
      this.setData({
        memory,
        related,
        editContent: memory.content,
        editTags: (memory.tags || []).join(', '),
        loading: false,
      })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  // ── 编辑模式 ──
  onToggleEdit() {
    this.setData({ editing: !this.data.editing })
    if (this.data.editing) {
      this.setData({
        editContent: this.data.memory.content,
        editTags: (this.data.memory.tags || []).join(', '),
      })
    }
  },

  onContentInput(e) {
    this.setData({ editContent: e.detail.value })
  },

  onTagsInput(e) {
    this.setData({ editTags: e.detail.value })
  },

  async onSave() {
    const content = this.data.editContent.trim()
    if (!content) return

    const tags = this.data.editTags
      .split(/[,，]/)
      .map(t => t.trim())
      .filter(Boolean)

    try {
      await api.updateMemory(this.data.id, { content, tags })
      wx.showToast({ title: '已保存', icon: 'success' })
      this.setData({ editing: false })
      this.loadMemory()
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  // ── 返回 ──
  onBack() {
    wx.navigateBack()
  },

  // ── AI 分析 ──
  async onEnrich() {
    this.setData({ enriching: true })
    try {
      const enriched = await api.enrichMemory(this.data.id)
      wx.showToast({ title: 'AI 分析完成', icon: 'success' })
      this.setData({ memory: enriched, enriching: false })
    } catch (e) {
      this.setData({ enriching: false })
      wx.showToast({ title: 'AI 分析失败', icon: 'none' })
    }
  },

  // ── 复制 ──
  onCopy() {
    wx.setClipboardData({ data: this.data.memory.content })
  },

  // ── 删除 ──
  async onDelete() {
    const res = await new Promise(r => {
      wx.showModal({ title: '确认删除', content: '删除后不可恢复', success: r })
    })
    if (!res.confirm) return
    try {
      await api.deleteMemory(this.data.id)
      wx.showToast({ title: '已删除', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      wx.showToast({ title: '删除失败', icon: 'none' })
    }
  },

  // ── 关联记忆点击 ──
  onRelatedTap(e) {
    const id = e.currentTarget.dataset.id
    wx.redirectTo({ url: `/pages/detail/detail?id=${id}` })
  },
})
