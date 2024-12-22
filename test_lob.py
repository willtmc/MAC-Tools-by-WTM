import os
from dotenv import load_dotenv
import lob

def test_lob_connection():
    # Load environment variables
    load_dotenv()
    
    # Initialize Lob client with test key
    lob.api_key = os.getenv('LOB_TEST_API_KEY')
    
    try:
        # Try to create a test US verification
        verification = lob.USVerification.create(
            primary_line='185 Berry St',
            city='San Francisco',
            state='CA',
            zip_code='94107'
        )
        print("✅ Successfully connected to Lob API!")
        print(f"Verified address: {verification}")
        return True
    except Exception as e:
        print("❌ Failed to connect to Lob API")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_lob_connection()
