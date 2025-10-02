"""Tests for structured logging system."""

import pytest
import logging
import json
from io import StringIO
from pysentry.monitoring.logger import (
    StructuredLogger,
    setup_logging,
    get_logger
)


class TestStructuredLogger:
    """Tests for StructuredLogger class."""
    
    def setup_method(self):
        """Setup test logger."""
        self.logger = StructuredLogger("test_logger")
        
    def test_logger_creation(self):
        """Test logger can be created."""
        assert self.logger is not None
        assert self.logger.logger.name == "test_logger"
        
    def test_info_logging(self):
        """Test info level logging."""
        # This will log to stdout - just verify no exceptions
        self.logger.info("Test info message", key="value")
        
    def test_warning_logging(self):
        """Test warning level logging."""
        self.logger.warning("Test warning", key="value")
        
    def test_error_logging(self):
        """Test error level logging."""
        self.logger.error("Test error", key="value")
        
    def test_critical_logging(self):
        """Test critical level logging."""
        self.logger.critical("Test critical", key="value")
        
    def test_debug_logging(self):
        """Test debug level logging."""
        self.logger.debug("Test debug", key="value")
        
    def test_log_request(self):
        """Test HTTP request logging."""
        self.logger.log_request("GET", "/api/test", 200, 0.15)
        
    def test_log_threat(self):
        """Test threat logging."""
        self.logger.log_threat("sqli", "critical", "192.168.1.1")
        
    def test_log_authentication(self):
        """Test authentication logging."""
        self.logger.log_authentication("user@example.com", True, "jwt")
        self.logger.log_authentication("hacker@evil.com", False, "password")
        
    def test_log_error_with_trace(self):
        """Test error logging with exception trace."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            self.logger.log_error_with_trace("Error occurred", e)


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_setup_with_json_format(self):
        """Test setup with JSON format."""
        setup_logging(level="INFO", json_format=True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
    def test_setup_with_plain_format(self):
        """Test setup with plain text format."""
        setup_logging(level="DEBUG", json_format=False)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        
    def test_setup_reduces_third_party_noise(self):
        """Test that third-party loggers are quieted."""
        setup_logging()
        urllib3_logger = logging.getLogger("urllib3")
        asyncio_logger = logging.getLogger("asyncio")
        
        assert urllib3_logger.level == logging.WARNING
        assert asyncio_logger.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_returns_structured_logger(self):
        """Test get_logger returns StructuredLogger instance."""
        logger = get_logger("test")
        assert isinstance(logger, StructuredLogger)
        
    def test_get_logger_with_name(self):
        """Test logger gets correct name."""
        logger = get_logger("my_module")
        assert logger.logger.name == "my_module"
