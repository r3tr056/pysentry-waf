"""
Core WAF service for request analysis and threat detection
"""

from typing import Dict, Any, Optional
import time
import logging
from datetime import datetime

from pysentry.core.validator import InputValidator
from pysentry.core.classifier import ThreatClassifier
from pysentry.database import DatabaseService, RedisService
from pysentry.models import WAFRequest, RequestLog
from .ip_service import IPBlockingService

logger = logging.getLogger(__name__)


class WAFService:
    """Main WAF service for analyzing and blocking threats"""

    def __init__(
        self,
        db_service: DatabaseService,
        redis_service: Optional[RedisService] = None,
        validator: Optional[InputValidator] = None,
        classifier: Optional[ThreatClassifier] = None,
    ):
        self.db = db_service
        self.redis = redis_service
        self.validator = validator or InputValidator()
        self.classifier = classifier
        self.ip_service = IPBlockingService(db_service, redis_service)

    async def analyze_request(self, request_data: Dict[str, Any]) -> WAFRequest:
        """Analyze incoming request for threats"""
        start_time = time.time()

        # Create WAF request object
        waf_request = WAFRequest(**request_data)

        # Check if IP is blocked
        if await self.ip_service.is_ip_blocked(waf_request.origin):
            waf_request.threats["ip_blocked"] = "IP address is blocked"
            logger.warning(f"Blocked request from banned IP: {waf_request.origin}")
            return waf_request

        # Validate input
        validation_threats = await self._validate_input(waf_request)
        waf_request.threats.update(validation_threats)

        # ML classification (if available)
        if self.classifier:
            ml_threats = await self._classify_with_ml(waf_request)
            waf_request.threats.update(ml_threats)

        # Log request
        processing_time = (time.time() - start_time) * 1000
        await self._log_request(waf_request, processing_time)

        return waf_request

    async def _validate_input(self, request: WAFRequest) -> Dict[str, str]:
        """Validate request using input validator"""
        threats = {}

        # Validate query parameters
        if request.query_params:
            if self.validator.contains_sql_injection(request.query_params):
                threats["sql_injection"] = "query_params"
            if self.validator.contains_xss(request.query_params):
                threats["xss"] = "query_params"
            if self.validator.contains_command_injection(request.query_params):
                threats["command_injection"] = "query_params"
            if self.validator.contains_path_traversal(request.query_params):
                threats["path_traversal"] = "query_params"

        # Validate body
        if request.body:
            if self.validator.contains_sql_injection(request.body):
                threats["sql_injection"] = "body"
            if self.validator.contains_xss(request.body):
                threats["xss"] = "body"

        # Validate headers
        for header_name, header_value in request.headers.items():
            if not self.validator.validate_header(header_name, header_value):
                threats["header_injection"] = header_name

        return threats

    async def _classify_with_ml(self, request: WAFRequest) -> Dict[str, str]:
        """Classify request using ML model"""
        # This would use the actual classifier
        # For now, return empty dict (implementation in Phase 5)
        return {}

    async def _log_request(self, request: WAFRequest, processing_time: float) -> None:
        """Log request to database"""
        log_data = {
            "request_id": request.id or f"req_{datetime.utcnow().timestamp()}",
            "origin": request.origin,
            "host": request.host,
            "method": request.method,
            "path": request.path,
            "status_code": 403 if request.threats else 200,
            "blocked": bool(request.threats),
            "threats_detected": list(request.threats.keys()),
            "processing_time_ms": processing_time,
        }

        try:
            await self.db.log_request(log_data)
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

    async def get_request_logs(
        self, skip: int = 0, limit: int = 100, blocked_only: bool = False
    ) -> list:
        """Get request logs"""
        filters = {"blocked": True} if blocked_only else {}
        return await self.db.get_request_logs(skip, limit, filters)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get WAF statistics"""
        # Get recent logs
        logs = await self.get_request_logs(limit=1000)

        total_requests = len(logs)
        blocked_requests = sum(1 for log in logs if log.get("blocked"))
        threat_types = {}

        for log in logs:
            for threat in log.get("threats_detected", []):
                threat_types[threat] = threat_types.get(threat, 0) + 1

        return {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "allowed_requests": total_requests - blocked_requests,
            "block_rate": (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
            "threat_types": threat_types,
        }
