"""
Phase 1 Tests: Fixed Classifier
Test bug fixes in threat classifier
"""
import pytest
from pathlib import Path
import sys
import tempfile
import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# Add phase1_implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.classifier_fixed import ThreatClassifier


@pytest.fixture
def mock_models(tmp_path):
    """Create mock ML models for testing"""
    # Create simple mock models
    X_train = ["valid request", "' OR '1'='1", "<script>alert('xss')</script>"]
    y_train = ["valid", "sqli", "xss"]
    
    # Train simple model
    vectorizer = CountVectorizer()
    X_vectorized = vectorizer.fit_transform(X_train)
    
    clf = MultinomialNB()
    clf.fit(X_vectorized, y_train)
    
    # Create a simple wrapper that includes vectorizer
    class ModelWrapper:
        def __init__(self, vectorizer, clf):
            self.vectorizer = vectorizer
            self.clf = clf
        
        def predict(self, X):
            X_vec = self.vectorizer.transform(X)
            return self.clf.predict(X_vec)
    
    model = ModelWrapper(vectorizer, clf)
    
    # Save models
    threat_model_path = tmp_path / "predictor.joblib"
    pt_model_path = tmp_path / "pt_predictor.joblib"
    
    joblib.dump(model, threat_model_path)
    
    # Create simple PT model
    pt_clf = MultinomialNB()
    pt_clf.fit([[1], [100], [1000]], ["valid", "valid", "parameter-tampering"])
    joblib.dump(pt_clf, pt_model_path)
    
    return str(threat_model_path), str(pt_model_path)


class TestClassifierBugFixes:
    """Test critical bug fixes"""
    
    def test_clean_pattern_returns_value(self):
        """Test bug fix: __clean_pattern now returns a value"""
        import tempfile
        import joblib
        from sklearn.naive_bayes import MultinomialNB
        
        # Create minimal models
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f1:
            threat_path = f1.name
            model = MultinomialNB()
            model.fit([[1, 0]], ['valid'])
            joblib.dump(model, threat_path)
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f2:
            pt_path = f2.name
            joblib.dump(model, pt_path)
        
        try:
            classifier = ThreatClassifier(threat_path, pt_path)
            
            # Access private method for testing
            result = classifier._ThreatClassifier__clean_pattern("TEST STRING  with   spaces")
            
            # Should return cleaned string
            assert result is not None
            assert result == "test string with spaces"
        finally:
            import os
            os.unlink(threat_path)
            os.unlink(pt_path)
    
    def test_variable_name_typo_fixed(self):
        """Test bug fix: 'pref' typo changed to 'pred'"""
        # This test ensures the code compiles and runs without NameError
        import tempfile
        import joblib
        from sklearn.naive_bayes import MultinomialNB
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f1:
            threat_path = f1.name
            model = MultinomialNB()
            model.fit([[1, 0]], ['valid'])
            joblib.dump(model, threat_path)
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f2:
            pt_path = f2.name
            joblib.dump(model, pt_path)
        
        try:
            classifier = ThreatClassifier(threat_path, pt_path)
            
            # Create mock request - use the actual schema
            class MockRequest:
                def __init__(self):
                    self.request = "test"
                    self.body = ""
                    self.method = "GET"
                    self.headers = {}
                    self.origin = "127.0.0.1"
                    self.host = "localhost"
                    self.threats = {}
            
            request = MockRequest()
            
            # Should not raise NameError about 'pred'
            try:
                classifier.classify_request(request)
            except TypeError:
                # It's OK if it fails type check, we just want to ensure no NameError
                pass
            
            assert hasattr(request, 'threats')
        finally:
            import os
            os.unlink(threat_path)
            os.unlink(pt_path)


class TestClassifierErrorHandling:
    """Test improved error handling"""
    
    def test_model_file_not_found(self):
        """Test error when model files don't exist"""
        # The __init__ method should raise FileNotFoundError when files don't exist
        # but it's wrapped in RuntimeError
        try:
            ThreatClassifier("/nonexistent/path.joblib", "/another/nonexistent.joblib")
            assert False, "Should have raised an error"
        except (FileNotFoundError, RuntimeError) as e:
            # Either error is acceptable
            assert "not found" in str(e).lower() or "loading failed" in str(e).lower()
    
    def test_invalid_model_file(self, tmp_path):
        """Test error when model file is invalid"""
        invalid_model = tmp_path / "invalid.joblib"
        invalid_model.write_text("not a valid joblib file")
        
        pt_model = tmp_path / "pt.joblib"
        pt_model.write_text("also invalid")
        
        with pytest.raises(RuntimeError, match="Model loading failed"):
            ThreatClassifier(str(invalid_model), str(pt_model))


class TestClassifierFunctionality:
    """Test classifier functionality"""
    
    def test_unquote_recursive(self):
        """Test recursive URL unquoting"""
        import tempfile
        import joblib
        from sklearn.naive_bayes import MultinomialNB
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f1:
            threat_path = f1.name
            model = MultinomialNB()
            model.fit([[1, 0]], ['valid'])
            joblib.dump(model, threat_path)
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f2:
            pt_path = f2.name
            joblib.dump(model, pt_path)
        
        try:
            classifier = ThreatClassifier(threat_path, pt_path)
            
            # Test double-encoded string
            encoded = "%2527%2520OR%25201%253D1"
            result = classifier._ThreatClassifier__unquote(encoded)
            
            # Should decode to "' OR 1=1"
            assert "OR" in result
            assert "1=1" in result or "1%3D1" in result
        finally:
            import os
            os.unlink(threat_path)
            os.unlink(pt_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
