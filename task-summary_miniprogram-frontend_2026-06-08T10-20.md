# Task: 微信小程序前端全部页面代码写入完成

**时间**: 2026-06-08 10:05-10:20

## 目标
继续之前中断的工作——为「记忆外挂」微信小程序补充全部页面代码（之前只搭了项目骨架和工具函数，页面代码未写）。

## 执行
一次性批量写入 31 个文件到 `miniprogram/` 目录下：

### 组件 (4文件)
- `components/memory-card/memory-card.{js,json,wxml,wxss}` — 记忆卡片组件，observer自动格式化数据(时间/标签颜色/实体图标)，支持点击→详情、长按→操作菜单(复制/编辑/删除)、标签点击→搜索

### 页面 (5个×4文件=20文件)
- **capture** (捕获/首页) — 按住录音按钮(带脉冲动画+计时器)、文字输入区(2000字限制)、来源切换、记忆列表(下拉刷新+触底加载)、离线缓存fallback
- **discover** (发现) — 顶部3栏统计、AI回顾卡片(总览/标签/回顾)、空状态引导
- **search** (搜索) — 搜索栏+confirm触发、历史记录(10条/LocalStorage)、结果列表复用memory-card、标签贯通(点击跳搜索)
- **detail** (详情) — 摘要条(紫色左边框)、inline编辑(内容+标签)、元信息栏、关联记忆列表、底部fixed操作栏(编辑/复制/删除)
- **mine** (我的) — 3栏统计、AI状态指示(绿色/灰色圆点)、标签云(字号+透明度按频率缩放)、功能列表(离线同步/导出/服务器设置)、API地址动态配置

### 核心文件 (7文件)
- `app.js` — globalData初始化、API地址Storage读取
- `app.json` — tabBar 5标签页配置(无图标占位)
- `app.wxss` — 全局暗色主题(.card/.tag/.empty-state/.btn-primary/.search-bar等)
- `utils/api.js` — 封装10个后端接口(getMemories/createMemory/searchMemories/getMemory/getRelated/updateMemory/deleteMemory/getStats/getTags/healthCheck)
- `utils/util.js` — 格式化时间/数字/实体图标/标签颜色/文本截断

## 关键决策
1. 组件内用observer+setData预处理数据（而非WXS），因为微信小程序WXS引入限制较多
2. 搜索历史存在LocalStorage（10条上限），标签跨页面传递用getApp().globalData
3. 离线缓存：网络异常时自动写入offline_memories数组，在「我的」页手动同步
4. tabBar 5个图标暂时无图（app.json中iconPath为空占位），需后续添加PNG

## 成果
- 31个文件，~1700行代码
- 完整的前端项目可直接导入微信开发者工具
- 需要：1)后端服务启动 2)tabBar图标 3)微信开发者工具打开验证
