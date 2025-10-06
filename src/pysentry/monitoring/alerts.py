"""
Alerting system for PySentry WAF.
"""

from enum import Enum
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from collections import defaultdict


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertRule(BaseModel):
    """Definition of an alert rule."""
    
    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq"
    duration: int  # seconds - how long condition must persist
    enabled: bool = True


class Alert(BaseModel):
    """An active or fired alert."""
    
    rule_name: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    value: float
    threshold: float
    labels: Optional[Dict] = None


class AlertManager:
    """
    Production-grade alert management system.
    
    Evaluates alert rules against metrics and fires alerts
    when thresholds are breached.
    """
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        self._rule_states: Dict[str, Dict] = defaultdict(dict)
        
    def register_rule(self, rule: AlertRule):
        """
        Register an alert rule.
        
        Args:
            rule: AlertRule to register
        """
        self._rules[rule.name] = rule
        
    def register_callback(self, callback: Callable[[Alert], None]):
        """
        Register a callback to be called when alerts fire.
        
        Args:
            callback: Function to call with Alert object
        """
        self._alert_callbacks.append(callback)
        
    def evaluate_rule(self, rule: AlertRule, current_value: float) -> Optional[Alert]:
        """
        Evaluate a single rule against current value.
        
        Args:
            rule: AlertRule to evaluate
            current_value: Current metric value
            
        Returns:
            Alert if rule is triggered, None otherwise
        """
        if not rule.enabled:
            return None
            
        triggered = False
        
        if rule.comparison == "gt":
            triggered = current_value > rule.threshold
        elif rule.comparison == "lt":
            triggered = current_value < rule.threshold
        elif rule.comparison == "eq":
            triggered = current_value == rule.threshold
            
        now = datetime.now(timezone.utc)
        
        # Check if condition has persisted for required duration
        state = self._rule_states[rule.name]
        
        if triggered:
            if "first_triggered" not in state:
                state["first_triggered"] = now
                
            duration = (now - state["first_triggered"]).total_seconds()
            
            if duration >= rule.duration:
                # Fire alert
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.description}: {current_value} {rule.comparison} {rule.threshold}",
                    triggered_at=now,
                    value=current_value,
                    threshold=rule.threshold
                )
                
                # Reset state
                state.clear()
                
                return alert
        else:
            # Clear state if no longer triggered
            state.clear()
            
        return None
        
    def evaluate_metrics(self, metrics: Dict[str, float]) -> List[Alert]:
        """
        Evaluate all rules against current metrics.
        
        Args:
            metrics: Dictionary of metric_name -> value
            
        Returns:
            List of fired alerts
        """
        alerts = []
        
        for rule in self._rules.values():
            if rule.metric_name in metrics:
                alert = self.evaluate_rule(rule, metrics[rule.metric_name])
                if alert:
                    alerts.append(alert)
                    self._fire_alert(alert)
                    
        return alerts
        
    def _fire_alert(self, alert: Alert):
        """Fire an alert and trigger callbacks."""
        # Store in active alerts
        self._active_alerts[alert.rule_name] = alert
        
        # Add to history
        self._alert_history.append(alert)
        
        # Call callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                # Log but don't fail
                print(f"Alert callback failed: {e}")
                
    def resolve_alert(self, rule_name: str):
        """
        Resolve an active alert.
        
        Args:
            rule_name: Name of rule to resolve
        """
        if rule_name in self._active_alerts:
            alert = self._active_alerts.pop(rule_name)
            alert.resolved_at = datetime.now(timezone.utc)
            
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get active alerts, optionally filtered by severity.
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of active alerts
        """
        alerts = list(self._active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
            
        return alerts
        
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity filter
            
        Returns:
            List of historical alerts
        """
        alerts = self._alert_history[-limit:]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
            
        return alerts


# Default alert rules for WAF
DEFAULT_ALERT_RULES = [
    AlertRule(
        name="high_threat_detection_rate",
        description="High rate of threat detection",
        severity=AlertSeverity.WARNING,
        metric_name="waf_threats_detected_per_minute",
        threshold=50.0,
        comparison="gt",
        duration=60
    ),
    AlertRule(
        name="high_request_block_rate",
        description="High rate of blocked requests",
        severity=AlertSeverity.WARNING,
        metric_name="waf_block_rate_percent",
        threshold=20.0,
        comparison="gt",
        duration=60
    ),
    AlertRule(
        name="critical_auth_failures",
        description="Critical number of authentication failures",
        severity=AlertSeverity.CRITICAL,
        metric_name="waf_auth_failure_rate",
        threshold=100.0,
        comparison="gt",
        duration=30
    ),
    AlertRule(
        name="high_rate_limit_hits",
        description="High rate of rate limit violations",
        severity=AlertSeverity.WARNING,
        metric_name="waf_rate_limit_hits_per_minute",
        threshold=1000.0,
        comparison="gt",
        duration=60
    ),
    AlertRule(
        name="low_memory",
        description="Low available memory",
        severity=AlertSeverity.CRITICAL,
        metric_name="system_memory_available_percent",
        threshold=10.0,
        comparison="lt",
        duration=30
    ),
    AlertRule(
        name="high_response_time",
        description="High average response time",
        severity=AlertSeverity.WARNING,
        metric_name="waf_avg_response_time_ms",
        threshold=1000.0,
        comparison="gt",
        duration=120
    ),
]


# Singleton instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the singleton alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        # Register default rules
        for rule in DEFAULT_ALERT_RULES:
            _alert_manager.register_rule(rule)
    return _alert_manager
