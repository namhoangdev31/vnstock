"""Script đẩy biến môi trường VNSTOCK_API_KEY từ file .env lên FastAPI Cloud."""

import json
import logging
import sys
import webbrowser
from pathlib import Path

from dotenv import dotenv_values

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("push_env")


def main() -> None:
    # 1. Đọc key từ file .env
    root_dir = Path(__file__).resolve().parent.parent.parent
    env_path = root_dir / ".env"
    if not env_path.exists():
        logger.error(f"Không tìm thấy file .env tại: {env_path}")
        sys.exit(1)

    vals = dotenv_values(env_path)
    api_key = vals.get("VNSTOCK_APIKEY") or vals.get("VNSTOCK_API_KEY")
    if not api_key or not api_key.strip():
        logger.error(
            "Không tìm thấy VNSTOCK_APIKEY hoặc VNSTOCK_API_KEY trong file .env!"
        )
        sys.exit(1)

    api_key = api_key.strip()
    logger.info(
        "Đã tìm thấy VNSTOCK_APIKEY trong file .env (độ dài %d ký tự)", len(api_key)
    )

    # 2. Đọc app_id từ .fastapicloud/cloud.json
    cloud_json_path = root_dir / ".fastapicloud" / "cloud.json"
    if not cloud_json_path.exists():
        logger.error(f"Không tìm thấy file cloud.json tại: {cloud_json_path}")
        sys.exit(1)

    with open(cloud_json_path) as f:
        cloud_config = json.load(f)
    app_id = cloud_config.get("app_id")
    if not app_id:
        logger.error("Không tìm thấy app_id trong cloud.json!")
        sys.exit(1)

    logger.info(
        "FastAPI Cloud target app_id: %s (slug: %s)",
        app_id,
        cloud_config.get("app_slug"),
    )

    # 3. Kiểm tra xác thực FastAPI Cloud
    from fastapi_cloud_cli.api import APIClient, EnvironmentVariableCreatePayload
    from fastapi_cloud_cli.commands._flow import (
        fetch_access_token,
        start_device_authorization,
    )
    from fastapi_cloud_cli.utils.auth import AuthConfig, Identity, write_auth_config

    identity = Identity()
    if not identity.is_logged_in():
        logger.warning("Phiên đăng nhập FastAPI Cloud đã hết hạn hoặc chưa đăng nhập.")
        with APIClient() as client:
            auth_data = start_device_authorization(client)
            url = auth_data.verification_uri_complete
            logger.info("Vui lòng xác nhận đăng nhập tại liên kết sau:")
            logger.info("==> %s", url)
            try:
                webbrowser.open(url)
            except Exception:
                pass
            logger.info("Đang chờ xác nhận từ trình duyệt (tối đa 120s)...")
            token = fetch_access_token(
                client, auth_data.device_code, auth_data.interval, timeout=120
            )
            write_auth_config(AuthConfig(access_token=token))
            logger.info("Đăng nhập FastAPI Cloud thành công!")

    # 4. Đẩy biến môi trường lên FastAPI Cloud
    with APIClient() as client:
        logger.info("Đang thiết lập biến môi trường bí mật trên FastAPI Cloud...")
        client.batch_environment_variables(
            app_id=app_id,
            upsert={
                "VNSTOCK_API_KEY": EnvironmentVariableCreatePayload(
                    value=api_key, is_secret=True
                ),
                "VNSTOCK_APIKEY": EnvironmentVariableCreatePayload(
                    value=api_key, is_secret=True
                ),
            },
            delete=[],
            redeploy=True,
        )
        logger.info(
            "✓ Đã thiết lập thành công VNSTOCK_API_KEY và VNSTOCK_APIKEY trên FastAPI Cloud!"
        )
        logger.info("FastAPI Cloud đang tiến hành redeploy bản cập nhật.")


if __name__ == "__main__":
    main()
