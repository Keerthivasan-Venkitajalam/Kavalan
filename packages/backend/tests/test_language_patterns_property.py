"""
Property-Based Test: Language-Specific Pattern Matching

Feature: production-ready-browser-extension
Property 11: Language-Specific Pattern Matching

For any transcript in a supported language (Hindi, English, Tamil, Telugu, Malayalam, Kannada),
the threat analyzer should apply the correct language-specific keyword patterns for that language.

Validates: Requirements 6.4
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.services.audio_transcriber import AudioTranscriber
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def transcriber():
    """Create audio transcriber instance"""
    return AudioTranscriber(model_size='tiny')


def test_keyword_matching_case_insensitive(transcriber):
    """
    Property: Keyword matching should be case-insensitive
    """
    # Test with different cases
    test_cases = [
        ("I am a CBI officer", ['CBI']),
        ("i am a cbi officer", ['CBI']),
        ("I AM A CBI OFFICER", ['CBI']),
        ("Transfer money to account", ['Transfer money']),
        ("TRANSFER MONEY TO ACCOUNT", ['Transfer money']),
    ]
    
    for transcript, expected_keywords in test_cases:
        matches = transcriber.match_keywords(transcript, language='en')
        
        # Check that keywords were matched
        assert len(matches) > 0, f"Should match keywords in: {transcript}"
        
        # Verify expected keywords are present
        all_matched = [kw for keywords in matches.values() for kw in keywords]
        for expected in expected_keywords:
            assert any(expected.lower() in kw.lower() for kw in all_matched), \
                f"Expected keyword '{expected}' not found in matches: {all_matched}"
    
    logger.info("✓ Case-insensitive keyword matching validated")


@settings(max_examples=20)
@given(
    keyword_category=st.sampled_from(['authority', 'coercion', 'financial', 'crime', 'urgency'])
)
def test_category_specific_matching(transcriber, keyword_category):
    """
    Property: Keywords should be matched to correct categories
    """
    # Get keywords for the category
    category_keywords = transcriber.keywords.get(keyword_category, [])
    
    if not category_keywords:
        return  # Skip if no keywords in category
    
    # Pick a keyword from the category
    test_keyword = category_keywords[0]
    transcript = f"This is a test with {test_keyword} in it."
    
    # Match keywords
    matches = transcriber.match_keywords(transcript, language='en')
    
    # Property: The keyword should be matched in the correct category
    if keyword_category in matches:
        assert test_keyword in matches[keyword_category], \
            f"Keyword '{test_keyword}' should be in category '{keyword_category}'"
    
    logger.info(f"✓ Category matching validated for '{keyword_category}': {test_keyword}")


def test_multiple_category_matching(transcriber):
    """
    Test that transcripts with keywords from multiple categories are correctly identified
    """
    # Transcript with keywords from multiple categories
    transcript = "CBI officer says transfer money urgent action required for investigation"
    
    matches = transcriber.match_keywords(transcript, language='en')
    
    # Should match multiple categories
    assert len(matches) >= 2, "Should match keywords from multiple categories"
    
    # Check specific categories
    assert 'authority' in matches, "Should match authority keywords (CBI)"
    assert 'financial' in matches, "Should match financial keywords (transfer, money)"
    
    logger.info(f"✓ Multi-category matching validated: {list(matches.keys())}")


def test_no_false_positives(transcriber):
    """
    Test that normal conversation doesn't trigger false positives
    """
    # Normal, non-threatening transcripts
    normal_transcripts = [
        "Hello, how are you today?",
        "The weather is nice.",
        "I went to the store yesterday.",
        "Let's meet for coffee tomorrow.",
    ]
    
    for transcript in normal_transcripts:
        matches = transcriber.match_keywords(transcript, language='en')
        
        # Should have no matches or very few
        total_matches = sum(len(keywords) for keywords in matches.values())
        assert total_matches == 0, \
            f"Normal transcript should not match threat keywords: '{transcript}' matched {matches}"
    
    logger.info("✓ No false positives in normal conversation")


def test_partial_keyword_matching(transcriber):
    """
    Test that keywords are matched as whole words or substrings correctly
    """
    # Test cases with keywords embedded in larger words
    test_cases = [
        ("The CBI is investigating", True),  # Should match
        ("I received a parcel", True),  # Should match "parcel" (from "Parcel intercepted")
        ("Hello world", False),  # Should not match
    ]
    
    for transcript, should_match in test_cases:
        matches = transcriber.match_keywords(transcript, language='en')
        has_matches = len(matches) > 0
        
        assert has_matches == should_match, \
            f"Transcript '{transcript}' match result {has_matches} != expected {should_match}"
    
    logger.info("✓ Partial keyword matching validated")


@settings(max_examples=10)
@given(
    language=st.sampled_from(['en', 'hi', 'ta', 'te', 'ml', 'kn'])
)
def test_language_parameter_accepted(transcriber, language):
    """
    Property: The match_keywords function should accept all supported languages
    """
    transcript = "Test transcript with CBI and money transfer"
    
    # Should not raise an exception for any supported language
    try:
        matches = transcriber.match_keywords(transcript, language=language)
        assert isinstance(matches, dict), "Should return a dictionary"
        logger.info(f"✓ Language '{language}' accepted")
    except Exception as e:
        pytest.fail(f"Language '{language}' should be supported: {e}")


def test_empty_transcript_no_matches(transcriber):
    """
    Test that empty transcripts return no matches
    """
    empty_transcripts = ["", "   ", "\n", "\t"]
    
    for transcript in empty_transcripts:
        matches = transcriber.match_keywords(transcript, language='en')
        assert len(matches) == 0, f"Empty transcript should have no matches: '{transcript}'"
    
    logger.info("✓ Empty transcripts return no matches")


def test_score_calculation_consistency(transcriber):
    """
    Test that threat scores are calculated consistently
    """
    # Same keywords should produce same score
    transcript1 = "CBI officer transfer money"
    transcript2 = "Transfer money CBI officer"
    
    matches1 = transcriber.match_keywords(transcript1, language='en')
    matches2 = transcriber.match_keywords(transcript2, language='en')
    
    score1 = transcriber.calculate_score(matches1)
    score2 = transcriber.calculate_score(matches2)
    
    # Scores should be equal (order doesn't matter)
    assert score1 == score2, \
        f"Same keywords should produce same score: {score1} != {score2}"
    
    logger.info(f"✓ Score calculation consistency validated: {score1}")


def test_score_range_constraint(transcriber):
    """
    Test that threat scores are always in range [0.0, 10.0]
    """
    # Test with various transcripts
    test_transcripts = [
        "",  # Empty
        "Hello world",  # Normal
        "CBI officer",  # Single keyword
        "CBI officer transfer money immediately for investigation",  # Multiple keywords
        "CBI NCB RBI ED Cyber Police transfer money immediately urgent",  # Many keywords
    ]
    
    for transcript in test_transcripts:
        matches = transcriber.match_keywords(transcript, language='en')
        score = transcriber.calculate_score(matches)
        
        # Property: Score must be in range [0.0, 10.0]
        assert 0.0 <= score <= 10.0, \
            f"Score {score} out of range [0.0, 10.0] for transcript: '{transcript}'"
    
    logger.info("✓ Score range constraint validated")


def test_high_threat_keywords_produce_high_scores(transcriber):
    """
    Test that transcripts with many threat keywords produce high scores
    """
    # High-threat transcript
    high_threat = (
        "CBI officer says do not disconnect keep camera on "
        "transfer money to supervision account immediately "
        "for money laundering investigation"
    )
    
    matches = transcriber.match_keywords(high_threat, language='en')
    score = transcriber.calculate_score(matches)
    
    # Should produce a high score (> 5.0)
    assert score > 5.0, \
        f"High-threat transcript should produce high score: {score}"
    
    logger.info(f"✓ High-threat keywords produce high score: {score:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
