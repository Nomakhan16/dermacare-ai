import random

class DermatologyChatbot:
    def __init__(self):
        self.responses = {
            "acne": "Try salicylic acid or benzoyl peroxide products.",
            "dry skin": "Use hyaluronic acid and ceramide-based moisturizers.",
            "oily skin": "Oil-free, non-comedogenic products are best.",
            "wrinkles": "Retinol and vitamin C serums can help.",
            "sunscreen": "Use SPF 30+ daily, even indoors."
        }
    
    def respond(self, query):
        query = query.lower()
        for keyword, response in self.responses.items():
            if keyword in query:
                return response
        return "I recommend consulting with a dermatologist for personalized advice."