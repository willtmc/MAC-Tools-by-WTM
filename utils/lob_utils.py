"""
Minimal Lob utility module
"""
import os
import lob
from dataclasses import dataclass
from typing import Dict, List, Any

class LobAPIError(Exception):
    pass

@dataclass
class Address:
    name: str
    address_line1: str
    address_city: str
    address_state: str
    address_zip: str

class LobClient:
    def __init__(self, use_test_key: bool = False):
        # Use test key or live key
        api_key = os.getenv('LOB_TEST_API_KEY') if use_test_key else os.getenv('LOB_API_KEY')
        if not api_key:
            raise LobAPIError("Missing Lob API Key. Set LOB_API_KEY or LOB_TEST_API_KEY.")
        lob.api_key = api_key

    def verify_address(self, address: Address) -> Dict[str, Any]:
        try:
            result = lob.USVerification.create(
                primary_line=address.address_line1,
                city=address.address_city,
                state=address.address_state,
                zip_code=address.address_zip
            )
            return {
                "valid": result.deliverability == "deliverable",
                "deliverability": result.deliverability,
                "details": result
            }
        except Exception as e:
            raise LobAPIError(f"Address verification failed: {str(e)}")

    def send_letter(self, address: Address, html_content: str) -> Dict[str, Any]:
        """
        Sends a single letter.
        """
        try:
            letter = lob.Letter.create(
                to_address={
                    "name": address.name,
                    "address_line1": address.address_line1,
                    "address_city": address.address_city,
                    "address_state": address.address_state,
                    "address_zip": address.address_zip,
                },
                from_address={
                    "name": "McLemore Auction Company",
                    "address_line1": "123 Example St",
                    "address_city": "Nashville",
                    "address_state": "TN",
                    "address_zip": "37209",
                },
                file=html_content,
                color=True
            )
            return {
                "id": letter.id,
                "status": letter.status
            }
        except Exception as e:
            raise LobAPIError(f"Letter creation failed: {str(e)}")

    def send_batch(self, addresses: List[Address], html_template: str) -> Dict[str, Any]:
        """
        Send a batch of letters. This is a naive loop approach for demonstration.
        """
        results = []
        for addr in addresses:
            try:
                res = self.send_letter(addr, html_template)
                results.append(res)
            except LobAPIError as e:
                results.append({"error": str(e), "address": addr})
        return {"results": results}