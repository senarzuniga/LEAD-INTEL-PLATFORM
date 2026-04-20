import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session
from pipeline.processor import run_pipeline


def test_run_pipeline_success():
    # Mock the database session
    db = Mock(spec=Session)
    
    # Mock the progress callback
    progress_callback = Mock()
    
    # Run the pipeline
    result = run_pipeline('Test Company', db, progress_callback=progress_callback)
    
    # Assertions
    assert 'company_id' in result
    assert 'name' in result
    assert 'score' in result
    assert 'tier' in result
    assert 'plants_found' in result
    assert 'contacts_found' in result
    assert 'subsidiaries_found' in result
    
    # Check if progress callback was called
    progress_callback.assert_called()
