// 记忆外挂 — 工具函数

// ── 时间格式化 ──
const formatTime = (isoString) => {
  if (!isoString) return ''
  const d = new Date(isoString)
  const now = new Date()
  const diff = now - d
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)}分钟前`
  if (diff < day) return `${Math.floor(diff / hour)}小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)}天前`

  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dt = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')

  if (y === now.getFullYear()) return `${m}-${dt} ${hh}:${mm}`
  return `${y}-${m}-${dt}`
}

const formatDate = (isoString) => {
  if (!isoString) return ''
  const d = new Date(isoString)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ── 数字格式化 ──
const formatNumber = (n) => {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

// ── 标签颜色（基于标签名 hash 取色） ──
const TAG_COLORS = [
  { bg: 'rgba(108,99,255,0.15)', text: '#a8a4ff', border: 'rgba(108,99,255,0.3)' },
  { bg: 'rgba(0,201,167,0.15)', text: '#00c9a7', border: 'rgba(0,201,167,0.3)' },
  { bg: 'rgba(255,107,107,0.15)', text: '#ff6b6b', border: 'rgba(255,107,107,0.3)' },
  { bg: 'rgba(255,184,77,0.15)', text: '#ffb84d', border: 'rgba(255,184,77,0.3)' },
  { bg: 'rgba(77,171,255,0.15)', text: '#4dabff', border: 'rgba(77,171,255,0.3)' },
  { bg: 'rgba(255,77,166,0.15)', text: '#ff4da6', border: 'rgba(255,77,166,0.3)' },
  { bg: 'rgba(77,255,136,0.15)', text: '#4dff88', border: 'rgba(77,255,136,0.3)' },
  { bg: 'rgba(204,77,255,0.15)', text: '#cc4dff', border: 'rgba(204,77,255,0.3)' },
]

const getTagColor = (tagName) => {
  let hash = 0
  for (let i = 0; i < tagName.length; i++) {
    hash = tagName.charCodeAt(i) + ((hash << 5) - hash)
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

// ── 实体图标 ──
const getEntityIcon = (type) => {
  const icons = {
    person: '👤', book: '📚', place: '📍',
    date: '📅', org: '🏢', link: '🔗', contact: '📞',
  }
  return icons[type] || '📌'
}

// ── 文本截断 ──
const truncate = (text, maxLen = 100) => {
  if (!text) return ''
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen) + '…'
}

module.exports = {
  formatTime,
  formatDate,
  formatNumber,
  getTagColor,
  getEntityIcon,
  truncate,
}
