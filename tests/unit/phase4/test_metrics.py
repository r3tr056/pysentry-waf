"""Tests for metrics collection system."""

import pytest
from pysentry.monitoring.metrics import (
    MetricsCollector,
    WAFMetrics,
    get_metrics_collector,
    MetricType
)


class TestMetricsCollector:
    """Tests for MetricsCollector class."""
    
    def setup_method(self):
        """Setup test with fresh collector."""
        self.collector = MetricsCollector()
        
    def test_increment_counter(self):
        """Test counter increments."""
        self.collector.increment_counter("test_counter", 1.0)
        self.collector.increment_counter("test_counter", 2.0)
        
        metrics = self.collector.get_metrics()
        assert metrics["counters"]["test_counter"] == 3.0
        
    def test_counter_with_labels(self):
        """Test counter with labels."""
        self.collector.increment_counter(
            "test_counter",
            1.0,
            labels={"method": "GET", "status": "200"}
        )
        
        metrics = self.collector.get_metrics()
        assert len(metrics["counters"]) == 1
        key = list(metrics["counters"].keys())[0]
        assert "method" in key
        assert "GET" in key
        
    def test_set_gauge(self):
        """Test gauge setting."""
        self.collector.set_gauge("test_gauge", 42.0)
        self.collector.set_gauge("test_gauge", 100.0)
        
        metrics = self.collector.get_metrics()
        assert metrics["gauges"]["test_gauge"] == 100.0
        
    def test_observe_histogram(self):
        """Test histogram observations."""
        self.collector.observe_histogram("test_histogram", 1.5)
        self.collector.observe_histogram("test_histogram", 2.5)
        self.collector.observe_histogram("test_histogram", 3.5)
        
        metrics = self.collector.get_metrics()
        assert len(metrics["histograms"]["test_histogram"]) == 3
        assert sum(metrics["histograms"]["test_histogram"]) == 7.5
        
    def test_observe_summary(self):
        """Test summary observations."""
        self.collector.observe_summary("test_summary", 10.0)
        self.collector.observe_summary("test_summary", 20.0)
        
        metrics = self.collector.get_metrics()
        assert len(metrics["summaries"]["test_summary"]) == 2
        
    def test_prometheus_format_export(self):
        """Test Prometheus format export."""
        self.collector.increment_counter("requests_total", 10)
        self.collector.set_gauge("active_connections", 5)
        
        output = self.collector.export_prometheus_format()
        
        assert "# TYPE requests_total counter" in output
        assert "requests_total 10" in output
        assert "# TYPE active_connections gauge" in output
        assert "active_connections 5" in output
        
    def test_reset(self):
        """Test metrics reset."""
        self.collector.increment_counter("test", 1.0)
        self.collector.set_gauge("test_gauge", 42.0)
        
        self.collector.reset()
        
        metrics = self.collector.get_metrics()
        assert len(metrics["counters"]) == 0
        assert len(metrics["gauges"]) == 0
        
    def test_singleton_instance(self):
        """Test singleton pattern."""
        instance1 = get_metrics_collector()
        instance2 = get_metrics_collector()
        
        assert instance1 is instance2


class TestWAFMetrics:
    """Tests for WAFMetrics helper class."""
    
    def setup_method(self):
        """Setup with fresh collector."""
        collector = MetricsCollector()
        self.waf_metrics = WAFMetrics(collector)
        self.collector = collector
        
    def test_record_request(self):
        """Test HTTP request recording."""
        self.waf_metrics.record_request("GET", "/api/test", 200, 0.15)
        
        metrics = self.collector.get_metrics()
        assert len(metrics["counters"]) == 1
        assert len(metrics["histograms"]) == 1
        
    def test_record_threat_detected(self):
        """Test threat detection recording."""
        self.waf_metrics.record_threat_detected("sqli", "critical")
        self.waf_metrics.record_threat_detected("xss", "high")
        
        metrics = self.collector.get_metrics()
        assert len(metrics["counters"]) == 2
        
    def test_record_blocked_request(self):
        """Test blocked request recording."""
        self.waf_metrics.record_blocked_request("rate_limit")
        
        metrics = self.collector.get_metrics()
        counters = metrics["counters"]
        assert any("waf_requests_blocked_total" in k for k in counters.keys())
        
    def test_record_authentication(self):
        """Test authentication recording."""
        self.waf_metrics.record_authentication(True, "jwt")
        self.waf_metrics.record_authentication(False, "api_key")
        
        metrics = self.collector.get_metrics()
        assert len(metrics["counters"]) == 2
        
    def test_record_rate_limit(self):
        """Test rate limit recording."""
        self.waf_metrics.record_rate_limit("192.168.1.1", "/api/test")
        
        metrics = self.collector.get_metrics()
        counters = metrics["counters"]
        assert any("waf_rate_limit_hits_total" in k for k in counters.keys())
        
    def test_set_active_connections(self):
        """Test active connections gauge."""
        self.waf_metrics.set_active_connections(42)
        
        metrics = self.collector.get_metrics()
        assert metrics["gauges"]["waf_active_connections"] == 42
        
    def test_set_cache_size(self):
        """Test cache size gauge."""
        self.waf_metrics.set_cache_size("redis", 1024)
        
        metrics = self.collector.get_metrics()
        gauges = metrics["gauges"]
        assert any("waf_cache_size_bytes" in k for k in gauges.keys())
