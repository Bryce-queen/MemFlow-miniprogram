// 记忆外挂 — memory-card 组件
const util = require('../../utils/util')

Component({
  properties: {
    memory: {
      type: Object,
      value: {},
      observer: '_onMemoryChange'
    },
    showActions: {
      type: Boolean,
      value: true
    }
  },

  data: {
    formatted: {}
  },

  methods: {
    _onMemoryChange(mem) {
      if (!mem || !mem.id) return
      this.setData({
        formatted: {
          time: util.formatTime(mem.created_at),
          date: util.formatDate(mem.created_at),
          summary: mem.summary || util.truncate(mem.content, 80),
          tags: (mem.tags || []).map(t => ({
            name: t,
            color: util.getTagColor(t)
          })),
          entities: (mem.entities || []).map(e => ({
            ...e,
            icon: util.getEntityIcon(e.type)
          })),
          sourceLabel: {
            text: '📝 文字输入',
            voice: '🎤 语音',
            image: '📷 图片',
            link: '🔗 链接',
            wechat: '💬 微信',
          }[mem.source] || '📝 文字输入',
        }
      })
    },

    // ── 事件 ──
    onTap() {
      this.triggerEvent('tap', { id: this.data.memory.id })
    },

    onLongPress() {
      if (!this.data.showActions) return
      const that = this
      wx.showActionSheet({
        itemList: ['复制内容', '编辑', '删除'],
        success(res) {
          const actions = ['copy', 'edit', 'delete']
          that.triggerEvent('action', {
            action: actions[res.tapIndex],
            id: that.data.memory.id,
            memory: that.data.memory,
          })
        }
      })
    },

    onTagTap(e) {
      const tag = e.currentTarget.dataset.tag
      this.triggerEvent('tagtap', { tag })
    },
  }
})
