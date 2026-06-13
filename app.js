// 记忆外挂 - 小程序入口
App({
  globalData: {
    apiBase: 'http://localhost:8701',  // 开发环境，上线改 HTTPS
    userInfo: null,
  },

  onLaunch() {
    // 检查登录态
    wx.getStorage({
      key: 'apiBase',
      success: (res) => {
        this.globalData.apiBase = res.data
      }
    })
    console.log('🧠 记忆外挂启动, API:', this.globalData.apiBase)
  },

  // 统一请求方法
  request(options) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBase + options.url,
        method: options.method || 'GET',
        data: options.data,
        header: {
          'Content-Type': 'application/json',
          ...options.header,
        },
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data)
          } else {
            reject({ status: res.statusCode, message: res.data })
          }
        },
        fail(err) {
          reject({ status: -1, message: '网络请求失败', error: err })
        }
      })
    })
  }
})
