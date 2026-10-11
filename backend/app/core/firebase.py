"""Firebase Admin SDK Integration for ViStock Platform.

Cung cấp khả năng xác thực mật mã các Firebase ID Tokens gửi từ App & Web.
"""

import json
import logging
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App | None:
    """Khởi tạo hoặc trả về instance Firebase Admin App."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        if settings.FIREBASE_CREDENTIALS_JSON:
            cert_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cert_dict)
            _firebase_app = firebase_admin.initialize_app(
                cred,
                {
                    "projectId": settings.FIREBASE_PROJECT_ID,
                    "databaseURL": settings.FIREBASE_DATABASE_URL,
                    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                },
            )
            logger.info("Firebase Admin initialized with inline credentials JSON")
        elif settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            _firebase_app = firebase_admin.initialize_app(
                cred,
                {
                    "projectId": settings.FIREBASE_PROJECT_ID,
                    "databaseURL": settings.FIREBASE_DATABASE_URL,
                    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                },
            )
            logger.info("Firebase Admin initialized with certificate file")
        elif settings.FIREBASE_PROJECT_ID:
            _firebase_app = firebase_admin.initialize_app(
                options={
                    "projectId": settings.FIREBASE_PROJECT_ID,
                    "databaseURL": settings.FIREBASE_DATABASE_URL,
                    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                }
            )
            logger.info(
                "Firebase Admin initialized with project ID: %s",
                settings.FIREBASE_PROJECT_ID,
            )
    except Exception as e:
        logger.warning("Could not initialize Firebase Admin: %s", e)
        return None

    return _firebase_app


def verify_firebase_id_token(id_token: str) -> dict[str, Any] | None:
    """Xác thực mã định danh Firebase ID Token gửi từ App/Web.

    Trả về claims (uid, email, name, picture) nếu hợp lệ, None nếu lỗi/hết hạn.
    """
    app = get_firebase_app()
    if not app:
        return None

    try:
        decoded_token = auth.verify_id_token(id_token, app=app)
        return decoded_token
    except Exception as e:
        logger.warning("Firebase ID token verification failed: %s", e)
        return None
