"""
Tests for CSV processing functionality
"""
import pytest
import pandas as pd
from io import StringIO
from csv_processor import CSVProcessor

def test_valid_csv_processing(sample_csv_data):
    """Test processing of valid CSV data."""
    # Convert string data to file-like object
    csv_file = StringIO(sample_csv_data)
    
    # Create CSV processor and read data
    processor = CSVProcessor()
    df = pd.read_csv(csv_file)
    
    # Process the CSV data
    result_df, stats = processor.process_csv_data(df)
    
    # Check that all required columns are present in result
    required_columns = ['Name', 'Address', 'City', 'State', 'Zip']
    for col in required_columns:
        assert col in result_df.columns
    
    # Check that we have the expected number of rows
    assert len(result_df) == 2
    
    # Check specific data values
    assert result_df.iloc[0]['Name'] == 'John Doe'
    assert result_df.iloc[1]['City'] == 'Springfield'
    
    # Check stats
    assert stats['total_rows'] == 2
    assert stats['processed_rows'] == 2
    assert stats['format_detected'] == 'manual'

def test_missing_columns():
    """Test that missing required columns raise an error."""
    # CSV data missing required columns
    invalid_csv = """Address,Name,City,State
123 Main St,John Doe,Springfield,IL"""
    
    csv_file = StringIO(invalid_csv)
    processor = CSVProcessor()
    df = pd.read_csv(csv_file)
    
    # Should raise ValueError with format not recognized message
    with pytest.raises(ValueError) as exc_info:
        processor.process_csv_data(df)
    assert "CSV format not recognized" in str(exc_info.value)
    assert "Missing columns for manual format: ['Zip']" in str(exc_info.value)

def test_empty_csv():
    """Test handling of empty CSV file."""
    empty_csv = StringIO("")
    processor = CSVProcessor()
    
    # pandas.errors.EmptyDataError is raised when reading an empty CSV
    with pytest.raises(pd.errors.EmptyDataError):
        df = pd.read_csv(empty_csv)
        processor.process_csv_data(df)

def test_duplicate_addresses():
    """Test handling of duplicate property addresses."""
    duplicate_csv = """Name,Address,City,State,Zip
John Doe,123 Main St,Springfield,IL,62701
Jane Smith,123 Main St,Springfield,IL,62701"""  # Exact same address
    
    csv_file = StringIO(duplicate_csv)
    processor = CSVProcessor()
    df = pd.read_csv(csv_file)
    result_df, stats = processor.process_csv_data(df)
    
    # Check that duplicates are handled
    assert stats['duplicate_rows'] == 1  # Second row should be counted as duplicate
    assert len(result_df) == 1  # Only first row should be kept
    assert result_df.iloc[0]['Name'] == 'John Doe'  # First row should be kept
