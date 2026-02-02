"""
REISHI 霊視 v5.0 - 通知服务

目的：发送通知（Telegram）
"""

import requests
from typing import Optional
from monitoring.realtime_monitor import Alert
from reporting.daily_report import DailyReport


class TelegramNotifier:
    """
    Telegram 通知服务
    """
    
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
    
    def send_daily_report(self, report: DailyReport):
        """发送每日报告"""
        if not self.enabled:
            print("📤 Telegram未配置，跳过发送每日报告")
            return
        
        message = self._format_report(report)
        self._send(message)
    
    def send_alert(self, alert: Alert):
        """发送即时警报"""
        if not self.enabled:
            print(f"📤 Telegram未配置，跳过警报: {alert.message}")
            return
        
        message = self._format_alert(alert)
        self._send(message, urgent=alert.severity == 'HIGH')
    
    def _format_report(self, report: DailyReport) -> str:
        """格式化报告为Telegram消息"""
        return f"<b>REISHI 霊視 v5.0 - 每日報告</b>\n\n{report.to_text()[:4000]}"
    
    def _format_alert(self, alert: Alert) -> str:
        """格式化警报为Telegram消息"""
        severity_emoji = {
            'HIGH': '🚨',
            'MEDIUM': '⚠️',
            'LOW': 'ℹ️'
        }
        emoji = severity_emoji.get(alert.severity, 'ℹ️')
        
        return f"{emoji} <b>{alert.type}</b>\n\n{alert.message}"
    
    def _send(self, message: str, urgent: bool = False):
        """发送讯息"""
        if not self.enabled:
            return
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_notification': not urgent
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✓ Telegram消息已发送")
            else:
                print(f"✗ Telegram发送失败: {response.status_code}")
        except Exception as e:
            print(f"✗ Telegram发送错误: {e}")
