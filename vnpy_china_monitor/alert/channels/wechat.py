"""
微信告警通道

通过企业微信Webhook发送告警消息
"""

from typing import Dict, Any, Optional
import urllib.request
import urllib.error
import json

from loguru import logger

from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage


class WechatChannel(AlertChannel):
    """微信告警通道

    通过企业微信Webhook发送告警消息
    """

    def __init__(
        self,
        enabled: bool = False,
        webhook_url: str = "",
        mention_list: Optional[list] = None,
        mention_mobile_list: Optional[list] = None,
    ):
        """初始化微信通道

        Args:
            enabled: 是否启用
            webhook_url: 企业微信Webhook地址
            mention_list: @用户ID列表
            mention_mobile_list: @手机号列表
        """
        super().__init__(enabled=enabled, name="WechatChannel")

        self.webhook_url = webhook_url
        self.mention_list = mention_list or []
        self.mention_mobile_list = mention_mobile_list or []

        if not webhook_url:
            logger.warning("微信通道未配置Webhook URL")

        logger.info(f"WechatChannel 初始化完成: webhook_url={bool(webhook_url)}")

    def send(self, message: AlertMessage) -> bool:
        """发送告警消息

        Args:
            message: 告警消息

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("微信通道未配置Webhook URL")
            return False

        try:
            # 构建消息内容
            payload = self._build_payload(message)

            # 发送请求
            self._send_request(payload)

            logger.info(f"微信告警发送成功: {message.title}")
            return True

        except Exception as e:
            logger.error(f"微信告警发送失败: {e}")
            return False

    def _build_payload(self, message: AlertMessage) -> Dict[str, Any]:
        """构建消息载荷

        Args:
            message: 告警消息

        Returns:
            消息载荷字典
        """
        # 根据严重程度设置颜色
        color_map = {
            "info": "#173177",      # 蓝色
            "warning": "#FFAB00",   # 橙色
            "critical": "#F44336",   # 红色
        }
        color = color_map.get(message.severity, "#757575")

        # 构建markdown内容
        content = f"""**{message.title}**

> {message.message}

- **严重程度**: {message.severity}
- **优先级**: {message.priority}
- **来源**: {message.source}
- **时间**: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

        if message.data:
            content += "\n**附加信息:**\n"
            for key, value in message.data.items():
                content += f"- {key}: {value}\n"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }

        # 添加@功能
        if self.mention_list or self.mention_mobile_list:
            payload["markdown"]["mentioned_list"] = self.mention_list
            payload["markdown"]["mentioned_mobile_list"] = self.mention_mobile_list

        return payload

    def _send_request(self, payload: Dict[str, Any]) -> None:
        """发送HTTP请求

        Args:
            payload: 消息载荷
        """
        data = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }

        request = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))

            if result.get("errcode") != 0:
                raise Exception(f"微信API错误: {result.get('errmsg')}")

    def test_connection(self) -> bool:
        """测试Webhook连接

        Returns:
            是否连接成功
        """
        if not self.webhook_url:
            logger.warning("微信通道未配置Webhook URL")
            return False

        try:
            # 发送测试消息
            test_message = AlertMessage(
                title="测试消息",
                message="这是一条测试消息，用于验证通道配置",
                severity="info",
                priority=10,
                timestamp=__import__("datetime").datetime.now(),
                source="WechatChannel",
            )

            self.send(test_message)
            logger.info("微信通道连接测试成功")
            return True

        except Exception as e:
            logger.error(f"微信通道连接测试失败: {e}")
            return False

    def set_webhook_url(self, url: str) -> None:
        """设置Webhook URL

        Args:
            url: Webhook地址
        """
        self.webhook_url = url

    def add_mention(self, user_id: str = "", mobile: str = "") -> None:
        """添加@用户

        Args:
            user_id: 用户ID
            mobile: 手机号
        """
        if user_id and user_id not in self.mention_list:
            self.mention_list.append(user_id)

        if mobile and mobile not in self.mention_mobile_list:
            self.mention_mobile_list.append(mobile)

    def clear_mentions(self) -> None:
        """清除所有@用户"""
        self.mention_list.clear()
        self.mention_mobile_list.clear()

    def get_info(self) -> Dict[str, Any]:
        """获取通道信息

        Returns:
            通道信息字典
        """
        info = super().get_info()
        info.update({
            "webhook_url_configured": bool(self.webhook_url),
            "mention_count": len(self.mention_list),
            "mention_mobile_count": len(self.mention_mobile_list),
        })
        return info
