import requests
from django.conf import settings

def initialize_chapa_transaction(amount, email, reference):
    url = "https://api.chapa.co/v1/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
    }
    data = {
        "amount": str(amount),
        "email": email,
        "currency": "ETB",
        "tx_ref": reference,
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()


def verify_chapa_transaction(reference):
    url = f"https://api.chapa.co/v1/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }

    response = requests.get(url, headers=headers)
    return response.json()
