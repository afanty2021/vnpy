"""
告警去重器

基于指纹的告警去重机制
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
import hashlib
import threading

from loguru import logger

from vnpy_china_monitor.alert.types import AlertEvent, AlertSeverity


@dataclass
class DedupeConfig:
    """去重配置"""

    window_seconds: int = 300  # 去重时间窗口（5分钟）
    cooldown_seconds: int = 600  # 冷却时间（10分钟）
    max_same_alerts: int = 3  # 相同告警最大次数


class AlertDeduplicator:
    """告警去重器

    基于指纹的告警去重机制，支持时间窗口、冷却时间和最大次数限制
    """

    def __init__(self, config: Optional[DedupeConfig] = None):
        """初始化去重器

        Args:
            config: 去重配置
        """
        self.config = config or DedupeConfig()

        # 告警指纹记录 {fingerprint: [timestamp1, timestamp2, ...]}
        self._alert_fingerprints: Dict[str, List[datetime]] = {}

        # 冷却中的指纹集合
        self._cooldown_fingerprints: Set[str] = set()
        # 冷却结束时间 {fingerprint: end_time}，供 cleanup_expired 判定解除冷却
        self._cooldown_end_times: Dict[str, datetime] = {}

        # 锁
        self._lock = threading.Lock()

        # 统计信息
        self._stats = {
            "total_alerts": 0,
            "deduped_count": 0,
            "cooldown_count": 0,
            "max_reached_count": 0,
        }

        logger.info(
            f"AlertDeduplicator 初始化完成: "
            f"窗口={self.config.window_seconds}秒, "
            f"冷却={self.config.cooldown_seconds}秒, "
            f"最大次数={self.config.max_same_alerts}"
        )

    def should_send(self, alert: AlertEvent) -> bool:
        """判断告警是否应该发送

        去重策略：
        1. 在冷却中 -> 不发送
        2. 在时间窗口内已有记录 -> 去重（除非已达到最大次数）
        3. 达到最大次数 -> 冷却，不发送
        4. 其他 -> 允许发送

        Args:
            alert: 告警事件

        Returns:
            是否应该发送
        """
        with self._lock:
            self._stats["total_alerts"] += 1

            fingerprint = self.get_fingerprint(alert)
            now = datetime.now()

            # 检查是否在冷却中
            if fingerprint in self._cooldown_fingerprints:
                logger.debug(f"告警在冷却中，跳过: {alert.title}")
                self._stats["cooldown_count"] += 1
                return False

            # 获取历史记录
            timestamps = self._alert_fingerprints.get(fingerprint, [])

            # 清理过期的时间戳
            window = timedelta(seconds=self.config.window_seconds)
            valid_timestamps = [ts for ts in timestamps if now - ts < window]

            # 更新有效时间戳（去掉过期的）
            if len(valid_timestamps) != len(timestamps):
                self._alert_fingerprints[fingerprint] = valid_timestamps

            # 策略1：检查是否达到最大次数（在时间窗口内）
            if len(valid_timestamps) >= self.config.max_same_alerts:
                # 标记为冷却
                self._cooldown_fingerprints.add(fingerprint)

                # 安排冷却结束
                cooldown = timedelta(seconds=self.config.cooldown_seconds)
                end_time = now + cooldown
                self._schedule_cooldown_end(fingerprint, end_time)

                logger.debug(f"告警达到最大次数，进入冷却: {alert.title}")
                self._stats["max_reached_count"] += 1
                return False

            # 策略2：在时间窗口内已有记录 -> 去重
            if valid_timestamps:
                logger.debug(f"告警在时间窗口内，去重: {alert.title}")
                self._stats["deduped_count"] += 1
                return False

            # 可以发送
            return True

    def record_alert(self, fingerprint: str) -> None:
        """记录已发送的告警

        Args:
            fingerprint: 告警指纹
        """
        with self._lock:
            now = datetime.now()

            if fingerprint not in self._alert_fingerprints:
                self._alert_fingerprints[fingerprint] = []

            self._alert_fingerprints[fingerprint].append(now)

            # 清理过期记录
            window = timedelta(seconds=self.config.window_seconds)
            self._alert_fingerprints[fingerprint] = [
                ts for ts in self._alert_fingerprints[fingerprint] if now - ts < window
            ]

    def get_fingerprint(self, alert: AlertEvent) -> str:
        """计算告警指纹

        基于 source + title + severity 生成唯一指纹

        Args:
            alert: 告警事件

        Returns:
            指纹字符串
        """
        # 组合关键字段
        key = f"{alert.source}:{alert.title}:{alert.severity.value}"

        # 生成hash
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def get_stats(self) -> Dict:
        """获取去重统计

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                "total_alerts": self._stats["total_alerts"],
                "deduped_count": self._stats["deduped_count"],
                "cooldown_count": self._stats["cooldown_count"],
                "max_reached_count": self._stats["max_reached_count"],
                "active_fingerprints": len(self._alert_fingerprints),
                "cooldown_count": len(self._cooldown_fingerprints),
            }

    def clear(self) -> None:
        """清空去重记录"""
        with self._lock:
            self._alert_fingerprints.clear()
            self._cooldown_fingerprints.clear()
            self._cooldown_end_times.clear()
            logger.info("去重记录已清空")

    def _schedule_cooldown_end(self, fingerprint: str, end_time: datetime) -> None:
        """安排冷却结束

        Args:
            fingerprint: 指纹
            end_time: 冷却结束时间
        """
        # 记录冷却结束时间，cleanup_expired 据此解除冷却
        # （外部需定期调用 cleanup_expired，否则指纹会永久滞留冷却集合）
        self._cooldown_end_times[fingerprint] = end_time

    def cleanup_expired(self) -> int:
        """清理过期的指纹记录

        Returns:
            清理的记录数
        """
        with self._lock:
            now = datetime.now()
            window = timedelta(seconds=self.config.window_seconds)
            cooldown = timedelta(seconds=self.config.cooldown_seconds)

            cleaned = 0

            # 清理过期的指纹记录
            for fingerprint in list(self._alert_fingerprints.keys()):
                timestamps = self._alert_fingerprints[fingerprint]
                valid = [ts for ts in timestamps if now - ts < window]

                if not valid:
                    del self._alert_fingerprints[fingerprint]
                    cleaned += 1
                else:
                    self._alert_fingerprints[fingerprint] = valid

            # 清理冷却结束的指纹（根据 _cooldown_end_times 判定）
            for fingerprint in list(self._cooldown_fingerprints):
                end_time = self._cooldown_end_times.get(fingerprint)
                if end_time is None or now >= end_time:
                    self._cooldown_fingerprints.discard(fingerprint)
                    self._cooldown_end_times.pop(fingerprint, None)
                    cleaned += 1

            return cleaned

    def is_in_cooldown(self, fingerprint: str) -> bool:
        """检查指纹是否在冷却中

        Args:
            fingerprint: 指纹

        Returns:
            是否在冷却中
        """
        with self._lock:
            return fingerprint in self._cooldown_fingerprints
