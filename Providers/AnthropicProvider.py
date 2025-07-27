import requests
from .AIProvider import AIProvider , ProductivityCategory

class AnthropicProvider(AIProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def classify(self, resource_name: str) -> ProductivityCategory:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 10,
            "messages": [{
                "role": "user",
                "content": f"""
                Classify this app/website for productivity (reply ONLY with one word):
                - Productive: Work/learning (e.g., VSCode, Coursera, Wikipedia)
                - Distracting: Entertainment (e.g., YouTube, games)
                - Blocked: Harmful/illegal (e.g., phishing, sexual websites)
                - Neutral: System/utilities (e.g., Settings, Calculator)

                Resource: {resource_name}
                """
            }]
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            answer = result['content'][0]['text'].strip()
            if answer in ["Productive", "Neutral", "Distracting", "Blocked"]:
                return answer
        except Exception as e:
            print(f"Anthropic Error: {e}")
        return "Neutral"
