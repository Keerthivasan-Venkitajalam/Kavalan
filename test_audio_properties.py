"""
Property-based tests for Audio Processing
Tests Properties 5 and 6 related to audio processing
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from modules.audio_processor import AudioProcessor, AudioResult

class TestAudioProperties:
    """Property-based tests for audio processing"""
    
    def setup_method(self):
        """Set up audio processor for each test"""
        # Use test keywords for consistent testing
        test_keywords = {
            "authority": ["CBI", "NCB", "Police", "Court", "RBI"],
            "coercion": ["Do not disconnect", "Stay on call", "Keep camera on"],
            "financial": ["Transfer money", "Verification account", "Asset verification"],
            "crime": ["Money laundering", "Arrest warrant", "Drugs"],
            "urgency": ["Immediate action", "Time sensitive", "Act now"]
        }
        
        self.processor = AudioProcessor(keywords_dict=test_keywords)
    
    def test_keyword_matching_completeness(self):
        """
        **Feature: kavalan-lite, Property 5: Keyword Matching Completeness**
        
        For any text containing keywords from the scam dictionary, the Audio_Processor
        should detect and return all matching keywords in the correct categories.
        """
        # Test cases with known keywords
        test_cases = [
            {
                "text": "This is CBI calling about money laundering case",
                "expected_categories": ["authority", "crime"],
                "expected_keywords": {"authority": ["CBI"], "crime": ["Money laundering"]}
            },
            {
                "text": "Do not disconnect the call, transfer money immediately",
                "expected_categories": ["coercion", "financial"],
                "expected_keywords": {"coercion": ["Do not disconnect"], "financial": ["Transfer money"]}
            },
            {
                "text": "Police investigation requires asset verification",
                "expected_categories": ["authority", "financial"],
                "expected_keywords": {"authority": ["Police"], "financial": ["Asset verification"]}
            },
            {
                "text": "NCB Court RBI arrest warrant drugs",
                "expected_categories": ["authority", "crime"],
                "expected_keywords": {"authority": ["NCB", "Court", "RBI"], "crime": ["Arrest warrant", "Drugs"]}
            }
        ]
        
        for i, case in enumerate(test_cases):
            matches = self.processor.match_keywords(case["text"])
            
            # Property 5: All expected categories should be detected
            for expected_category in case["expected_categories"]:
                assert expected_category in matches, \
                    f"Case {i}: Category '{expected_category}' not detected in '{case['text']}'"
            
            # Property 5: All expected keywords should be detected
            for category, expected_keywords in case["expected_keywords"].items():
                assert category in matches, \
                    f"Case {i}: Category '{category}' missing from matches"
                
                for keyword in expected_keywords:
                    assert keyword in matches[category], \
                        f"Case {i}: Keyword '{keyword}' not found in category '{category}'"
    
    @given(
        text_with_keywords=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=10)
    def test_keyword_matching_robustness(self, text_with_keywords):
        """
        **Feature: kavalan-lite, Property 5: Keyword Matching Completeness (Robustness)**
        
        Keyword matching should handle various text inputs without errors.
        """
        # Test that matching doesn't crash on arbitrary text
        try:
            matches = self.processor.match_keywords(text_with_keywords)
            
            # Property: Should return a dictionary
            assert isinstance(matches, dict), f"Should return dict, got {type(matches)}"
            
            # Property: All values should be lists
            for category, keywords in matches.items():
                assert isinstance(keywords, list), \
                    f"Category '{category}' should have list value, got {type(keywords)}"
                
                # Property: All keywords should be strings
                for keyword in keywords:
                    assert isinstance(keyword, str), \
                        f"Keyword should be string, got {type(keyword)}"
                        
        except Exception as e:
            pytest.fail(f"Keyword matching failed on text: '{text_with_keywords[:50]}...': {e}")
    
    def test_multi_category_score_scaling(self):
        """
        **Feature: kavalan-lite, Property 6: Multi-Category Score Scaling**
        
        For any text with keywords from N categories, the audio threat score
        should be proportionally higher than text with keywords from fewer categories.
        """
        # Test cases with increasing category counts
        test_cases = [
            {
                "text": "Hello world",  # 0 categories
                "expected_categories": 0
            },
            {
                "text": "CBI is calling",  # 1 category (authority)
                "expected_categories": 1
            },
            {
                "text": "CBI calling about money laundering",  # 2 categories (authority + crime)
                "expected_categories": 2
            },
            {
                "text": "CBI calling about money laundering, do not disconnect",  # 3 categories
                "expected_categories": 3
            },
            {
                "text": "CBI calling about money laundering, do not disconnect, transfer money immediately",  # 4 categories
                "expected_categories": 4
            }
        ]
        
        scores = []
        for case in test_cases:
            matches = self.processor.match_keywords(case["text"])
            score = self.processor.calculate_score(matches)
            scores.append(score)
            
            # Verify expected category count
            actual_categories = len(matches)
            assert actual_categories == case["expected_categories"], \
                f"Expected {case['expected_categories']} categories, got {actual_categories} for '{case['text']}'"
        
        # Property 6: Scores should generally increase with more categories
        for i in range(1, len(scores)):
            if scores[i-1] > 0:  # Only compare if previous score was non-zero
                assert scores[i] >= scores[i-1], \
                    f"Score should increase with more categories: {scores[i]} >= {scores[i-1]}"
    
    def test_score_range_property(self):
        """
        **Feature: kavalan-lite, Property 6: Multi-Category Score Scaling (Range)**
        
        All calculated scores should be in the valid range [0, 10].
        """
        test_texts = [
            "",  # Empty text
            "Normal conversation without keywords",
            "CBI",  # Single keyword
            "CBI NCB Police Court RBI money laundering drugs arrest warrant do not disconnect transfer money",  # Many keywords
            "CBI " * 100,  # Repeated keywords
        ]
        
        for text in test_texts:
            matches = self.processor.match_keywords(text)
            score = self.processor.calculate_score(matches)
            
            # Property: Score should be in valid range
            assert 0.0 <= score <= 10.0, \
                f"Score {score} out of range [0, 10] for text: '{text[:50]}...'"
    
    def test_threat_level_consistency_property(self):
        """
        **Feature: kavalan-lite, Property 6: Multi-Category Score Scaling (Threat Levels)**
        
        Threat levels should be consistent with scores.
        """
        # Test score ranges and expected threat levels
        test_scores = [0.0, 2.0, 4.0, 6.5, 8.5, 10.0]
        expected_levels = ["low", "low", "medium", "high", "critical", "critical"]
        
        for score, expected_level in zip(test_scores, expected_levels):
            actual_level = self.processor.determine_threat_level(score)
            assert actual_level == expected_level, \
                f"Score {score} should have threat level '{expected_level}', got '{actual_level}'"
    
    def test_case_insensitive_matching_property(self):
        """
        **Feature: kavalan-lite, Property 5: Keyword Matching Completeness (Case Insensitive)**
        
        Keyword matching should be case-insensitive.
        """
        test_cases = [
            "CBI calling",
            "cbi calling", 
            "Cbi Calling",
            "CBI CALLING",
            "cBi CaLlInG"
        ]
        
        # All should produce the same matches
        expected_matches = None
        for text in test_cases:
            matches = self.processor.match_keywords(text)
            
            if expected_matches is None:
                expected_matches = matches
            else:
                # Property: Case variations should produce same matches
                assert matches == expected_matches, \
                    f"Case insensitive matching failed for '{text}'"
    
    def test_buffer_management_property(self):
        """
        **Feature: kavalan-lite, Property 5: Keyword Matching Completeness (Buffer)**
        
        Transcript buffer should be managed properly and not grow indefinitely.
        """
        # Create mock audio data
        mock_audio = np.zeros(1000, dtype=np.float32)
        
        # Process multiple chunks to fill buffer
        long_text = "CBI calling about money laundering " * 50  # Long text
        
        # Simulate processing by directly adding to buffer
        self.processor.transcript_buffer = long_text
        
        # Process audio (will add to buffer)
        result = self.processor.process_audio(mock_audio)
        
        # Property: Buffer should be limited in size
        assert len(self.processor.transcript_buffer) <= 1000, \
            f"Buffer too large: {len(self.processor.transcript_buffer)} characters"
        
        # Property: Should still detect keywords in buffer
        assert len(result.detected_keywords) > 0, \
            "Should detect keywords even with buffer management"
    
    def test_reset_buffer_property(self):
        """
        **Feature: kavalan-lite, Property 5: Keyword Matching Completeness (Reset)**
        
        Buffer reset should clear all accumulated transcript data.
        """
        # Add some data to buffer
        self.processor.transcript_buffer = "CBI calling about money laundering"
        
        # Verify buffer has content
        assert len(self.processor.transcript_buffer) > 0, "Buffer should have content"
        
        # Reset buffer
        self.processor.reset_buffer()
        
        # Property: Buffer should be empty after reset
        assert self.processor.transcript_buffer == "", \
            f"Buffer should be empty after reset, got: '{self.processor.transcript_buffer}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])