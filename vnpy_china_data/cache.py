"""
Redis缓存管理模块

提供数据查询缓存功能，用于加速重复数据查询。
"""

import json
from typing import Any, Optional
from datetime import timedelta
from threading import Lock

try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    RedisError = Exception
    REDIS_AVAILABLE = False


class DataQueryCache:
    """数据查询缓存

    基于Redis实现的数据查询缓存，支持：
    - 自动序列化/反序列化
    - TTL过期管理
    - 模式匹配批量删除
    - 连接状态管理
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = "",
        default_ttl: int = 3600,
    ):
        """初始化Redis缓存

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: 密码
            default_ttl: 默认过期时间（秒）
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl

        self._redis_client: Optional[redis.Redis] = None
        self._lock = Lock()
        self._connected = False

    def connect(self) -> bool:
        """连接Redis

        Returns:
            是否连接成功
        """
        try:
            self._redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password if self.password else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self._redis_client.ping()
            self._connected = True
            return True
        except RedisError:
            self._connected = False
            return False

    def close(self) -> None:
        """关闭连接"""
        if self._redis_client:
            try:
                self._redis_client.close()
            except Exception:
                pass
            finally:
                self._redis_client = None
                self._connected = False

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self._redis_client is not None

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，不存在返回None
        """
        if not self.is_connected:
            return None

        try:
            data = self._redis_client.get(key)
            if data:
                return json.loads(data)
        except (RedisError, json.JSONDecodeError):
            pass
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示使用默认值

        Returns:
            是否设置成功
        """
        if not self.is_connected:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            return self._redis_client.setex(key, ttl, serialized) == True
        except (RedisError, TypeError):
            return False

    def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.is_connected:
            return False

        try:
            return self._redis_client.delete(key) > 0
        except RedisError:
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配的所有缓存

        Args:
            pattern: 键模式（如：bar_*）

        Returns:
            删除的键数量
        """
        if not self.is_connected:
            return 0

        try:
            keys = self._redis_client.keys(f"{pattern}*")
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except RedisError:
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self.is_connected:
            return False

        try:
            return self._redis_client.exists(key) > 0
        except RedisError:
            return False

    def get_ttl(self, key: str) -> int:
        """获取缓存剩余生存时间

        Args:
            key: 缓存键

        Returns:
            剩余秒数，-2表示不存在，-1表示无过期时间
        """
        if not self.is_connected:
            return -2

        try:
            return self._redis_client.ttl(key)
        except RedisError:
            return -2

    def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.is_connected:
            return False

        try:
            return self._redis_client.expire(key, ttl)
        except RedisError:
            return False

    def ping(self) -> bool:
        """Ping Redis服务器

        Returns:
            是否响应成功
        """
        if not self.is_connected:
            return False

        try:
            return self._redis_client.ping()
        except RedisError:
            return False


class MemoryCache:
    """内存缓存（Redis不可用时的备用方案）"""

    def __init__(self, default_ttl: int = 3600):
        self._cache: dict = {}
        self._expiry: dict = {}
        self.default_ttl = default_ttl
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                if key in self._expiry:
                    import time
                    if time.time() < self._expiry[key]:
                        return self._cache[key]
                    else:
                        del self._cache[key]
                        del self._expiry[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import time
        with self._lock:
            self._cache[key] = value
            self._expiry[key] = time.time() + (ttl or self.default_ttl)
        return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._expiry:
                    del self._expiry[key]
                return True
        return False

    def clear_pattern(self, pattern: str) -> int:
        import fnmatch
        with self._lock:
            keys = [k for k in self._cache.keys() if fnmatch.fnmatch(k, f"{pattern}*")]
            for key in keys:
                del self._cache[key]
                if key in self._expiry:
                    del self._expiry[key]
            return len(keys)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None
