import requests
from .AIProvider import AIProvider , ProductivityCategory

class GeminiProvider(AIProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    
    def classify(self, resource_name: str) -> ProductivityCategory:
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": f"""
                    Classify this app/website for productivity (reply ONLY with one word):
                    - Productive: Work/learning (e.g., VSCode, Coursera, Wikipedia)
                    - Distracting: Entertainment (e.g., YouTube, games)
                    - Blocked: Harmful/illegal (e.g., phishing , sexual websites , not for kids ..)
                    - Neutral: System/utilities (e.g., Settings, Calculator)

                    Resource: {resource_name}
                    """
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 10,
                "temperature": 0.1
            }
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            answer = result['candidates'][0]['content']['parts'][0]['text'].strip()
            if answer in ["Productive", "Neutral", "Distracting", "Blocked"]:
                return answer
        except Exception as e:
            print(f"Gemini Error: {e}")
        return "Neutral"
