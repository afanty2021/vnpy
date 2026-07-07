"""
系统监控器

监控系统状态：QMT连接、内存、CPU、磁盘、进程等
"""

from datetime import datetime
from typing import Dict, Any, Optional
import threading
import time

try:
    import psutil
except ImportError:
    psutil = None

from loguru import logger

from vnpy_china_monitor.monitor.engine import MonitorEngine, MonitorType


class SystemMonitor:
    """系统监控器

    检查系统资源使用情况和QMT连接状态
    """

    def __init__(
        self,
        monitor_engine: MonitorEngine,
        check_interval: int = 60,
        memory_warning: float = 0.80,
        memory_critical: float = 0.90,
        cpu_warning: float = 0.80,
        cpu_critical: float = 0.90,
        disk_warning: float = 0.85,
        disk_critical: float = 0.95,
    ):
        """初始化系统监控器

        Args:
            monitor_engine: 监控引擎实例
            check_interval: 检查间隔(秒)
            memory_warning: 内存警告阈值
            memory_critical: 内存严重阈值
            cpu_warning: CPU警告阈值
            cpu_critical: CPU严重阈值
            disk_warning: 磁盘警告阈值
            disk_critical: 磁盘严重阈值
        """
        self.monitor_engine = monitor_engine
        self.check_interval = check_interval

        # 阈值设置
        self.memory_warning = memory_warning
        self.memory_critical = memory_critical
        self.cpu_warning = cpu_warning
        self.cpu_critical = cpu_critical
        self.disk_warning = disk_warning
        self.disk_critical = disk_critical

        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # QMT网关引用
        self._qmt_gateway = None
        self._qmt_check_interval = 30  # QMT连接检查间隔

        # 最后一次检查结果缓存
        self._last_check_results: Dict[str, Any] = {}

        logger.info("SystemMonitor 初始化完成")

    def set_qmt_gateway(self, gateway) -> None:
        """设置QMT网关用于连接检查

        Args:
            gateway: QMT网关实例
        """
        self._qmt_gateway = gateway

    def check_qmt_connection(self) -> Dict[str, Any]:
        """检查QMT连接状态

        Returns:
            包含连接状态的字典
        """
        if not self._qmt_gateway:
            return {
                "connected": False,
                "status": "unknown",
                "message": "未配置QMT网关",
            }

        try:
            # 尝试检查网关连接状态
            # QMT网关应该有 is_connected 属性或方法
            if hasattr(self._qmt_gateway, "is_connected"):
                connected = self._qmt_gateway.is_connected()
            elif hasattr(self._qmt_gateway, "get_status"):
                status = self._qmt_gateway.get_status()
                connected = status.get("connected", False)
            else:
                # 假设未连接
                connected = False

            result = {
                "connected": connected,
                "status": "connected" if connected else "disconnected",
                "message": "QMT已连接" if connected else "QMT未连接",
            }

        except Exception as e:
            logger.error(f"检查QMT连接状态失败: {e}")
            result = {
                "connected": False,
                "status": "error",
                "message": f"检查失败: {str(e)}",
            }

        self._last_check_results["qmt"] = result
        return result

    def check_memory_usage(self) -> Dict[str, Any]:
        """检查内存使用情况

        Returns:
            包含内存使用信息的字典
        """
        if not psutil:
            return {
                "percent": 0,
                "total": 0,
                "available": 0,
                "used": 0,
                "status": "unavailable",
                "message": "psutil未安装",
            }

        try:
            memory = psutil.virtual_memory()

            percent = memory.percent / 100.0
            if percent >= self.memory_critical:
                status = "critical"
            elif percent >= self.memory_warning:
                status = "warning"
            else:
                status = "normal"

            result = {
                "percent": memory.percent,
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "status": status,
                "message": f"内存使用率: {memory.percent:.1f}%",
            }

        except Exception as e:
            logger.error(f"检查内存使用失败: {e}")
            result = {
                "percent": 0,
                "status": "error",
                "message": f"检查失败: {str(e)}",
            }

        self._last_check_results["memory"] = result
        return result

    def check_cpu_usage(self) -> Dict[str, Any]:
        """检查CPU使用情况

        Returns:
            包含CPU使用信息的字典
        """
        if not psutil:
            return {
                "percent": 0,
                "status": "unavailable",
                "message": "psutil未安装",
            }

        try:
            # 获取CPU使用率 (interval=1 表示等待1秒获取准确值)
            # 状态判定与展示复用同一采样值，避免两次 cpu_percent 调用数值不一致
            cpu_percent_value = psutil.cpu_percent(interval=1)
            percent = cpu_percent_value / 100.0

            if percent >= self.cpu_critical:
                status = "critical"
            elif percent >= self.cpu_warning:
                status = "warning"
            else:
                status = "normal"

            result = {
                "percent": cpu_percent_value,
                "status": status,
                "message": f"CPU使用率: {cpu_percent_value:.1f}%",
                "cpu_count": psutil.cpu_count(),
            }

        except Exception as e:
            logger.error(f"检查CPU使用失败: {e}")
            result = {
                "percent": 0,
                "status": "error",
                "message": f"检查失败: {str(e)}",
            }

        self._last_check_results["cpu"] = result
        return result

    def check_disk_usage(self) -> Dict[str, Any]:
        """检查磁盘使用情况

        Returns:
            包含磁盘使用信息的字典
        """
        if not psutil:
            return {
                "percent": 0,
                "status": "unavailable",
                "message": "psutil未安装",
            }

        try:
            disk = psutil.disk_usage("/")

            percent = disk.percent / 100.0
            if percent >= self.disk_critical:
                status = "critical"
            elif percent >= self.disk_warning:
                status = "warning"
            else:
                status = "normal"

            result = {
                "percent": disk.percent,
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "status": status,
                "message": f"磁盘使用率: {disk.percent:.1f}%",
            }

        except Exception as e:
            logger.error(f"检查磁盘使用失败: {e}")
            result = {
                "percent": 0,
                "status": "error",
                "message": f"检查失败: {str(e)}",
            }

        self._last_check_results["disk"] = result
        return result

    def check_process_status(self) -> Dict[str, Any]:
        """检查进程状态

        Returns:
            包含进程信息的字典
        """
        try:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)

            result = {
                "pid": current_process.pid,
                "name": current_process.name(),
                "status": current_process.status(),
                "memory_mb": current_process.memory_info().rss / 1024 / 1024,
                "cpu_percent": current_process.cpu_percent(interval=0.1),
                "num_threads": current_process.num_threads(),
                "children_count": len(children),
                "status": "running",
                "message": f"进程运行中，子进程数: {len(children)}",
            }

        except Exception as e:
            logger.error(f"检查进程状态失败: {e}")
            result = {
                "status": "error",
                "message": f"检查失败: {str(e)}",
            }

        self._last_check_results["process"] = result
        return result

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有监控指标

        Returns:
            所有监控指标的字典
        """
        return {
            "qmt": self.check_qmt_connection(),
            "memory": self.check_memory_usage(),
            "cpu": self.check_cpu_usage(),
            "disk": self.check_disk_usage(),
            "process": self.check_process_status(),
        }

    def update_all_metrics(self) -> None:
        """更新所有监控数据到监控引擎"""
        # QMT连接
        qmt_result = self.check_qmt_connection()
        self.monitor_engine.update_monitor(
            name="qmt_connection",
            monitor_type=MonitorType.SYSTEM,
            value=qmt_result["connected"],
            status=qmt_result["status"],
            unit="",
            description=qmt_result["message"],
        )

        # 内存
        memory_result = self.check_memory_usage()
        self.monitor_engine.update_monitor(
            name="memory_usage",
            monitor_type=MonitorType.SYSTEM,
            value=memory_result["percent"],
            status=memory_result["status"],
            unit="%",
            description=memory_result["message"],
        )

        # CPU
        cpu_result = self.check_cpu_usage()
        self.monitor_engine.update_monitor(
            name="cpu_usage",
            monitor_type=MonitorType.SYSTEM,
            value=cpu_result["percent"],
            status=cpu_result["status"],
            unit="%",
            description=cpu_result["message"],
        )

        # 磁盘
        disk_result = self.check_disk_usage()
        self.monitor_engine.update_monitor(
            name="disk_usage",
            monitor_type=MonitorType.SYSTEM,
            value=disk_result["percent"],
            status=disk_result["status"],
            unit="%",
            description=disk_result["message"],
        )

        # 进程
        process_result = self.check_process_status()
        self.monitor_engine.update_monitor(
            name="process_status",
            monitor_type=MonitorType.SYSTEM,
            value=process_result.get("status", "unknown"),
            status=process_result["status"],
            unit="",
            description=process_result["message"],
        )

    def start(self) -> None:
        """启动系统监控"""
        if self._running:
            logger.warning("系统监控已在运行中")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("系统监控已启动")

    def stop(self) -> None:
        """停止系统监控"""
        if not self._running:
            logger.warning("系统监控未在运行")
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("系统监控已停止")

    def _monitor_loop(self) -> None:
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self.update_all_metrics()
            except Exception as e:
                logger.error(f"系统监控更新失败: {e}")

            # 等待下一个检查周期
            self._stop_event.wait(self.check_interval)

    def get_last_check_results(self) -> Dict[str, Any]:
        """获取最后一次检查结果"""
        return self._last_check_results.copy()
