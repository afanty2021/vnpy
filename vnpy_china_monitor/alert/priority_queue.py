"""
告警优先级队列

基于堆的优先级队列实现
"""

import heapq
from typing import List, Optional, Any
from dataclasses import dataclass, field

from vnpy_china_monitor.alert.types import AlertEvent


@dataclass(order=True)
class QueueItem:
    """队列项（用于堆排序）"""

    priority: int
    timestamp: float
    alert: AlertEvent = field(compare=False)


class AlertPriorityQueue:
    """告警优先级队列

    基于heapq实现，支持优先级排序和超时自动移除
    """

    def __init__(self, maxsize: int = 0):
        """初始化队列

        Args:
            maxsize: 最大队列大小，0表示无限制
        """
        self._heap: List[QueueItem] = []
        self._maxsize = maxsize
        self._alert_ids = set()  # 用于快速查找

    def put(self, alert: AlertEvent) -> bool:
        """添加告警到队列

        Args:
            alert: 告警事件

        Returns:
            是否添加成功
        """
        # 检查是否已存在
        if alert.id in self._alert_ids:
            return False

        # 检查队列大小限制
        if self._maxsize > 0 and len(self._heap) >= self._maxsize:
            # 移除优先级最低的
            self.pop()

        # 添加到堆
        item = QueueItem(
            priority=-alert.priority.value,  # 负数实现最大堆
            timestamp=alert.timestamp.timestamp(),
            alert=alert,
        )
        heapq.heappush(self._heap, item)
        self._alert_ids.add(alert.id)

        return True

    def pop(self) -> Optional[AlertEvent]:
        """弹出最高优先级的告警

        Returns:
            告警事件或None
        """
        if not self._heap:
            return None

        item = heapq.heappop(self._heap)
        self._alert_ids.discard(item.alert.id)
        return item.alert

    def peek(self) -> Optional[AlertEvent]:
        """查看最高优先级的告警（不移除）

        Returns:
            告警事件或None
        """
        if not self._heap:
            return None
        return self._heap[0].alert

    def remove(self, alert_id: str) -> bool:
        """移除指定告警

        Args:
            alert_id: 告警ID

        Returns:
            是否成功移除
        """
        # 重建堆（移除指定元素）
        new_heap = [item for item in self._heap if item.alert.id != alert_id]

        if len(new_heap) == len(self._heap):
            return False

        heapq.heapify(new_heap)
        self._heap = new_heap
        self._alert_ids.discard(alert_id)

        return True

    def size(self) -> int:
        """获取队列大小

        Returns:
            队列大小
        """
        return len(self._heap)

    def is_empty(self) -> bool:
        """检查队列是否为空

        Returns:
            是否为空
        """
        return len(self._heap) == 0

    def is_full(self) -> bool:
        """检查队列是否已满

        Returns:
            是否已满
        """
        if self._maxsize <= 0:
            return False
        return len(self._heap) >= self._maxsize

    def clear(self) -> None:
        """清空队列"""
        self._heap.clear()
        self._alert_ids.clear()

    def get_all(self) -> List[AlertEvent]:
        """获取所有告警（按优先级排序）

        Returns:
            告警列表
        """
        return [item.alert for item in sorted(self._heap, key=lambda x: -x.priority)]
