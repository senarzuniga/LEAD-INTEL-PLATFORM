import pytest
from unittest.mock import Mock
from research.company_researcher import research_company


def test_research_company_success():
    # Mock the progress callback
    progress_callback = Mock()
    
    # Run the research
    result = research_company('Test Company', progress_callback=progress_callback)
    
    # Assertions
    assert 'company' in result
    assert 'subsidiaries' in result
    assert 'plants' in result
    assert 'contacts' in result
    assert 'raw_news' in result
    
    # Check if progress callback was called
    progress_callback.assert_called()
