#!/usr/bin/env python3
"""使用 Koyeb REST API 部署 GitHub 仓库到 Koyeb 平台

服务名称从 .env 文件中的 SERVICE_NAME 读取（必须是规范化的名称）。

默认会自动引用 OPENAI_API_KEY Secret 作为环境变量。
如果需要引用其他 Secrets，可以使用 --secret-ref 参数。

用法:
    python deploy_koyeb.py [--repo REPO] [--branch BRANCH] [--port PORT]
    
    引用额外的 Secrets:
    python deploy_koyeb.py --secret-ref ANOTHER_SECRET
    
    列出所有服务:
    python deploy_koyeb.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

# Koyeb API 基础 URL
KOYEB_API_BASE = "https://app.koyeb.com/v1"


def load_env() -> dict[str, str]:
    """加载环境变量配置"""
    env = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    env.update(os.environ)
    return {k: v for k, v in env.items() if v is not None}


def normalize_service_name(service_name: str) -> str:
    """规范化服务名称：Koyeb 服务名称只能包含小写字母、数字和连字符，不能以下划线开头或结尾"""
    import re
    # 将下划线替换为连字符，并转换为小写
    normalized = service_name.replace("_", "-").lower()
    # 移除开头和结尾的连字符
    normalized = normalized.strip("-")
    # 确保只包含小写字母、数字和连字符
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    return normalized


def is_service_name_normalized(service_name: str) -> bool:
    """检查服务名称是否已经规范化"""
    normalized = normalize_service_name(service_name)
    return service_name == normalized


def check_path_consistency(service_name: str) -> tuple[bool, str]:
    """检查配置一致性（已简化，不再需要检查 base path）
    
    Returns:
        (is_consistent, error_message)
    """
    # 使用 reverse proxy + 独立域名，不再需要 base path 配置
    # 此函数保留用于未来可能的其他检查
    return True, ""


def get_or_create_secret(
    api_key: str,
    secret_name: str,
    secret_value: str | None = None,
) -> str | None:
    """获取或创建 Koyeb Secret，返回 secret ID
    
    Args:
        api_key: Koyeb API key
        secret_name: Secret 名称
        secret_value: Secret 值（如果提供，且 secret 不存在则创建）
    
    Returns:
        Secret ID 或 None（如果失败）
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    try:
        # 1. 检查 secret 是否已存在
        secrets_resp = httpx.get(
            f"{KOYEB_API_BASE}/secrets",
            headers=headers,
            timeout=30.0,
        )
        secrets_resp.raise_for_status()
        secrets_data = secrets_resp.json()
        
        secret_id = None
        for secret in secrets_data.get("secrets", []):
            if secret.get("name") == secret_name:
                secret_id = secret.get("id")
                print(f"✓ Secret 已存在: {secret_name} ({secret_id})")
                return secret_id
        
        # 2. Secret 不存在，如果提供了值则创建
        if secret_value:
            print(f"创建 Secret: {secret_name}...")
            create_secret_resp = httpx.post(
                f"{KOYEB_API_BASE}/secrets",
                headers=headers,
                json={
                    "type": "SIMPLE",
                    "name": secret_name,
                    "value": secret_value,
                },
                timeout=30.0,
            )
            create_secret_resp.raise_for_status()
            secret_data = create_secret_resp.json()
            secret_id = secret_data.get("secret", {}).get("id")
            print(f"✓ Secret 创建成功: {secret_id}")
            return secret_id
        else:
            print(f"⚠ Secret '{secret_name}' 不存在，且未提供值，跳过创建")
            return None
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误: {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应内容: {e.response.text}")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None


def deploy(
    api_key: str,
    repo: str,
    app_name: str,
    service_name: str,
    branch: str = "master",
    port: int = 8001,
    secret_refs: list[str] | None = None,
    routes: list[dict] | None = None,
) -> bool:
    """使用 Koyeb REST API 部署"""
    # 构建路由配置（如果没有提供，则使用默认路由：/<service_name> -> port）
    routes_config = routes
    if routes_config is None:
        # 默认路由：/<service_name> -> port
        routes_config = [
            {
                "port": port,
                "path": f"/{service_name}"
            }
        ]
    
    print(f"部署配置:")
    print(f"  仓库: {repo}")
    print(f"  应用名: {app_name}")
    print(f"  服务名: {service_name}")
    print(f"  分支: {branch}")
    print(f"  端口: {port}")
    print(f"  构建方式: Docker (Dockerfile)")
    print(f"  路由配置: {json.dumps(routes_config, indent=2, ensure_ascii=False)}")
    print(f"  注意: 使用 reverse proxy + 独立域名，前后端不需要 base path 支持")
    if secret_refs:
        print(f"  引用 Secrets: {', '.join(secret_refs)}")
    print()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 用于保存最后一个请求的 payload，以便错误时显示
    last_request_payload = None

    try:
        # 1. 检查或创建应用
        print("检查应用是否存在...")
        apps_resp = httpx.get(
            f"{KOYEB_API_BASE}/apps",
            headers=headers,
            timeout=30.0,
        )
        apps_resp.raise_for_status()
        apps_data = apps_resp.json()

        app_id = None
        for app in apps_data.get("apps", []):
            if app.get("name") == app_name:
                app_id = app.get("id")
                print(f"✓ 应用已存在: {app_id}")
                break

        if not app_id:
            print(f"创建应用: {app_name}...")
            create_app_resp = httpx.post(
                f"{KOYEB_API_BASE}/apps",
                headers=headers,
                json={"name": app_name},
                timeout=30.0,
            )
            create_app_resp.raise_for_status()
            app_data = create_app_resp.json()
            app_id = app_data.get("app", {}).get("id")
            print(f"✓ 应用创建成功: {app_id}")

        # 2. 检查或创建服务
        print(f"检查服务是否存在...")
        services_resp = httpx.get(
            f"{KOYEB_API_BASE}/services",
            headers=headers,
            params={"app_id": app_id},
            timeout=30.0,
        )
        services_resp.raise_for_status()
        services_data = services_resp.json()

        service_id = None
        for service in services_data.get("services", []):
            if service.get("name") == service_name:
                service_id = service.get("id")
                print(f"✓ 服务已存在: {service_id}")
                break

        # 构建 Git 仓库 URL（Koyeb API 需要 github.com/<org>/<repo> 格式）
        if repo.startswith("http://") or repo.startswith("https://"):
            # 从完整 URL 中提取 github.com/<org>/<repo>
            if "github.com/" in repo:
                git_repo_url = repo.split("github.com/")[-1].rstrip("/")
                if not git_repo_url.startswith("github.com/"):
                    git_repo_url = f"github.com/{git_repo_url}"
            else:
                git_repo_url = repo
        else:
            # 已经是 <org>/<repo> 格式
            git_repo_url = f"github.com/{repo}" if "/" in repo else repo

        # 构建环境变量配置（引用 Secrets）
        env_config = []
        if secret_refs:
            # 验证 Secret 是否存在，然后使用插值语法引用
            missing_secrets = []
            for secret_name in secret_refs:
                secret_id = get_or_create_secret(api_key, secret_name)
                if secret_id:
                    # Koyeb API 使用插值语法 {{ secret.SECRET_NAME }} 引用 Secret
                    # 注意：格式必须是 {{ secret.SECRET_NAME }}，中间有空格
                    env_config.append({"key": secret_name, "value": f"{{{{ secret.{secret_name} }}}}"})
                    print(f"✓ 配置环境变量 {secret_name} 引用 Secret: {secret_name} (ID: {secret_id})")
                else:
                    missing_secrets.append(secret_name)
            
            # 如果 Secret 不存在，报错并停止部署
            if missing_secrets:
                print(f"\n❌ 错误: 以下 Secrets 不存在，无法继续部署:")
                for secret_name in missing_secrets:
                    print(f"   - {secret_name}")
                print(f"\n请在 Koyeb 控制台创建这些 Secrets:")
                print(f"   1. 访问 https://app.koyeb.com/secrets")
                print(f"   2. 点击 'Add secret'")
                print(f"   3. 输入 Secret 名称和值")
                return False
        
        # 添加 SERVICE_NAME 到环境变量（如果需要的话，可以用于其他用途）
        # 注意：前后端不再需要 BASE_PATH，因为使用 reverse proxy + 独立域名
        env_config.append({"key": "SERVICE_NAME", "value": service_name})

        if not service_id:
            print(f"创建服务: {service_name}...")
            service_payload = {
                "app_id": app_id,
                "definition": {
                    "name": service_name,
                    "type": "WEB_SERVICE",
                    "git": {
                        "repository": git_repo_url,
                        "branch": branch,
                        "docker": {
                            "dockerfile": "Dockerfile",
                            "build_args": {
                                "SERVICE_NAME": service_name
                            }
                        }
                    },
                    "ports": [
                        {
                            "port": port,
                            "protocol": "HTTP",
                        }
                    ],
                    "regions": ["na"],
                    "instance_types": [
                        {
                            "type": "nano"
                        }
                    ],
                    "scalings": [
                        {
                            "min": 1,
                            "max": 1
                        }
                    ],
                    "routes": routes_config,
                },
            }
            # 添加环境变量配置（引用 Secrets）
            if env_config:
                service_payload["definition"]["env"] = env_config
                print(f"\n📋 环境变量配置 (共 {len(env_config)} 个):")
                for env_var in env_config:
                    value = env_var.get('value', '')
                    # 检查是否是 Secret 引用（包含 {{ secret.xxx }}）
                    if '{{ secret.' in value:
                        print(f"   {env_var['key']} = {value} (Secret 引用)")
                    else:
                        print(f"   {env_var['key']} = {value}")
                print(f"\n完整 env 配置 JSON:")
                print(json.dumps(env_config, indent=2, ensure_ascii=False))
            # 保存请求 payload 以便错误时显示
            last_request_payload = service_payload
            create_service_resp = httpx.post(
                f"{KOYEB_API_BASE}/services",
                headers=headers,
                json=service_payload,
                timeout=60.0,
            )
            create_service_resp.raise_for_status()
            service_data = create_service_resp.json()
            service_id = service_data.get("service", {}).get("id")
            print(f"✓ 服务创建成功: {service_id}")
        else:
            print(f"更新服务: {service_id}...")
            # 更新服务（触发重新部署）
            update_payload = {
                "definition": {
                    "name": service_name,
                    "type": "WEB_SERVICE",
                    "git": {
                        "repository": git_repo_url,
                        "branch": branch,
                        "docker": {
                            "dockerfile": "Dockerfile",
                            "build_args": {
                                "SERVICE_NAME": service_name
                            }
                        }
                    },
                    "ports": [
                        {
                            "port": port,
                            "protocol": "HTTP",
                        }
                    ],
                    "regions": ["na"],
                    "instance_types": [
                        {
                            "type": "nano"
                        }
                    ],
                    "scalings": [
                        {
                            "min": 1,
                            "max": 1
                        }
                    ],
                    "routes": routes_config,
                },
            }
            # 添加环境变量配置（引用 Secrets）
            if env_config:
                update_payload["definition"]["env"] = env_config
                print(f"📋 环境变量配置:")
                for env_var in env_config:
                    value = env_var.get('value', '')
                    # 检查是否是 Secret 引用（包含 {{ secret.xxx }}）
                    if '{{ secret.' in value:
                        print(f"   {env_var['key']} = {value} (Secret 引用)")
                    else:
                        print(f"   {env_var['key']} = {value}")
            update_service_resp = httpx.patch(
                f"{KOYEB_API_BASE}/services/{service_id}",
                headers=headers,
                json=update_payload,
                timeout=60.0,
            )
            update_service_resp.raise_for_status()
            print(f"✓ 服务更新成功")

        print()
        print("=== 部署完成 ===")
        print(f"应用 ID: {app_id}")
        print(f"服务 ID: {service_id}")
        return True

    except httpx.HTTPStatusError as e:
        print(f"\n{'='*60}")
        print(f"HTTP 错误: {e.response.status_code}")
        print(f"{'='*60}")
        
        if e.request:
            print(f"\n请求信息:")
            print(f"  URL: {e.request.url}")
            print(f"  方法: {e.request.method}")
            # 尝试显示请求体（优先使用保存的 payload，否则尝试从 request 中获取）
            if last_request_payload:
                print(f"  请求体:")
                print(json.dumps(last_request_payload, indent=4, ensure_ascii=False))
            elif hasattr(e.request, 'content') and e.request.content:
                try:
                    request_body = json.loads(e.request.content)
                    print(f"  请求体:")
                    print(json.dumps(request_body, indent=4, ensure_ascii=False))
                except:
                    content_preview = str(e.request.content)[:500]
                    print(f"  请求体: {content_preview}")
        
        print(f"\n响应信息:")
        print(f"  状态码: {e.response.status_code}")
        print(f"  Headers: {dict(e.response.headers)}")
        print(f"  响应内容:")
        try:
            error_data = e.response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            response_text = e.response.text
            print(f"  {response_text[:1000]}")
            if len(response_text) > 1000:
                print(f"  ... (响应内容过长，已截断)")
        print(f"{'='*60}\n")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def list_services(api_key: str, app_name: str | None = None) -> bool:
    """列出 Koyeb 服务"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    try:
        # 获取所有应用
        apps_resp = httpx.get(
            f"{KOYEB_API_BASE}/apps",
            headers=headers,
            timeout=30.0,
        )
        apps_resp.raise_for_status()
        apps_data = apps_resp.json()
        
        print("=== Koyeb 应用和服务列表 ===\n")
        
        apps = apps_data.get("apps", [])
        if not apps:
            print("未找到任何应用")
            return True
        
        print(f"找到 {len(apps)} 个应用:\n")
        
        for app in apps:
            app_id = app.get("id")
            app_name_current = app.get("name")
            
            # 如果指定了 app_name，只显示匹配的应用
            if app_name and app_name_current != app_name:
                continue
            
            print(f"应用: {app_name_current} (ID: {app_id})")
            
            # 获取该应用下的所有服务
            services_resp = httpx.get(
                f"{KOYEB_API_BASE}/services",
                headers=headers,
                params={"app_id": app_id},
                timeout=30.0,
            )
            services_resp.raise_for_status()
            services_data = services_resp.json()
            
            services = services_data.get("services", [])
            if services:
                for service in services:
                    service_name = service.get("name")
                    service_id = service.get("id")
                    status = service.get("status", "unknown")
                    print(f"  └─ 服务: {service_name} (ID: {service_id}, 状态: {status})")
            else:
                print("  └─ (无服务)")
            print()
        
        return True
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误: {e.response.status_code}")
        print(f"响应内容: {e.response.text[:500]}")
        try:
            error_data = e.response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            pass
        return False
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="使用 Koyeb API 部署 GitHub 仓库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo",
        default="https://github.com/grapeot/agentic_code_index",
        help="GitHub 仓库 URL 或路径 (默认: https://github.com/grapeot/agentic_code_index)",
    )
    parser.add_argument(
        "--app-name",
        default="ai-builders",
        help="Koyeb 应用名称 (默认: ai-builders，已硬编码)",
    )
    parser.add_argument(
        "--branch",
        default="master",
        help="Git 分支 (默认: master)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="应用端口 (默认: 8001)",
    )
    parser.add_argument(
        "--secret-ref",
        action="append",
        metavar="SECRET_NAME",
        help="引用 Koyeb Secret 作为环境变量（可多次使用，例如: --secret-ref ANOTHER_SECRET）。默认会自动引用 OPENAI_API_KEY",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有应用和服务，然后退出",
    )

    args = parser.parse_args(argv)

    # 加载环境变量
    env = load_env()
    api_key = env.get("KOYEB_API_KEY")
    if not api_key:
        print("错误: 未找到 KOYEB_API_KEY 环境变量")
        print("请在 .env 文件中设置 KOYEB_API_KEY")
        return 1

    # 如果只是列出服务，则执行并退出（不指定 app_name 以显示所有应用）
    if args.list:
        success = list_services(api_key, None)  # 显示所有应用
        return 0 if success else 1

    # 硬编码 app 名称为 ai-builders
    app_name = "ai-builders"
    
    # 从 .env 文件读取服务名称
    service_name = env.get("SERVICE_NAME")
    
    # 服务名称必须提供（除非使用 --list）
    if not service_name:
        print("错误: 服务名称未设置")
        print("请在 .env 文件中设置 SERVICE_NAME=<name>")
        return 1
    
    # 检查服务名称是否已经规范化
    if not is_service_name_normalized(service_name):
        normalized_name = normalize_service_name(service_name)
        print(f"❌ 错误: 服务名称未规范化")
        print(f"   当前值: {service_name}")
        print(f"   规范化后: {normalized_name}")
        print()
        print("Koyeb 服务名称要求：")
        print("  - 只能包含小写字母、数字和连字符 (-)")
        print("  - 不能以下划线 (_) 开头或结尾")
        print("  - 不能包含其他特殊字符")
        print()
        print("请修改 .env 文件中的 SERVICE_NAME，使用规范化后的名称。")
        return 1
    
    print(f"✓ 服务名称已规范化: {service_name}")
    print(f"✓ 使用 reverse proxy + 独立域名，前后端不需要 base path 配置")

    # 解析 Secret 引用，默认包含 OPENAI_API_KEY
    secret_refs = args.secret_ref or []
    if "OPENAI_API_KEY" not in secret_refs:
        secret_refs.insert(0, "OPENAI_API_KEY")

    # 使用 REST API 部署
    success = deploy(
        api_key=api_key,
        repo=args.repo,
        app_name=app_name,
        service_name=service_name,
        branch=args.branch,
        port=args.port,
        secret_refs=secret_refs,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

