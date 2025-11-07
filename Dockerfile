# 多阶段构建：先构建前端
FROM node:18-slim AS frontend-builder

# 接受构建参数：SERVICE_NAME（用于计算 base path）
# Koyeb 的环境变量在构建时可能不可用，所以同时支持 ARG 和环境变量
ARG SERVICE_NAME
# 如果 ARG 未设置，尝试从环境变量读取（Koyeb 可能通过环境变量传递）
ENV SERVICE_NAME=${SERVICE_NAME}

WORKDIR /app/frontend

# 复制前端 package.json（如果存在）
COPY frontend/package*.json ./

# 安装依赖
RUN if [ -f package.json ]; then \
      npm install; \
    else \
      echo "No package.json found, skipping npm install"; \
    fi

# 复制前端文件
COPY frontend/ .

# 构建前端
# SERVICE_NAME 通过 ARG 或环境变量传递，用于设置 Vite 的 base path
RUN if [ -f package.json ]; then \
      SERVICE_NAME=${SERVICE_NAME:-$SERVICE_NAME} npm run build; \
      if [ ! -f dist/index.html ]; then \
        echo "❌ ERROR: index.html not found after build!"; \
        exit 1; \
      fi; \
    else \
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
RUN if [ ! -d frontend/dist ] || [ ! -f frontend/dist/index.html ]; then \
      echo "❌ ERROR: frontend/dist/index.html not found!"; \
      exit 1; \
    fi

ENV PORT=8001

CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"

