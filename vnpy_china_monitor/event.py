"""
监控告警事件定义

定义模块内部使用的事件类型
"""

from vnpy.event import Event

# 监控数据事件
EVENT_MONITOR_DATA = "eMonitorData"

# 告警发送事件
EVENT_ALERT_SENT = "eAlertSent"

# 告警确认事件
EVENT_ALERT_ACKNOWLEDGED = "eAlertAck"

# 风控告警事件
EVENT_RISK_ALERT = "eRiskAlert"

# 事件数据格式
MonitorDataEvent = dict
"""
{
    "monitor_type": "system|trade|risk",
    "name": "memory|cpu|position|...",
    "value": ...,
    "status": "normal|warning|critical",
    "timestamp": "..."
}
"""

AlertSentEvent = dict
"""
{
    "alert_id": "...",
    "title": "...",
    "severity": "...",
    "timestamp": "..."
}
"""

AlertAckEvent = dict
"""
{
    "alert_id": "...",
    "timestamp": "..."
}
"""

RiskAlertEvent = dict
"""
{
    "rule_name": "...",
    "rule_type": "...",
    "message": "...",
    "severity": "...",
    "timestamp": "..."
}
"""
