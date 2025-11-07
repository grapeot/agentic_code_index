# Koyeb 部署指南

## 前置要求

1. **Koyeb 账户和 API Key**
   - 登录 [Koyeb 控制台](https://app.koyeb.com/)
   - 在账户设置中创建 API Key
   - 将 API Key 保存到 `.env` 文件或环境变量中

2. **创建 OPENAI_API_KEY Secret**
   - 在 Koyeb 控制台中创建名为 `OPENAI_API_KEY` 的 Secret
   - 部署脚本会自动引用这个 Secret

3. **GitHub 仓库**
   - 确保代码已推送到 GitHub
   - 仓库需要包含 `Dockerfile`

## 快速开始

### 1. 配置环境变量

创建或编辑 `.env` 文件：

```bash
KOYEB_API_KEY=your-koyeb-api-key-here
```

或者直接设置环境变量：

```bash
export KOYEB_API_KEY=your-koyeb-api-key-here
```

### 2. 运行部署脚本

**基本部署**（使用默认配置）：
```bash
python deploy_koyeb.py --force-api
```

**自定义配置**：
```bash
python deploy_koyeb.py \
  --repo https://github.com/your-username/your-repo \
  --app-name my-app \
  --branch main \
  --port 8001 \
  --force-api
```

## 参数说明

- `--repo`: GitHub 仓库 URL（默认：当前项目仓库）
- `--app-name`: Koyeb 应用名称（默认：`agentic-code-index`）
- `--service-name`: Koyeb 服务名称（默认：`{app-name}-service`）
- `--branch`: Git 分支（默认：`master`）
- `--port`: 应用端口（默认：`8001`）
- `--force-api`: 强制使用 REST API（即使 CLI 可用）
- `--secret-ref`: 引用额外的 Koyeb Secret（可多次使用）

## 部署流程

脚本会自动执行以下步骤：

1. **检查或创建应用**
   - 如果应用不存在，自动创建
   - 如果已存在，使用现有应用

2. **检查或创建服务**
   - 如果服务不存在，创建新服务
   - 如果已存在，更新服务（触发重新部署）

3. **配置环境变量**
   - 自动引用 `OPENAI_API_KEY` Secret
   - 可以添加其他 Secrets

4. **部署代码**
   - 从 GitHub 仓库拉取代码
   - 使用 Dockerfile 构建镜像
   - 部署到 Koyeb 平台

## 示例

### 示例 1: 部署到默认应用

```bash
# 设置 API Key
export KOYEB_API_KEY=your-key

# 部署
python deploy_koyeb.py --force-api
```

### 示例 2: 部署到自定义应用

```bash
python deploy_koyeb.py \
  --app-name my-custom-app \
  --branch main \
  --force-api
```

### 示例 3: 引用多个 Secrets

```bash
python deploy_koyeb.py \
  --secret-ref DATABASE_URL \
  --secret-ref REDIS_URL \
  --force-api
```

## 验证部署

部署完成后，脚本会显示：

```
=== 部署完成 ===
应用 ID: xxx
服务 ID: xxx

查看部署状态:
  https://app.koyeb.com/apps/{app-name}/services/{service-name}
```

访问显示的 URL 查看部署状态，或直接访问你的应用 URL。

## 常见问题

**Q: 如何获取 Koyeb API Key？**
A: 登录 Koyeb 控制台 → 账户设置 → API Keys → 创建新 Key

**Q: 如何创建 Secret？**
A: 在 Koyeb 控制台中，进入 Secrets 页面 → 创建新 Secret → 输入名称和值

**Q: 部署后如何更新？**
A: 推送代码到 GitHub，然后再次运行部署脚本。脚本会自动检测到服务已存在并触发更新。

**Q: 如何查看日志？**
A: 在 Koyeb 控制台的服务页面可以查看实时日志

**Q: 如何回滚？**
A: 在 Koyeb 控制台的服务页面，可以查看部署历史并回滚到之前的版本

## 注意事项

1. **确保 Dockerfile 存在**：Koyeb 使用 Dockerfile 构建应用
2. **确保代码已推送**：部署脚本从 GitHub 拉取代码
3. **Secret 名称匹配**：确保 Koyeb 中的 Secret 名称与代码中使用的环境变量名一致
4. **端口配置**：确保 Dockerfile 中的端口与 `--port` 参数一致（默认 8001）

## 故障排查

**部署失败**：
- 检查 `KOYEB_API_KEY` 是否正确设置
- 确认 GitHub 仓库 URL 正确
- 查看 Koyeb 控制台的错误日志

**应用无法启动**：
- 检查 Dockerfile 是否正确
- 确认 `OPENAI_API_KEY` Secret 已创建
- 查看应用日志排查错误

**前端无法访问**：
- 确认前端已构建（`frontend/dist` 存在）
- 检查 Dockerfile 是否正确复制了前端文件
- 验证根路径路由配置正确

