"""Redis会话存储服务"""

import json
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_USE_REDIS = False

SESSION_TTL = 7 * 24 * 3600
SESSION_LIST_KEY = "chat:sessions"


def _get_redis() -> Optional[redis.Redis]:
    global _redis_client, _USE_REDIS
    if _USE_REDIS and _redis_client:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        _USE_REDIS = False
        return None

    try:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        _USE_REDIS = True
        logger.info("Redis连接成功")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis连接失败，降级为内存存储: {e}")
        _USE_REDIS = False
        _redis_client = None
        return None


def is_redis_available() -> bool:
    return _get_redis() is not None


def _session_key(session_id: str) -> str:
    return f"chat:session:{session_id}"


def save_session(session_id: str, messages: List[Dict[str, str]]) -> bool:
    r = _get_redis()
    if not r:
        return False

    try:
        data = json.dumps(messages, ensure_ascii=False)
        r.setex(_session_key(session_id), SESSION_TTL, data)

        r.zadd(SESSION_LIST_KEY, {session_id: datetime.now().timestamp()})
        r.expire(SESSION_LIST_KEY, SESSION_TTL)

        return True
    except Exception as e:
        logger.error(f"Redis保存会话失败: {e}")
        return False


def load_session(session_id: str) -> Optional[List[Dict[str, str]]]:
    r = _get_redis()
    if not r:
        return None

    try:
        data = r.get(_session_key(session_id))
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis加载会话失败: {e}")
        return None


def delete_session(session_id: str) -> bool:
    r = _get_redis()
    if not r:
        return False

    try:
        r.delete(_session_key(session_id))
        r.zrem(SESSION_LIST_KEY, session_id)
        return True
    except Exception as e:
        logger.error(f"Redis删除会话失败: {e}")
        return False


def list_sessions() -> List[Dict[str, Any]]:
    r = _get_redis()
    if not r:
        return []

    try:
        session_ids = r.zrevrange(SESSION_LIST_KEY, 0, -1)
        result = []
        for sid in session_ids:
            messages = load_session(sid)
            if messages and len(messages) > 0:
                first_user_msg = ""
                for m in messages:
                    if m.get("role") == "user":
                        first_user_msg = m.get("content", "")[:30]
                        break
                score = r.zscore(SESSION_LIST_KEY, sid)
                result.append({
                    "session_id": sid,
                    "title": first_user_msg or f"会话 {sid}",
                    "message_count": len(messages),
                    "updated_at": datetime.fromtimestamp(score).isoformat() if score else None,
                })
        return result
    except Exception as e:
        logger.error(f"Redis列出会话失败: {e}")
        return []
