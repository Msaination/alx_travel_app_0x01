import os
# import requests

class ChapaServices:
    def __init__(self):
        self.secrete_key = os.getenv("CHAPA_SECRET_KEY")
        self.base_url = "https://api.chapa.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",     
        }

    def initialize_payment(self, transaction_id, booking_reference, amount, email, first_name, last_name):
        url = f"{self.base_url}/transaction/initialize"

        payload = {
            
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "amount": amount,
            "tx_ref": transaction_id,
            "booking_reference": booking_reference,
            "currency": "ETB",
            "customization[title]": "Booking Payment",
            "callback_url": callback_url,
            "return_url": f"http://127.0.0.1:8000/api/listings/payment/verify/{transaction_id}",
            "customization[description]": "Payment for booking",
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error initializing payment: {e}")
            return None

    def verify_payment(self, transaction_id):
        url = f"{self.base_url}/transaction/verify/{transaction_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error verifying payment: {e}")
            return None