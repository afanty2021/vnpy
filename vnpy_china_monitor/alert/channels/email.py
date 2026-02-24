"""
邮件告警通道

通过SMTP发送告警邮件
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from loguru import logger

from vnpy_china_monitor.alert.channels.base import AlertChannel, AlertMessage


class EmailChannel(AlertChannel):
    """邮件告警通道

    通过SMTP协议发送告警邮件
    """

    def __init__(
        self,
        enabled: bool = False,
        smtp_host: str = "smtp.example.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        email_from: str = "",
        email_to: Optional[List[str]] = None,
        use_tls: bool = True,
    ):
        """初始化邮件通道

        Args:
            enabled: 是否启用
            smtp_host: SMTP服务器地址
            smtp_port: SMTP服务器端口
            smtp_user: SMTP用户名
            smtp_password: SMTP密码
            email_from: 发件人地址
            email_to: 收件人地址列表
            use_tls: 是否使用TLS
        """
        super().__init__(enabled=enabled, name="EmailChannel")

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from or smtp_user
        self.email_to = email_to or []
        self.use_tls = use_tls

        logger.info(
            f"EmailChannel 初始化完成: "
            f"host={smtp_host}, port={smtp_port}, "
            f"from={self.email_from}, to={len(self.email_to)} recipients"
        )

    def send(self, message: AlertMessage) -> bool:
        """发送告警邮件

        Args:
            message: 告警消息

        Returns:
            是否发送成功
        """
        if not self.email_to:
            logger.warning("邮件通道未配置收件人")
            return False

        try:
            # 创建邮件
            msg = self._create_message(message)

            # 发送邮件
            self._send_email(msg)

            logger.info(f"邮件告警发送成功: {message.title}")
            return True

        except Exception as e:
            logger.error(f"邮件告警发送失败: {e}")
            return False

    def _create_message(self, message: AlertMessage) -> MIMEMultipart:
        """创建邮件消息

        Args:
            message: 告警消息

        Returns:
            邮件消息对象
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{message.severity.upper()}] {message.title}"
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)

        # 纯文本版本
        text_content = message.format_text()
        msg.attach(MIMEText(text_content, "plain"))

        # HTML版本
        html_content = message.format_html()
        msg.attach(MIMEText(html_content, "html"))

        return msg

    def _send_email(self, msg: MIMEMultipart) -> None:
        """发送邮件

        Args:
            msg: 邮件消息对象
        """
        if self.use_tls:
            # 使用TLS
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
        else:
            # 不使用TLS
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

    def test_connection(self) -> bool:
        """测试SMTP连接

        Returns:
            是否连接成功
        """
        try:
            if self.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_password)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)

            logger.info("邮件通道连接测试成功")
            return True

        except Exception as e:
            logger.error(f"邮件通道连接测试失败: {e}")
            return False

    def add_recipient(self, email: str) -> None:
        """添加收件人

        Args:
            email: 收件人邮箱
        """
        if email not in self.email_to:
            self.email_to.append(email)
            logger.info(f"添加收件人: {email}")

    def remove_recipient(self, email: str) -> None:
        """移除收件人

        Args:
            email: 收件人邮箱
        """
        if email in self.email_to:
            self.email_to.remove(email)
            logger.info(f"移除收件人: {email}")

    def get_info(self) -> Dict[str, Any]:
        """获取通道信息

        Returns:
            通道信息字典
        """
        info = super().get_info()
        info.update({
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "email_from": self.email_from,
            "email_to_count": len(self.email_to),
            "use_tls": self.use_tls,
        })
        return info
