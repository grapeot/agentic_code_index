# 多阶段构建：先构建前端
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# 复制前端 package.json（如果存在）
COPY frontend/package*.json ./

# 安装依赖（npm install 默认会安装所有依赖包括 devDependencies）
RUN if [ -f package.json ]; then \
      npm install; \
    else \
      echo "No package.json found, skipping npm install"; \
    fi

# 复制前端文件
COPY frontend/ .

# 构建前端（如果 package.json 存在）
# 注意：BASE_PATH 需要通过环境变量传递（Koyeb 的环境变量在构建时可能不可用）
# 如果 BASE_PATH 未设置，使用相对路径 './'（适用于根路径部署）
# 构建后，如果 BASE_PATH 设置了，会通过脚本修改 HTML 文件中的路径
RUN if [ -f package.json ]; then \
      echo "Building frontend..." && \
      echo "BASE_PATH=${BASE_PATH:-}" && \
      export BASE_PATH=${BASE_PATH:-} && \
      echo "Exported BASE_PATH=${BASE_PATH}" && \
      npm run build && \
      echo "Build completed. Checking dist directory..." && \
      ls -la dist/ && \
      if [ -f dist/index.html ]; then \
        echo "✅ index.html found"; \
        echo "Checking index.html content for base path..." && \
        head -10 dist/index.html && \
        echo "---" && \
        echo "Checking for asset paths:" && \
        grep -o 'href="[^"]*"' dist/index.html | head -3 || echo "No href found" && \
        grep -o 'src="[^"]*"' dist/index.html | head -3 || echo "No src found"; \
        echo "---" && \
        if [ -n "$BASE_PATH" ] && [ "$BASE_PATH" != "/" ]; then \
          echo "BASE_PATH is set to: $BASE_PATH, updating HTML paths..." && \
          sed -i "s|href=\"/assets/|href=\"$BASE_PATH/assets/|g" dist/index.html && \
          sed -i "s|src=\"/assets/|src=\"$BASE_PATH/assets/|g" dist/index.html && \
          echo "Updated HTML paths:" && \
          grep -o 'href="[^"]*"' dist/index.html | head -3 && \
          grep -o 'src="[^"]*"' dist/index.html | head -3; \
        else \
          echo "BASE_PATH not set or is root, using relative paths (no modification needed)"; \
        fi; \
      else \
        echo "❌ ERROR: index.html not found after build!"; \
        exit 1; \
      fi; \
    else \
      echo "No package.json found, skipping build"; \
      mkdir -p dist && echo "<html><body>Frontend not built</body></html>" > dist/index.html; \
    fi

# Python 后端阶段
FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 从前端构建阶段复制构建好的静态文件
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 验证前端文件已复制
RUN echo "Verifying frontend files..." && \
    ls -la frontend/ && \
    if [ -d frontend/dist ]; then \
      echo "✅ frontend/dist exists" && \
      ls -la frontend/dist/ && \
      if [ -f frontend/dist/index.html ]; then \
        echo "✅ frontend/dist/index.html exists"; \
      else \
        echo "❌ ERROR: frontend/dist/index.html not found!"; \
        exit 1; \
      fi; \
    else \
      echo "❌ ERROR: frontend/dist directory not found!"; \
      exit 1; \
    fi

ENV PORT=8001

CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"

