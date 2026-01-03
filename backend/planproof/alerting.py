"""
Alerting and monitoring infrastructure for production.

Supports multiple alerting channels:
- Email (SMTP)
- Azure Monitor (Application Insights)
- Webhooks (Slack, Teams, custom endpoints)
- Logging (for fallback)

Usage:
    from planproof.alerting import AlertManager, AlertSeverity, init_alerts
    
    # Initialize at app startup
    alert_mgr = init_alerts()
    
    # Send alerts
    alert_mgr.alert(
        title="Database Connection Lost",
        message="Cannot connect to PostgreSQL database",
        severity=AlertSeverity.CRITICAL
    )
"""

import os
import logging
import json
import traceback
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

LOGGER = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Available alert channels."""
    EMAIL = "email"
    AZURE_MONITOR = "azure_monitor"
    WEBHOOK = "webhook"
    LOG = "log"


class AlertManager:
    """Centralized alerting system with multiple channel support."""
    
    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        min_severity: AlertSeverity = AlertSeverity.ERROR
    ):
        """
        Initialize alert manager.
        
        Args:
            channels: List of alert channels to use. If None, auto-detect.
            min_severity: Minimum severity level to send alerts
        """
        self.channels = channels or self._auto_detect_channels()
        self.min_severity = min_severity
        self._alert_count: Dict[AlertSeverity, int] = {s: 0 for s in AlertSeverity}
        self._last_alert_time: Optional[datetime] = None
        
        # Rate limiting
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max = 10  # max alerts per window
        self._recent_alerts: List[datetime] = []
        
        LOGGER.info(f"Alert manager initialized with channels: {self.channels}")
    
    def _auto_detect_channels(self) -> List[AlertChannel]:
        """Auto-detect available alert channels."""
        channels = [AlertChannel.LOG]  # Always include logging
        
        # Check for email configuration
        if os.getenv("SMTP_HOST") and os.getenv("ALERT_EMAIL_TO"):
            channels.append(AlertChannel.EMAIL)
        
        # Check for Azure Monitor
        if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY"):
            channels.append(AlertChannel.AZURE_MONITOR)
        
        # Check for webhook
        if os.getenv("ALERT_WEBHOOK_URL"):
            channels.append(AlertChannel.WEBHOOK)
        
        return channels
    
    def alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert through configured channels.
        
        Args:
            title: Alert title/subject
            message: Detailed alert message
            severity: Alert severity level
            metadata: Additional metadata (e.g., error details, context)
        
        Returns:
            True if alert was sent successfully through at least one channel
        """
        # Check severity threshold
        if self._compare_severity(severity, self.min_severity) < 0:
            LOGGER.debug(f"Alert skipped (below min severity): {title}")
            return False
        
        # Check rate limiting
        if self._is_rate_limited():
            LOGGER.warning(f"Alert rate limited: {title}")
            return False
        
        # Track alert
        self._alert_count[severity] += 1
        self._last_alert_time = datetime.now(timezone.utc)
        self._recent_alerts.append(self._last_alert_time)
        
        # Build alert payload
        alert_data = {
            "title": title,
            "message": message,
            "severity": severity.value,
            "timestamp": self._last_alert_time.isoformat(),
            "metadata": metadata or {},
            "environment": os.getenv("ENVIRONMENT", "development"),
            "hostname": os.getenv("HOSTNAME", "unknown"),
        }
        
        # Send through all channels
        success = False
        for channel in self.channels:
            try:
                if channel == AlertChannel.LOG:
                    self._send_log(alert_data)
                    success = True
                elif channel == AlertChannel.EMAIL:
                    self._send_email(alert_data)
                    success = True
                elif channel == AlertChannel.AZURE_MONITOR:
                    self._send_azure_monitor(alert_data)
                    success = True
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook(alert_data)
                    success = True
            except Exception as e:
                LOGGER.error(f"Failed to send alert via {channel}: {e}")
        
        return success
    
    def _is_rate_limited(self) -> bool:
        """Check if alerts are rate limited."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.rate_limit_window
        
        # Remove old alerts
        self._recent_alerts = [
            t for t in self._recent_alerts
            if t.timestamp() > cutoff
        ]
        
        return len(self._recent_alerts) >= self.rate_limit_max
    
    def _compare_severity(self, s1: AlertSeverity, s2: AlertSeverity) -> int:
        """Compare two severity levels (-1, 0, 1)."""
        order = [
            AlertSeverity.DEBUG,
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL
        ]
        idx1 = order.index(s1)
        idx2 = order.index(s2)
        return (idx1 > idx2) - (idx1 < idx2)
    
    def _send_log(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to logging system."""
        severity = alert_data["severity"]
        title = alert_data["title"]
        message = alert_data["message"]
        
        log_message = f"[ALERT] {title}: {message}"
        
        if severity == "critical":
            LOGGER.critical(log_message, extra={"alert_data": alert_data})
        elif severity == "error":
            LOGGER.error(log_message, extra={"alert_data": alert_data})
        elif severity == "warning":
            LOGGER.warning(log_message, extra={"alert_data": alert_data})
        else:
            LOGGER.info(log_message, extra={"alert_data": alert_data})
    
    def _send_email(self, alert_data: Dict[str, Any]) -> None:
        """Send alert via email."""
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("ALERT_EMAIL_FROM", "alerts@planproof.local")
        to_emails = os.getenv("ALERT_EMAIL_TO", "").split(",")
        
        if not to_emails or not to_emails[0]:
            raise ValueError("ALERT_EMAIL_TO not configured")
        
        # Build email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{alert_data['severity'].upper()}] {alert_data['title']}"
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)
        
        # HTML body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="padding: 20px; border-left: 4px solid {'#dc3545' if alert_data['severity'] in ['error', 'critical'] else '#ffc107'};">
              <h2 style="color: {'#dc3545' if alert_data['severity'] in ['error', 'critical'] else '#ffc107'};">
                {alert_data['title']}
              </h2>
              <p><strong>Severity:</strong> {alert_data['severity'].upper()}</p>
              <p><strong>Time:</strong> {alert_data['timestamp']}</p>
              <p><strong>Environment:</strong> {alert_data['environment']}</p>
              <hr>
              <p><strong>Message:</strong></p>
              <pre style="background: #f5f5f5; padding: 10px;">{alert_data['message']}</pre>
              
              {f'<p><strong>Metadata:</strong></p><pre style="background: #f5f5f5; padding: 10px;">{json.dumps(alert_data["metadata"], indent=2)}</pre>' if alert_data['metadata'] else ''}
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, "html"))
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        LOGGER.debug(f"Alert email sent to {to_emails}")
    
    def _send_azure_monitor(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to Azure Monitor / Application Insights."""
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler
        except ImportError:
            LOGGER.warning("Azure Monitor requires: pip install opencensus-ext-azure")
            return
        
        connection_string = (
            os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or
            f"InstrumentationKey={os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')}"
        )
        
        # Log to Application Insights
        handler = AzureLogHandler(connection_string=connection_string)
        alert_logger = logging.getLogger("planproof.alerts")
        alert_logger.addHandler(handler)
        
        alert_logger.error(
            f"{alert_data['title']}: {alert_data['message']}",
            extra={"custom_dimensions": alert_data}
        )
        
        LOGGER.debug("Alert sent to Azure Monitor")
    
    def _send_webhook(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to webhook endpoint (Slack, Teams, etc.)."""
        webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("ALERT_WEBHOOK_URL not configured")
        
        # Format for Slack/Teams
        color_map = {
            "critical": "#dc3545",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
            "debug": "#6c757d"
        }
        
        payload = {
            "text": f"[{alert_data['severity'].upper()}] {alert_data['title']}",
            "attachments": [{
                "color": color_map.get(alert_data['severity'], "#6c757d"),
                "fields": [
                    {"title": "Message", "value": alert_data['message'], "short": False},
                    {"title": "Severity", "value": alert_data['severity'], "short": True},
                    {"title": "Environment", "value": alert_data['environment'], "short": True},
                    {"title": "Time", "value": alert_data['timestamp'], "short": False},
                ]
            }]
        }
        
        if alert_data['metadata']:
            payload["attachments"][0]["fields"].append({
                "title": "Metadata",
                "value": f"```{json.dumps(alert_data['metadata'], indent=2)}```",
                "short": False
            })
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        
        LOGGER.debug(f"Alert sent to webhook: {webhook_url}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alerting statistics."""
        return {
            "total_alerts": sum(self._alert_count.values()),
            "by_severity": dict(self._alert_count),
            "last_alert_time": self._last_alert_time.isoformat() if self._last_alert_time else None,
            "recent_alerts_count": len(self._recent_alerts),
            "rate_limited": self._is_rate_limited(),
        }
    
    def clear_stats(self) -> None:
        """Clear alerting statistics."""
        self._alert_count = {s: 0 for s in AlertSeverity}
        self._last_alert_time = None
        self._recent_alerts = []


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def init_alerts(
    channels: Optional[List[AlertChannel]] = None,
    min_severity: AlertSeverity = AlertSeverity.ERROR
) -> AlertManager:
    """
    Initialize the global alert manager.
    
    Args:
        channels: List of alert channels to use
        min_severity: Minimum severity level to send alerts
    
    Returns:
        Initialized AlertManager instance
    """
    global _alert_manager
    _alert_manager = AlertManager(channels=channels, min_severity=min_severity)
    return _alert_manager


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    if _alert_manager is None:
        return init_alerts()
    return _alert_manager


def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.ERROR,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Convenience function to send an alert.
    
    Args:
        title: Alert title
        message: Alert message
        severity: Alert severity
        metadata: Additional metadata
    
    Returns:
        True if alert was sent successfully
    """
    manager = get_alert_manager()
    return manager.alert(title, message, severity, metadata)


# Convenience functions for common alert types
def alert_database_error(error: Exception, context: str = "") -> None:
    """Send database error alert."""
    send_alert(
        title="Database Error",
        message=f"{context}: {str(error)}",
        severity=AlertSeverity.CRITICAL,
        metadata={
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc(),
            "context": context
        }
    )


def alert_api_error(error: Exception, endpoint: str) -> None:
    """Send API error alert."""
    send_alert(
        title="API Error",
        message=f"Error in endpoint {endpoint}: {str(error)}",
        severity=AlertSeverity.ERROR,
        metadata={
            "error_type": type(error).__name__,
            "endpoint": endpoint,
            "traceback": traceback.format_exc()
        }
    )


def alert_processing_failure(document_id: int, error: Exception) -> None:
    """Send processing failure alert."""
    send_alert(
        title="Document Processing Failed",
        message=f"Failed to process document {document_id}: {str(error)}",
        severity=AlertSeverity.ERROR,
        metadata={
            "document_id": document_id,
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        }
    )


def alert_performance_degradation(metric: str, value: float, threshold: float) -> None:
    """Send performance degradation alert."""
    send_alert(
        title="Performance Degradation Detected",
        message=f"{metric} is {value:.2f} (threshold: {threshold:.2f})",
        severity=AlertSeverity.WARNING,
        metadata={
            "metric": metric,
            "value": value,
            "threshold": threshold
        }
    )
