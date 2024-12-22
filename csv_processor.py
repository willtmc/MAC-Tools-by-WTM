import pandas as pd
import logging
import traceback
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)

class CSVProcessor:
    """Process CSV files for neighbor letters"""
    
    # Required columns for manually prepared CSV
    MANUAL_REQUIRED_COLUMNS = {
        'Name': str,
        'Address': str,
        'City': str,
        'State': str,
        'Zip': str
    }
    
    # Required columns for CRS format
    CRS_REQUIRED_COLUMNS = {
        'Owner 1': str,
        'Owner Address': str,
        'Owner City': str,
        'Owner State': str,
        'Owner Zip': str
    }

    def __init__(self):
        """Initialize CSV processor"""
        self.stats = {
            'total_rows': 0,
            'processed_rows': 0,
            'skipped_rows': 0,
            'format_detected': None,
            'cemetery_records_skipped': 0,
            'duplicate_rows': 0
        }

    def detect_csv_format(self, df: pd.DataFrame) -> str:
        """
        Detect if the CSV is in CRS or manual format
        
        Args:
            df: Pandas DataFrame of the CSV
            
        Returns:
            str: 'crs' or 'manual'
            
        Raises:
            ValueError: If CSV format cannot be determined
        """
        try:
            # Clean up column names - remove any trailing whitespace
            df.columns = df.columns.str.strip()
            columns = set(df.columns)
            logger.info(f"Detecting CSV format. Available columns: {sorted(list(columns))}")
            
            # Check for CRS format - we only need Owner 1 and the address fields
            crs_fields = {'Owner 1', 'Owner Address', 'Owner City', 'Owner State', 'Owner Zip'}
            if all(col in columns for col in crs_fields):
                logger.info("CRS format detected")
                return 'crs'
                
            # Check for manual format
            if all(col in columns for col in self.MANUAL_REQUIRED_COLUMNS.keys()):
                logger.info("Manual format detected")
                return 'manual'
                
            # If neither format matches, show helpful error
            missing_crs = [col for col in crs_fields if col not in columns]
            missing_manual = [col for col in self.MANUAL_REQUIRED_COLUMNS.keys() if col not in columns]
            
            error_msg = (
                "CSV format not recognized. Your CSV must have either:\n"
                "1. CRS format with columns: " + ", ".join(crs_fields) + "\n"
                "2. Manual format with columns: " + ", ".join(self.MANUAL_REQUIRED_COLUMNS.keys()) + "\n\n"
                f"Missing columns for CRS format: {missing_crs}\n"
                f"Missing columns for manual format: {missing_manual}\n\n"
                f"Available columns in your CSV: {sorted(list(columns))}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        except Exception as e:
            logger.error(f"Error detecting CSV format: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def truncate_name(self, name: str) -> str:
        """
        Truncate name to 40 characters and remove any partial words
        
        Args:
            name: Full name string
            
        Returns:
            str: Truncated name if necessary
        """
        try:
            if not name or pd.isna(name) or len(str(name).strip()) == 0:
                return ""
                
            # Convert to string and clean
            name = str(name).strip()
            
            # Return as is if under limit
            if len(name) <= 40:
                return name
                
            # Truncate to 40 characters
            truncated = name[:40]
            
            # Find the last complete word
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]
                
            return truncated.strip()
            
        except Exception as e:
            logger.error(f"Error truncating name '{name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return str(name)[:40].strip()  # Fallback to simple truncation

    def clean_address_field(self, value: str) -> str:
        """Clean and validate an address field"""
        if pd.isna(value):
            return ""
        return str(value).strip()

    def process_crs_row(self, row: pd.Series) -> dict:
        """
        Process a row from CRS format CSV
        
        Args:
            row: Pandas Series containing row data
            
        Returns:
            dict: Processed address data
        """
        try:
            # Log row data for debugging
            logger.debug(f"Processing CRS row: {row.to_dict()}")
            
            # Get owner name and truncate if needed
            name = row.get('Owner 1', '')
            if pd.isna(name) or not str(name).strip():
                logger.warning(f"Empty name in row: {row.to_dict()}")
                raise ValueError("Name is required")
                
            name = self.truncate_name(name)
            if not name:
                raise ValueError("Name is required")
            
            # Get and clean address fields
            address = self.clean_address_field(row.get('Owner Address', ''))
            city = self.clean_address_field(row.get('Owner City', ''))
            state = self.clean_address_field(row.get('Owner State', ''))
            zip_code = self.clean_address_field(row.get('Owner Zip', ''))
            
            # Validate required fields
            missing = []
            if not address: missing.append('Owner Address')
            if not city: missing.append('Owner City')
            if not state: missing.append('Owner State')
            if not zip_code: missing.append('Owner Zip')
            
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
            processed = {
                'Name': name,
                'Address': address,
                'City': city,
                'State': state,
                'Zip': zip_code
            }
            
            logger.debug(f"Processed CRS row: {processed}")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing CRS row: {str(e)}")
            logger.error(f"Row data: {row.to_dict()}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error processing row: {str(e)}")

    def process_manual_row(self, row: pd.Series) -> dict:
        """
        Process a row from manual format CSV
        
        Args:
            row: Pandas Series containing row data
            
        Returns:
            dict: Processed address data
        """
        try:
            # Log row data for debugging
            logger.debug(f"Processing manual row: {row.to_dict()}")
            
            # Get name and truncate if needed
            name = row.get('Name', '')
            if pd.isna(name) or not str(name).strip():
                logger.warning(f"Empty name in row: {row.to_dict()}")
                raise ValueError("Name is required")
                
            name = self.truncate_name(name)
            if not name:
                raise ValueError("Name is required")
            
            # Get and clean address fields
            address = self.clean_address_field(row.get('Address', ''))
            city = self.clean_address_field(row.get('City', ''))
            state = self.clean_address_field(row.get('State', ''))
            zip_code = self.clean_address_field(row.get('Zip', ''))
            
            # Validate required fields
            missing = []
            if not address: missing.append('Address')
            if not city: missing.append('City')
            if not state: missing.append('State')
            if not zip_code: missing.append('Zip')
            
            if missing:
                raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
            processed = {
                'Name': name,
                'Address': address,
                'City': city,
                'State': state,
                'Zip': zip_code
            }
            
            logger.debug(f"Processed manual row: {processed}")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing manual row: {str(e)}")
            logger.error(f"Row data: {row.to_dict()}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error processing row: {str(e)}")

    def process_csv_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        Process CSV data and return processed DataFrame and stats
        
        Args:
            df: Pandas DataFrame of the CSV
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Processed DataFrame and statistics
            
        Raises:
            ValueError: If CSV format is invalid
        """
        try:
            # Clean up column names
            df.columns = df.columns.str.strip()
            logger.info(f"Processing CSV with shape: {df.shape}")
            logger.info(f"Columns after cleanup: {list(df.columns)}")
            
            # Fill NaN values with empty strings
            df = df.fillna('')
            
            self.stats['total_rows'] = len(df)
            
            # Detect format
            format_type = self.detect_csv_format(df)
            self.stats['format_detected'] = format_type
            logger.info(f"Format detected: {format_type}")
            
            # Process rows based on format
            processed_data = []
            seen_addresses = set()  # Track unique addresses
            
            for idx, row in df.iterrows():
                try:
                    # Skip cemetery records
                    name = row['Owner 1'] if format_type == 'crs' else row['Name']
                    name = str(name).lower()
                    if not name or any(term in name for term in ['cemetery', 'cemetary', 'memorial', 'church']):
                        self.stats['cemetery_records_skipped'] = self.stats.get('cemetery_records_skipped', 0) + 1
                        logger.info(f"Skipped cemetery/church record: {name}")
                        continue
                    
                    # Process row based on format
                    if format_type == 'crs':
                        processed_row = self.process_crs_row(row)
                    else:
                        processed_row = self.process_manual_row(row)
                    
                    # Check for duplicates
                    address_key = (
                        processed_row['Address'].lower(),
                        processed_row['City'].lower(),
                        processed_row['State'].lower(),
                        processed_row['Zip']
                    )
                    
                    if address_key in seen_addresses:
                        self.stats['duplicate_rows'] = self.stats.get('duplicate_rows', 0) + 1
                        logger.info(f"Skipped duplicate address: {processed_row['Address']}")
                        continue
                        
                    seen_addresses.add(address_key)
                    processed_data.append(processed_row)
                    self.stats['processed_rows'] += 1
                    
                except ValueError as e:
                    logger.warning(f"Skipping invalid row {idx}: {str(e)}")
                    self.stats['skipped_rows'] += 1
                    continue
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {str(e)}")
                    logger.error(f"Row data: {row.to_dict()}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    self.stats['skipped_rows'] += 1
                    continue
            
            if not processed_data:
                raise ValueError("No valid rows found in CSV file")
                
            # Create DataFrame from processed data
            result_df = pd.DataFrame(processed_data)
            
            # Remove any remaining duplicates
            result_df = result_df.drop_duplicates(subset=['Address', 'City', 'State', 'Zip'])
            
            logger.info(f"Finished processing CSV. Stats: {self.stats}")
            return result_df, self.stats
            
        except Exception as e:
            logger.error(f"Error processing CSV data: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
