// 记忆外挂 — API 封装层
const app = getApp()

const request = (url, method = 'GET', data = null) => {
  return new Promise((resolve, reject) => {
    var headers = { 'Content-Type': 'application/json' }
    var apiKey = app.globalData.apiKey
    if (apiKey) {
      headers['X-API-Key'] = apiKey
    }
    wx.request({
      url: app.globalData.apiBase + url,
      method,
      data,
      header: headers,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject({ status: res.statusCode, message: res.data })
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常', icon: 'none' })
        reject({ status: -1, message: '网络请求失败', error: err })
      }
    })
  })
}

// ── 健康检查 ──
const healthCheck = () => request('/health')

// ── 记忆 CRUD ──
const getMemories = (params = {}) => {
  const query = Object.keys(params)
    .filter(k => params[k] !== undefined && params[k] !== null)
    .map(k => `${k}=${encodeURIComponent(params[k])}`)
    .join('&')
  return request(`/memories${query ? '?' + query : ''}`)
}

const createMemory = (data) => request('/memories', 'POST', data)
const getMemory = (id) => request(`/memories/${id}`)
const updateMemory = (id, data) => request(`/memories/${id}`, 'PATCH', data)
const deleteMemory = (id) => request(`/memories/${id}`, 'DELETE')

// ── AI 富化 ──
const enrichMemory = (id) => request(`/memories/${id}/enrich`, 'POST')

// ── 搜索 ──
const searchMemories = (q, mode = 'keyword', limit = 20) =>
  request(`/memories/search?q=${encodeURIComponent(q)}&mode=${mode}&limit=${limit}`)

// ── 关联 ──
const getRelated = (id) => request(`/memories/${id}/related`)

// ── 标签 & 统计 ──
const getTags = () => request('/tags')
const getStats = () => request('/stats')

module.exports = {
  healthCheck,
  getMemories,
  createMemory,
  getMemory,
  updateMemory,
  deleteMemory,
  searchMemories,
  getRelated,
  enrichMemory,
  getTags,
  getStats,
}
