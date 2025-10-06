"""Tests for alerting system."""

import pytest
from datetime import datetime, timedelta, timezone
from pysentry.monitoring.alerts import (
    AlertSeverity,
    AlertRule,
    Alert,
    AlertManager,
    get_alert_manager,
    DEFAULT_ALERT_RULES
)


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"


class TestAlertRule:
    """Tests for AlertRule model."""
    
    def test_alert_rule_creation(self):
        """Test creating AlertRule."""
        rule = AlertRule(
            name="test_rule",
            description="Test alert",
            severity=AlertSeverity.WARNING,
            metric_name="test_metric",
            threshold=100.0,
            comparison="gt",
            duration=60
        )
        
        assert rule.name == "test_rule"
        assert rule.threshold == 100.0
        assert rule.enabled is True


class TestAlert:
    """Tests for Alert model."""
    
    def test_alert_creation(self):
        """Test creating Alert."""
        alert = Alert(
            rule_name="test_rule",
            severity=AlertSeverity.CRITICAL,
            message="Test alert fired",
            triggered_at=datetime.now(timezone.utc),
            value=150.0,
            threshold=100.0
        )
        
        assert alert.rule_name == "test_rule"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.resolved_at is None


class TestAlertManager:
    """Tests for AlertManager class."""
    
    def setup_method(self):
        """Setup alert manager instance."""
        self.manager = AlertManager()
        
    def test_register_rule(self):
        """Test registering an alert rule."""
        rule = AlertRule(
            name="test_rule",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test_metric",
            threshold=100.0,
            comparison="gt",
            duration=60
        )
        
        self.manager.register_rule(rule)
        assert "test_rule" in self.manager._rules
        
    def test_register_callback(self):
        """Test registering alert callback."""
        called = []
        
        def callback(alert):
            called.append(alert)
            
        self.manager.register_callback(callback)
        assert len(self.manager._alert_callbacks) == 1
        
    def test_evaluate_rule_gt_triggered(self):
        """Test evaluating rule with > comparison (triggered)."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0  # Immediate
        )
        
        alert = self.manager.evaluate_rule(rule, 150.0)
        assert alert is not None
        assert alert.value == 150.0
        
    def test_evaluate_rule_gt_not_triggered(self):
        """Test evaluating rule with > comparison (not triggered)."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        alert = self.manager.evaluate_rule(rule, 50.0)
        assert alert is None
        
    def test_evaluate_rule_lt_triggered(self):
        """Test evaluating rule with < comparison (triggered)."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="lt",
            duration=0
        )
        
        alert = self.manager.evaluate_rule(rule, 50.0)
        assert alert is not None
        
    def test_evaluate_rule_eq_triggered(self):
        """Test evaluating rule with = comparison (triggered)."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="eq",
            duration=0
        )
        
        alert = self.manager.evaluate_rule(rule, 100.0)
        assert alert is not None
        
    def test_evaluate_rule_disabled(self):
        """Test evaluating disabled rule."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0,
            enabled=False
        )
        
        alert = self.manager.evaluate_rule(rule, 150.0)
        assert alert is None
        
    def test_evaluate_metrics(self):
        """Test evaluating multiple metrics."""
        rule1 = AlertRule(
            name="rule1",
            description="Test 1",
            severity=AlertSeverity.WARNING,
            metric_name="metric1",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        rule2 = AlertRule(
            name="rule2",
            description="Test 2",
            severity=AlertSeverity.WARNING,
            metric_name="metric2",
            threshold=50.0,
            comparison="lt",
            duration=0
        )
        
        self.manager.register_rule(rule1)
        self.manager.register_rule(rule2)
        
        metrics = {
            "metric1": 150.0,  # Should trigger
            "metric2": 25.0,   # Should trigger
        }
        
        alerts = self.manager.evaluate_metrics(metrics)
        assert len(alerts) == 2
        
    def test_fire_alert_callback(self):
        """Test alert callback is called."""
        called_alerts = []
        
        def callback(alert):
            called_alerts.append(alert)
            
        self.manager.register_callback(callback)
        
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        self.manager.register_rule(rule)
        self.manager.evaluate_metrics({"test": 150.0})
        
        assert len(called_alerts) == 1
        
    def test_resolve_alert(self):
        """Test resolving an alert."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        self.manager.register_rule(rule)
        self.manager.evaluate_metrics({"test": 150.0})
        
        assert "test" in self.manager._active_alerts
        
        self.manager.resolve_alert("test")
        assert "test" not in self.manager._active_alerts
        
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        self.manager.register_rule(rule)
        self.manager.evaluate_metrics({"test": 150.0})
        
        alerts = self.manager.get_active_alerts()
        assert len(alerts) == 1
        
    def test_get_active_alerts_filtered(self):
        """Test getting active alerts filtered by severity."""
        rule1 = AlertRule(
            name="rule1",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test1",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        rule2 = AlertRule(
            name="rule2",
            description="Test",
            severity=AlertSeverity.CRITICAL,
            metric_name="test2",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        self.manager.register_rule(rule1)
        self.manager.register_rule(rule2)
        self.manager.evaluate_metrics({"test1": 150.0, "test2": 150.0})
        
        critical_alerts = self.manager.get_active_alerts(
            severity=AlertSeverity.CRITICAL
        )
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL
        
    def test_get_alert_history(self):
        """Test getting alert history."""
        rule = AlertRule(
            name="test",
            description="Test",
            severity=AlertSeverity.WARNING,
            metric_name="test",
            threshold=100.0,
            comparison="gt",
            duration=0
        )
        
        self.manager.register_rule(rule)
        self.manager.evaluate_metrics({"test": 150.0})
        
        history = self.manager.get_alert_history()
        assert len(history) == 1


class TestDefaultAlertRules:
    """Tests for default alert rules."""
    
    def test_default_rules_exist(self):
        """Test that default rules are defined."""
        assert len(DEFAULT_ALERT_RULES) > 0
        
    def test_default_rules_have_required_fields(self):
        """Test default rules have all required fields."""
        for rule in DEFAULT_ALERT_RULES:
            assert rule.name
            assert rule.description
            assert rule.severity
            assert rule.metric_name
            assert rule.threshold
            assert rule.comparison
            assert rule.duration


class TestGetAlertManager:
    """Tests for get_alert_manager singleton."""
    
    def test_singleton_instance(self):
        """Test singleton pattern."""
        instance1 = get_alert_manager()
        instance2 = get_alert_manager()
        
        assert instance1 is instance2
        
    def test_default_rules_registered(self):
        """Test default rules are registered."""
        manager = get_alert_manager()
        assert len(manager._rules) >= len(DEFAULT_ALERT_RULES)
