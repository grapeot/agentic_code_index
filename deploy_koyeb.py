#!/usr/bin/env python3
"""使用 Koyeb API 部署 GitHub 仓库到 Koyeb 平台

支持两种部署方式：
1. 使用 Koyeb CLI（如果已安装）
2. 使用 Koyeb REST API（如果 CLI 不可用）

默认会自动引用 OPENAI_API_KEY Secret 作为环境变量。
如果需要引用其他 Secrets，可以使用 --secret-ref 参数。

用法:
    python deploy_koyeb.py [--repo REPO] [--app-name APP_NAME] [--branch BRANCH] [--port PORT]
    
    引用额外的 Secrets:
    python deploy_koyeb.py --secret-ref ANOTHER_SECRET
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

# Koyeb API 基础 URL
KOYEB_API_BASE = "https://www.koyeb.com/api/v1"


def load_env() -> dict[str, str]:
    """加载环境变量配置"""
    env = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    env.update(os.environ)
    return {k: v for k, v in env.items() if v is not None}


def check_koyeb_cli() -> bool:
    """检查 Koyeb CLI 是否已安装"""
    try:
        result = subprocess.run(
            ["koyeb", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def deploy_with_cli(
    api_key: str,
    repo: str,
    app_name: str,
    service_name: str,
    branch: str = "master",
    port: int = 8001,
    secret_refs: list[str] | None = None,
) -> bool:
    """使用 Koyeb CLI 部署"""
    print(f"使用 Koyeb CLI 部署...")
    print(f"  仓库: {repo}")
    print(f"  应用名: {app_name}")
    print(f"  服务名: {service_name}")
    print(f"  分支: {branch}")
    print(f"  端口: {port}")
    if secret_refs:
        print(f"  引用 Secrets: {', '.join(secret_refs)}")
    print()

    # 设置环境变量
    env = os.environ.copy()
    env["KOYEB_API_KEY"] = api_key

    try:
        # 检查应用是否已存在
        print("检查应用是否存在...")
        check_app = subprocess.run(
            ["koyeb", "app", "get", app_name],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        if check_app.returncode != 0:
            # 应用不存在，创建应用
            print(f"创建应用: {app_name}...")
            create_app = subprocess.run(
                ["koyeb", "app", "create", app_name],
                env=env,
                timeout=30,
            )
            if create_app.returncode != 0:
                print(f"错误: 创建应用失败")
                return False
            print(f"✓ 应用创建成功")
        else:
            print(f"✓ 应用已存在")

        # 检查服务是否已存在
        print(f"检查服务是否存在...")
        check_service = subprocess.run(
            ["koyeb", "service", "get", service_name, "--app", app_name],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        if check_service.returncode != 0:
            # 服务不存在，创建服务
            print(f"创建服务: {service_name}...")
            create_service_cmd = [
                "koyeb",
                "service",
                "create",
                service_name,
                "--app",
                app_name,
                "--git",
                repo,
                "--branch",
                branch,
                "--port",
                str(port),
            ]
            # 添加 Secret 引用作为环境变量
            if secret_refs:
                for secret_name in secret_refs:
                    create_service_cmd.extend(["--env", f"{secret_name}=@{secret_name}"])
            create_service = subprocess.run(
                create_service_cmd,
                env=env,
                timeout=60,
            )
            if create_service.returncode != 0:
                print(f"错误: 创建服务失败")
                return False
            print(f"✓ 服务创建成功")
        else:
            print(f"✓ 服务已存在，将更新部署...")
            # 更新服务（触发重新部署）
            update_service_cmd = [
                "koyeb",
                "service",
                "update",
                service_name,
                "--app",
                app_name,
                "--git",
                repo,
                "--branch",
                branch,
            ]
            # 添加 Secret 引用作为环境变量
            if secret_refs:
                for secret_name in secret_refs:
                    update_service_cmd.extend(["--env", f"{secret_name}=@{secret_name}"])
            update_service = subprocess.run(
                update_service_cmd,
                env=env,
                timeout=60,
            )
            if update_service.returncode != 0:
                print(f"错误: 更新服务失败")
                return False
            print(f"✓ 服务更新成功")

        print()
        print("=== 部署完成 ===")
        print(f"应用名称: {app_name}")
        print(f"服务名称: {service_name}")
        print()
        print("查看部署状态:")
        print(f"  koyeb service get {service_name} --app {app_name}")
        print()
        print("查看应用详情:")
        print(f"  koyeb app get {app_name}")
        return True

    except subprocess.TimeoutExpired:
        print("错误: 命令执行超时")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False


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


def deploy_with_api(
    api_key: str,
    repo: str,
    app_name: str,
    service_name: str,
    branch: str = "master",
    port: int = 8001,
    secret_refs: list[str] | None = None,
) -> bool:
    """使用 Koyeb REST API 部署"""
    print(f"使用 Koyeb REST API 部署...")
    print(f"  仓库: {repo}")
    print(f"  应用名: {app_name}")
    print(f"  服务名: {service_name}")
    print(f"  分支: {branch}")
    print(f"  端口: {port}")
    if secret_refs:
        print(f"  引用 Secrets: {', '.join(secret_refs)}")
    print()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

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

        # 构建 Git 仓库 URL
        git_repo_url = repo
        if not git_repo_url.startswith("http"):
            git_repo_url = f"https://github.com/{repo}"

        # 构建环境变量配置（引用 Secrets）
        env_config = []
        if secret_refs:
            # Koyeb 使用 @SECRET_NAME 格式引用 secrets
            for secret_name in secret_refs:
                env_config.append({"name": secret_name, "value": f"@{secret_name}"})

        if not service_id:
            print(f"创建服务: {service_name}...")
            service_payload = {
                "name": service_name,
                "app_id": app_id,
                "definition": {
                    "name": service_name,
                    "type": "WEB_SERVICE",
                    "git": {
                        "repository": git_repo_url,
                        "branch": branch,
                    },
                    "ports": [
                        {
                            "port": port,
                            "protocol": "HTTP",
                        }
                    ],
                },
            }
            # 添加环境变量配置（引用 Secrets）
            if env_config:
                service_payload["definition"]["env"] = env_config
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
                    "git": {
                        "repository": git_repo_url,
                        "branch": branch,
                    },
                },
            }
            # 添加环境变量配置（引用 Secrets）
            if env_config:
                update_payload["definition"]["env"] = env_config
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
        print()
        print("查看部署状态:")
        print(f"  https://app.koyeb.com/apps/{app_name}/services/{service_name}")
        return True

    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误: {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应内容: {e.response.text}")
        return False
    except Exception as e:
        print(f"错误: {e}")
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
        default="agentic-code-index",
        help="Koyeb 应用名称 (默认: agentic-code-index)",
    )
    parser.add_argument(
        "--service-name",
        default=None,
        help="Koyeb 服务名称 (默认: {app-name}-service)",
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
        "--force-api",
        action="store_true",
        help="强制使用 REST API，即使 CLI 可用",
    )
    parser.add_argument(
        "--secret-ref",
        action="append",
        metavar="SECRET_NAME",
        help="引用 Koyeb Secret 作为环境变量（可多次使用，例如: --secret-ref ANOTHER_SECRET）。默认会自动引用 OPENAI_API_KEY",
    )

    args = parser.parse_args(argv)

    # 加载环境变量
    env = load_env()
    api_key = env.get("KOYEB_API_KEY")
    if not api_key:
        print("错误: 未找到 KOYEB_API_KEY 环境变量")
        print("请在 .env 文件中设置 KOYEB_API_KEY")
        return 1

    # 设置服务名称
    service_name = args.service_name or f"{args.app_name}-service"

    # 解析 Secret 引用，默认包含 OPENAI_API_KEY
    secret_refs = args.secret_ref or []
    if "OPENAI_API_KEY" not in secret_refs:
        secret_refs.insert(0, "OPENAI_API_KEY")

    # 选择部署方式
    use_cli = check_koyeb_cli() and not args.force_api

    if use_cli:
        success = deploy_with_cli(
            api_key=api_key,
            repo=args.repo,
            app_name=args.app_name,
            service_name=service_name,
            branch=args.branch,
            port=args.port,
            secret_refs=secret_refs,
        )
    else:
        if not args.force_api and not check_koyeb_cli():
            print("提示: Koyeb CLI 未安装，使用 REST API 部署")
            print("要安装 CLI，请运行: curl -sSL https://get.koyeb.com | bash")
            print()
        success = deploy_with_api(
            api_key=api_key,
            repo=args.repo,
            app_name=args.app_name,
            service_name=service_name,
            branch=args.branch,
            port=args.port,
            secret_refs=secret_refs,
        )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

