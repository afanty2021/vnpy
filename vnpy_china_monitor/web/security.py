"""
安全认证模块

提供JWT认证、密码加密等安全功能
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """哈希密码

    Args:
        password: 明文密码
        salt: 盐值，None时自动生成

    Returns:
        (哈希后的密码, 盐值)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # 使用SHA-256哈希
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,  # 迭代次数
    )

    return pwd_hash.hex(), salt


def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    """验证密码

    Args:
        password: 明文密码
        pwd_hash: 哈希后的密码
        salt: 盐值

    Returns:
        是否匹配
    """
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, pwd_hash)


class JWTManager:
    """JWT令牌管理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
    ):
        """初始化JWT管理器

        Args:
            secret_key: 密钥
            algorithm: 算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_days: 刷新令牌过期时间（天）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """创建访问令牌

        Args:
            data: 令牌数据
            expires_delta: 过期时间增量

        Returns:
            JWT令牌
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "type": "access",
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌

        Args:
            data: 令牌数据

        Returns:
            JWT令牌
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "type": "refresh",
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌

        Args:
            token: JWT令牌

        Returns:
            解码后的数据，失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌

        Args:
            token: JWT令牌

        Returns:
            令牌数据，失败返回None
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        if payload.get("type") != "access":
            logger.warning("Invalid token type: expected 'access'")
            return None

        return payload

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证刷新令牌

        Args:
            token: JWT令牌

        Returns:
            令牌数据，失败返回None
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        if payload.get("type") != "refresh":
            logger.warning("Invalid token type: expected 'refresh'")
            return None

        return payload


class SimpleUserStore:
    """简单用户存储

    注意：生产环境应使用数据库
    """

    def __init__(self):
        # 用户名 -> (哈希密码, 盐值)
        self._users: Dict[str, tuple[str, str]] = {}

        # 默认用户: admin / admin123
        pwd_hash, salt = hash_password("admin123")
        self._users["admin"] = (pwd_hash, salt)

    def add_user(self, username: str, password: str) -> None:
        """添加用户

        Args:
            username: 用户名
            password: 明文密码
        """
        pwd_hash, salt = hash_password(password)
        self._users[username] = (pwd_hash, salt)
        logger.info(f"User added: {username}")

    def verify_user(self, username: str, password: str) -> bool:
        """验证用户

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            是否验证成功
        """
        if username not in self._users:
            logger.warning(f"User not found: {username}")
            return False

        pwd_hash, salt = self._users[username]
        return verify_password(password, pwd_hash, salt)


class AuthManager:
    """认证管理器"""

    def __init__(
        self,
        jwt_manager: JWTManager,
        user_store: Optional[SimpleUserStore] = None,
    ):
        """初始化认证管理器

        Args:
            jwt_manager: JWT管理器
            user_store: 用户存储
        """
        self.jwt_manager = jwt_manager
        self.user_store = user_store or SimpleUserStore()

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """认证用户

        Args:
            username: 用户名
            password: 密码

        Returns:
            访问令牌，失败返回None
        """
        if not self.user_store.verify_user(username, password):
            logger.warning(f"Authentication failed for user: {username}")
            return None

        logger.info(f"User authenticated: {username}")

        # 创建令牌
        token_data = {
            "sub": username,
            "iat": datetime.utcnow().timestamp(),
        }

        access_token = self.jwt_manager.create_access_token(token_data)
        refresh_token = self.jwt_manager.create_refresh_token(token_data)

        # 返回访问令牌（实际应用中可能需要返回刷新令牌）
        return access_token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌

        Args:
            token: JWT令牌

        Returns:
            令牌数据，失败返回None
        """
        return self.jwt_manager.verify_access_token(token)

    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """刷新令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的访问令牌，失败返回None
        """
        payload = self.jwt_manager.verify_refresh_token(refresh_token)

        if not payload:
            return None

        # 创建新的访问令牌
        token_data = {
            "sub": payload.get("sub"),
            "iat": datetime.utcnow().timestamp(),
        }

        return self.jwt_manager.create_access_token(token_data)
