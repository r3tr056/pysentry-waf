"""
Structured logging system for PySentry WAF.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """
    Production-grade structured logger with JSON formatting.
    
    Provides consistent, machine-readable logging for better
    observability in production environments.
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically module name)
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s',
                timestamp=True
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
    def _add_context(self, extra: Optional[Dict] = None) -> Dict:
        """Add contextual information to log entry."""
        context = {
            "service": "pysentry-waf",
            "timestamp": datetime.utcnow().isoformat(),
        }
        if extra:
            context.update(extra)
        return context
        
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        extra = self._add_context(kwargs)
        self.logger.info(message, extra=extra)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        extra = self._add_context(kwargs)
        self.logger.warning(message, extra=extra)
        
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        extra = self._add_context(kwargs)
        self.logger.error(message, extra=extra)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data."""
        extra = self._add_context(kwargs)
        self.logger.critical(message, extra=extra)
        
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        extra = self._add_context(kwargs)
        self.logger.debug(message, extra=extra)
        
    def log_request(self, method: str, path: str, status: int, duration: float, **kwargs):
        """Log HTTP request with standard fields."""
        self.info(
            "HTTP request processed",
            method=method,
            path=path,
            status_code=status,
            duration_ms=duration * 1000,
            **kwargs
        )
        
    def log_threat(self, threat_type: str, severity: str, source_ip: str, **kwargs):
        """Log detected threat."""
        self.warning(
            "Threat detected",
            threat_type=threat_type,
            severity=severity,
            source_ip=source_ip,
            **kwargs
        )
        
    def log_authentication(self, username: str, success: bool, method: str, **kwargs):
        """Log authentication attempt."""
        level = self.info if success else self.warning
        level(
            "Authentication attempt",
            username=username,
            success=success,
            method=method,
            **kwargs
        )
        
    def log_error_with_trace(self, message: str, exc: Exception, **kwargs):
        """Log error with exception trace."""
        extra = self._add_context({
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            **kwargs
        })
        self.logger.error(message, extra=extra, exc_info=True)


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Setup application-wide logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (default True)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Create new handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
