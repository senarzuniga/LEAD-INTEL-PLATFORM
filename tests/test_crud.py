import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session
from database.crud import create_item, get_item


def test_create_item_success():
    # Mock the database session
    db = Mock(spec=Session)
    
    # Mock item data
    item_data = {'name': 'Test Item', 'value': 100}
    
    # Call the create_item function
    result = create_item(db, item_data)
    
    # Assertions
    assert result is not None
    assert result.name == 'Test Item'
    assert result.value == 100


def test_get_item_success():
    # Mock the database session
    db = Mock(spec=Session)
    
    # Mock item ID
    item_id = 1
    
    # Mock the return value of get_item
    db.query().filter_by().first.return_value = Mock(name='Test Item', value=100)
    
    # Call the get_item function
    result = get_item(db, item_id)
    
    # Assertions
    assert result is not None
    assert result.name == 'Test Item'
    assert result.value == 100
