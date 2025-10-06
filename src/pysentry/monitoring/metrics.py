"""
Prometheus metrics collection for PySentry WAF.
"""

import time
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
from enum import Enum


class MetricType(Enum):
    """Metric types supported by Prometheus."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricsCollector:
    """
    Production-grade metrics collector for Prometheus.
    
    Collects and exposes metrics in Prometheus format for monitoring
    system health, performance, and security events.
    """
    
    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._summaries: Dict[str, list] = defaultdict(list)
        
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to add (default 1.0)
            labels: Optional labels dictionary
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self._counters[metric_key] += value
            
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """
        Set a gauge metric value.
        
        Args:
            name: Metric name
            value: Current value
            labels: Optional labels dictionary
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self._gauges[metric_key] = value
            
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """
        Record a histogram observation.
        
        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels dictionary
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self._histograms[metric_key].append(value)
            
    def observe_summary(self, name: str, value: float, labels: Optional[Dict] = None):
        """
        Record a summary observation.
        
        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels dictionary
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self._summaries[metric_key].append(value)
            
    def _build_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """Build metric key with labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
        
    def get_metrics(self) -> Dict[str, any]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary of all metrics
        """
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
                "summaries": {k: list(v) for k, v in self._summaries.items()},
            }
            
    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Metrics in Prometheus exposition format
        """
        lines = []
        
        # Export counters
        for key, value in self._counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")
            
        # Export gauges
        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")
            
        # Export histograms (simplified - would need buckets in production)
        for key, values in self._histograms.items():
            if values:
                lines.append(f"# TYPE {key.split('{')[0]} histogram")
                lines.append(f"{key}_sum {sum(values)}")
                lines.append(f"{key}_count {len(values)}")
                
        # Export summaries
        for key, values in self._summaries.items():
            if values:
                lines.append(f"# TYPE {key.split('{')[0]} summary")
                lines.append(f"{key}_sum {sum(values)}")
                lines.append(f"{key}_count {len(values)}")
                
        return "\n".join(lines)
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._summaries.clear()


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the singleton metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# WAF-specific metric helpers
class WAFMetrics:
    """High-level metrics for WAF operations."""
    
    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or get_metrics_collector()
        
    def record_request(self, method: str, path: str, status: int, duration: float):
        """Record an HTTP request."""
        labels = {"method": method, "path": path, "status": str(status)}
        self.collector.increment_counter("waf_requests_total", labels=labels)
        self.collector.observe_histogram("waf_request_duration_seconds", duration, labels=labels)
        
    def record_threat_detected(self, threat_type: str, severity: str):
        """Record a detected threat."""
        labels = {"type": threat_type, "severity": severity}
        self.collector.increment_counter("waf_threats_detected_total", labels=labels)
        
    def record_blocked_request(self, reason: str):
        """Record a blocked request."""
        labels = {"reason": reason}
        self.collector.increment_counter("waf_requests_blocked_total", labels=labels)
        
    def record_authentication(self, success: bool, method: str):
        """Record authentication attempt."""
        labels = {"success": str(success).lower(), "method": method}
        self.collector.increment_counter("waf_auth_attempts_total", labels=labels)
        
    def record_rate_limit(self, ip: str, endpoint: str):
        """Record rate limit hit."""
        labels = {"ip": ip, "endpoint": endpoint}
        self.collector.increment_counter("waf_rate_limit_hits_total", labels=labels)
        
    def set_active_connections(self, count: int):
        """Set current active connections."""
        self.collector.set_gauge("waf_active_connections", count)
        
    def set_cache_size(self, cache_name: str, size: int):
        """Set cache size."""
        labels = {"cache": cache_name}
        self.collector.set_gauge("waf_cache_size_bytes", size, labels=labels)
