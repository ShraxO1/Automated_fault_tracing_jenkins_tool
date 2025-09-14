"""
Optional ML classification module
TF-IDF + Logistic Regression for augmenting rule-based classification
Graceful degradation when ML dependencies are not available
"""

import os
from typing import List, Optional
from models.pydantic_models import TrainingData, ClassificationResult

class MLClassifier:
    """Optional ML classifier with graceful degradation"""

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.trained = False
        self.available = self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Check if ML dependencies are available"""
        try:
            import sklearn
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import LabelEncoder
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """Check if ML functionality is available"""
        return self.available and os.getenv("ENABLE_ML", "0") == "1"

    def is_trained(self) -> bool:
        """Check if model is trained"""
        return self.trained and self.model is not None

    def train(self, training_data: List[TrainingData]) -> None:
        """
        Train the ML classifier

        Args:
            training_data: List of training samples with text and labels
        """
        if not self.is_available():
            raise RuntimeError("ML dependencies not available or not enabled")

        if len(training_data) < 2:
            raise ValueError("Need at least 2 training samples")

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import LabelEncoder
            import numpy as np
        except ImportError:
            raise RuntimeError("scikit-learn not available")

        # Prepare data
        texts = [sample.text for sample in training_data]
        labels = [sample.label for sample in training_data]

        # Initialize components
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english'
        )

        self.label_encoder = LabelEncoder()

        # Fit vectorizer and encode labels
        X = self.vectorizer.fit_transform(texts)
        y = self.label_encoder.fit_transform(labels)

        # Train logistic regression
        self.model = LogisticRegression(
            random_state=42,
            max_iter=1000,
            multi_class='ovr'
        )
        self.model.fit(X, y)

        self.trained = True

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify text using trained ML model

        Args:
            text: Raw text to classify

        Returns:
            Classification result with label, confidence, and scores
        """
        if not self.is_available():
            return ClassificationResult(
                label="ML_UNAVAILABLE",
                confidence=0.0,
                scores={"ML_UNAVAILABLE": 0}
            )

        if not self.is_trained():
            return ClassificationResult(
                label="ML_UNTRAINED", 
                confidence=0.0,
                scores={"ML_UNTRAINED": 0}
            )

        try:
            import numpy as np

            # Vectorize input text  
            X = self.vectorizer.transform([text])

            # Get prediction probabilities
            probabilities = self.model.predict_proba(X)[0]

            # Get predicted class
            predicted_class_idx = np.argmax(probabilities)
            predicted_label = self.label_encoder.inverse_transform([predicted_class_idx])[0]

            # Calculate confidence (max probability)
            confidence = float(np.max(probabilities))

            # Create scores dictionary with all classes
            scores = {}
            for i, prob in enumerate(probabilities):
                label = self.label_encoder.inverse_transform([i])[0]
                scores[label] = int(prob * 100)  # Convert to integer score

            return ClassificationResult(
                label=predicted_label,
                confidence=confidence,
                scores=scores
            )

        except Exception as e:
            return ClassificationResult(
                label="ML_ERROR",
                confidence=0.0,
                scores={"ML_ERROR": 0}
            )

    def get_status(self) -> str:
        """Get current status of ML classifier"""
        if not self.available:
            return "unavailable"
        elif not os.getenv("ENABLE_ML", "0") == "1":
            return "deferred"
        elif not self.trained:
            return "available"
        else:
            return "active"
