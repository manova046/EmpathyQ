# user/utils.py - Updated RazorpayClient
import razorpay
from django.conf import settings
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

class RazorpayClient:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    def create_order(self, amount, currency='INR'):
        """
        Create a Razorpay order
        amount should be in rupees (will be converted to paise)
        """
        try:
            # Convert Decimal to float and then to paise
            amount_in_paise = int(float(amount) * 100)
            
            data = {
                'amount': amount_in_paise,
                'currency': currency,
                'payment_capture': 1  # Auto capture payment
            }
            order = self.client.order.create(data=data)
            logger.info(f"Razorpay order created: {order['id']} for amount: {amount_in_paise} paise")
            return order
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")
            return None
    
    def verify_payment(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify payment signature
        """
        try:
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            self.client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return False
    
    def fetch_payment(self, payment_id):
        """
        Fetch payment details
        """
        try:
            payment = self.client.payment.fetch(payment_id)
            return payment
        except Exception as e:
            logger.error(f"Fetch payment failed: {str(e)}")
            return None