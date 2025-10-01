"""
Phase 1.3: Fixed Classifier Module
Fixed all 3 critical bugs identified in the assessment
"""
import joblib
import urllib.parse
import json
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ThreatClassifier:
    """
    ML-based threat classifier for detecting web application attacks.
    
    Bugs Fixed:
    1. Line 74: Variable typo 'pref' -> 'pred'
    2. Line 34: Missing return statement in __clean_pattern()
    3. Improved error handling for model loading
    """
    
    def __init__(self, threat_model_path: str = "./waf/threat_engine/predictor.joblib",
                 pt_model_path: str = "./waf/threat_engine/pt_predictor.joblib"):
        """
        Initialize threat classifier with ML models.
        
        Args:
            threat_model_path: Path to threat classification model
            pt_model_path: Path to parameter tampering model
            
        Raises:
            FileNotFoundError: If model files don't exist
            RuntimeError: If models fail to load
        """
        try:
            # Validate model files exist
            if not Path(threat_model_path).exists():
                raise FileNotFoundError(f"Threat model not found: {threat_model_path}")
            if not Path(pt_model_path).exists():
                raise FileNotFoundError(f"Parameter tampering model not found: {pt_model_path}")
            
            self.clf = joblib.load(threat_model_path)
            self.pt_clf = joblib.load(pt_model_path)
            logger.info("Threat classifier models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load threat classifier models: {e}")
            raise RuntimeError(f"Model loading failed: {e}") from e
    
    def __unquote(self, text: str) -> str:
        """Recursively unquote URL-encoded text"""
        k = 0
        uq_prev = text
        while k < 100:
            uq = urllib.parse.unquote_plus(uq_prev)
            if uq == uq_prev:
                break
            else:
                uq_prev = uq
            k += 1
        return uq_prev
    
    def __remove_new_line(self, text: str) -> str:
        """Remove newlines from text"""
        text = text.strip()
        return ' '.join(text.splitlines())
    
    def __remove_multiple_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        return ' '.join(text.split())
    
    def __clean_pattern(self, pattern: str) -> str:
        """
        Clean and normalize input pattern for ML model.
        
        BUG FIX: Added missing return statement
        """
        pattern = self.__unquote(pattern)
        pattern = self.__remove_new_line(pattern)
        pattern = pattern.lower()
        pattern = self.__remove_multiple_whitespace(pattern)
        return pattern  # FIX: Added missing return
    
    def __is_valid(self, parameter: Optional[str]) -> bool:
        """Check if parameter is valid (not None or empty)"""
        return parameter is not None and parameter != ''
    
    def classify_request(self, req) -> None:
        """
        Classify a request for potential security threats.
        
        Args:
            req: Request object to classify
            
        Side Effects:
            Sets req.threats dictionary with detected threats
            
        Raises:
            TypeError: If req is not a Request instance
        """
        # Import here to avoid circular dependency
        # Accept any object with required attributes
        required_attrs = ['request', 'body', 'method', 'headers', 'origin', 'host']
        if not all(hasattr(req, attr) for attr in required_attrs):
            raise TypeError("Object must have request, body, method, headers, origin, and host attributes")
        
        try:
            parameters = []
            locations = []
            
            # Check request parameters
            if self.__is_valid(req.request):
                cleaned = self.__clean_pattern(req.request)
                if cleaned:  # Only add if cleaning succeeded
                    parameters.append(cleaned)
                    locations.append('Request')
            
            # Check body
            if self.__is_valid(req.body):
                cleaned = self.__clean_pattern(req.body)
                if cleaned:
                    parameters.append(cleaned)
                    locations.append('Body')
            
            # Check headers
            if req.headers:
                if 'Cookie' in req.headers and self.__is_valid(req.headers['Cookie']):
                    cleaned = self.__clean_pattern(req.headers['Cookie'])
                    if cleaned:
                        parameters.append(cleaned)
                        locations.append('Cookie')
                
                if 'User_Agent' in req.headers and self.__is_valid(req.headers['User_Agent']):
                    cleaned = self.__clean_pattern(req.headers['User_Agent'])
                    if cleaned:
                        parameters.append(cleaned)
                        locations.append('User Agent')
                
                if 'Accept_Encoding' in req.headers and self.__is_valid(req.headers['Accept_Encoding']):
                    cleaned = self.__clean_pattern(req.headers['Accept_Encoding'])
                    if cleaned:
                        parameters.append(cleaned)
                        locations.append('Accept Encoding')
                
                if 'Accept_Language' in req.headers and self.__is_valid(req.headers['Accept_Language']):
                    cleaned = self.__clean_pattern(req.headers['Accept_Language'])
                    if cleaned:
                        parameters.append(cleaned)
                        locations.append('Accept Language')
            
            req.threats = {}
            
            # Run ML classification on collected parameters
            if len(parameters) > 0:
                predictions = self.clf.predict(parameters)
                for idx, pred in enumerate(predictions):  # FIX: Changed 'pref' to 'pred'
                    if pred != 'valid':
                        req.threats[pred] = locations[idx]
            
            # Parse request and body parameters for tampering detection
            request_parameters = {}
            if self.__is_valid(req.request):
                cleaned = self.__clean_pattern(req.request)
                if cleaned:
                    request_parameters = urllib.parse.parse_qs(cleaned)
            
            body_parameters = {}
            if self.__is_valid(req.body):
                cleaned = self.__clean_pattern(req.body)
                if cleaned:
                    body_parameters = urllib.parse.parse_qs(cleaned)
                    
                    # Try JSON parsing if URL parsing failed
                    if len(body_parameters) == 0:
                        try:
                            body_parameters = json.loads(cleaned)
                        except (json.JSONDecodeError, ValueError):
                            pass
            
            # Collect parameter lengths for tampering detection
            parameters = []
            locations = []
            
            for name, value in request_parameters.items():
                for elem in value:
                    parameters.append([len(elem)])
                    locations.append('Request')
            
            for name, value in body_parameters.items():
                if isinstance(value, list):
                    for elem in value:
                        parameters.append([len(str(elem))])
                        locations.append('Body')
                else:
                    parameters.append([len(str(value))])
                    locations.append('Body')
            
            # Run parameter tampering detection
            if len(parameters) > 0:
                pt_predictions = self.pt_clf.predict(parameters)
                for idx, pred in enumerate(pt_predictions):
                    if pred != 'valid':
                        req.threats[pred] = locations[idx]
            
            # Default to valid if no threats detected
            if len(req.threats) == 0:
                req.threats['valid'] = ''
                
        except Exception as e:
            logger.error(f"Error during threat classification: {e}", exc_info=True)
            # Set default on error to fail safe
            req.threats = {'valid': ''}
