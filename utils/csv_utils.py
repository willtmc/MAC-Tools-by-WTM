"""
Utility functions for handling CSV files with flexible encoding and dialect detection.
"""
import io
import csv
import logging
import pandas as pd
from typing import Optional, Union, BinaryIO, TextIO
from pathlib import Path

logger = logging.getLogger(__name__)

class CSVReadError(Exception):
    """Base exception for CSV reading errors"""
    pass

def detect_encoding(content: bytes) -> str:
    """
    Detect the encoding of a CSV file content
    
    Args:
        content: Raw bytes content of the CSV file
        
    Returns:
        str: Detected encoding (utf-8-sig, utf-8, or latin-1)
        
    Raises:
        CSVReadError: If no valid encoding is found
    """
    encodings = ['utf-8-sig', 'utf-8', 'latin-1']
    
    for encoding in encodings:
        try:
            content.decode(encoding)
            logger.debug(f"Successfully decoded content with {encoding} encoding")
            return encoding
        except UnicodeDecodeError:
            logger.debug(f"Failed to decode with {encoding} encoding")
            continue
    
    raise CSVReadError("Could not decode file content with any supported encoding")

def detect_dialect(content: bytes, encoding: str) -> csv.Dialect:
    """
    Detect the dialect of a CSV file
    
    Args:
        content: Raw bytes content of the CSV file
        encoding: Encoding to use for reading the content
        
    Returns:
        csv.Dialect: Detected CSV dialect
        
    Raises:
        CSVReadError: If dialect detection fails
    """
    try:
        # Read a sample of the file to detect dialect
        sample = content.decode(encoding).split('\n')[:5]
        if not sample:
            raise CSVReadError("Empty file")
            
        dialect = csv.Sniffer().sniff('\n'.join(sample))
        logger.debug(f"Detected CSV dialect: delimiter='{dialect.delimiter}'")
        return dialect
        
    except Exception as e:
        logger.error(f"Error detecting CSV dialect: {str(e)}")
        raise CSVReadError(f"Failed to detect CSV dialect: {str(e)}")

def read_csv_flexibly(file: Union[str, Path, bytes, BinaryIO, TextIO],
                     encoding: Optional[str] = None,
                     **kwargs) -> pd.DataFrame:
    """
    Flexibly read a CSV file with automatic encoding and dialect detection
    
    Args:
        file: File path, bytes content, or file-like object containing CSV data
        encoding: Optional encoding to use (if not provided, will be auto-detected)
        **kwargs: Additional arguments to pass to pd.read_csv
        
    Returns:
        pd.DataFrame: Parsed CSV data
        
    Raises:
        CSVReadError: If file cannot be read or parsed
        pd.errors.EmptyDataError: If file is empty
    """
    try:
        # Convert file to bytes if needed
        if isinstance(file, (str, Path)):
            with open(file, 'rb') as f:
                content = f.read()
        elif isinstance(file, bytes):
            content = file
        elif hasattr(file, 'read'):
            # Handle file-like objects
            if hasattr(file, 'buffer'):
                # TextIOWrapper case
                content = file.buffer.read()
            else:
                # Binary file case
                content = file.read()
            
            # Reset file pointer if possible
            if hasattr(file, 'seek'):
                try:
                    file.seek(0)
                except (OSError, io.UnsupportedOperation):
                    pass
        else:
            raise CSVReadError(f"Unsupported file type: {type(file)}")
            
        # Detect encoding if not provided
        if not encoding:
            encoding = detect_encoding(content)
            
        # Detect dialect
        dialect = detect_dialect(content, encoding)
        
        # Read CSV with pandas
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                encoding=encoding,
                sep=dialect.delimiter,
                quotechar=dialect.quotechar,
                escapechar=dialect.escapechar,
                **kwargs
            )
            
            logger.info(f"Successfully read CSV with {len(df)} rows using {encoding} encoding")
            return df
            
        except pd.errors.EmptyDataError:
            logger.warning("Empty CSV file")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV with pandas: {str(e)}")
            raise CSVReadError(f"Failed to parse CSV: {str(e)}")
            
    except Exception as e:
        if not isinstance(e, (CSVReadError, pd.errors.EmptyDataError)):
            logger.error(f"Unexpected error reading CSV: {str(e)}")
            raise CSVReadError(f"Unexpected error: {str(e)}")
        raise
