# Code Indexing Frontend

React 前端应用，用于与代码索引 Agent 交互。

## 功能特性

- 📁 **文件树**: 左侧显示代码库的文件结构
- 💻 **代码查看器**: 支持语法高亮，可高亮显示特定行
- 💬 **聊天界面**: 右侧聊天面板，可以提问关于代码库的问题
- 🔗 **代码引用**: 答案中的文件引用可点击，自动跳转并高亮

## 安装和运行

```bash
# 安装依赖
npm install

# 启动开发服务器（端口 3000）
npm run dev

# 构建生产版本
npm run build
```

## 配置

前端通过 Vite 代理连接到后端 API（端口 8001）。配置在 `vite.config.js` 中。

确保后端服务运行在 `http://localhost:8001`。

## 使用

1. 启动后端服务：`./launch_backend.sh`
2. 启动前端：`npm run dev`
3. 在浏览器中打开 `http://localhost:3000`

