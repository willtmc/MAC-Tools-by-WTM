"""
Tests for CSV processing functionality
"""
import pytest
import pandas as pd
from io import StringIO
from tools.neighbor_letters.csv_processor import process_csv_data

def test_valid_csv_processing(sample_csv_data):
    """Test processing of valid CSV data."""
    # Convert string data to file-like object
    csv_file = StringIO(sample_csv_data)
    
    # Process the CSV data
    df = process_csv_data(csv_file)
    
    # Check that all required columns are present
    required_columns = ['Property Address', 'Owner Name', 'Owner Address', 'City', 'State', 'Zip']
    for col in required_columns:
        assert col in df.columns
    
    # Check that we have the expected number of rows
    assert len(df) == 2
    
    # Check specific data values
    assert df.iloc[0]['Owner Name'] == 'John Doe'
    assert df.iloc[1]['City'] == 'Springfield'

def test_missing_columns():
    """Test that missing required columns raise an error."""
    # CSV data missing required columns
    invalid_csv = """Address,Name,City,State
123 Main St,John Doe,Springfield,IL"""
    
    csv_file = StringIO(invalid_csv)
    
    # Should raise ValueError due to missing required columns
    with pytest.raises(ValueError) as exc_info:
        process_csv_data(csv_file)
    assert "Missing required columns" in str(exc_info.value)

def test_empty_csv():
    """Test handling of empty CSV file."""
    empty_csv = StringIO("")
    
    with pytest.raises(ValueError) as exc_info:
        process_csv_data(empty_csv)
    assert "Empty CSV file" in str(exc_info.value)

def test_duplicate_addresses():
    """Test handling of duplicate property addresses."""
    duplicate_csv = """Property Address,Owner Name,Owner Address,City,State,Zip
123 Main St,John Doe,456 Oak Rd,Springfield,IL,62701
123 Main St,Jane Smith,789 Pine Ave,Springfield,IL,62702"""
    
    csv_file = StringIO(duplicate_csv)
    df = process_csv_data(csv_file)
    
    # Check that duplicates are removed and we keep the first occurrence
    assert len(df) == 1
    assert df.iloc[0]['Owner Name'] == 'John Doe'
