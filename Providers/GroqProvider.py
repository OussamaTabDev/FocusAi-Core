import requests
from .AIProvider import AIProvider , ProductivityCategory

class GroqProvider(AIProvider):
    """Groq provider (fast inference)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def classify(self, resource_name: str) -> ProductivityCategory:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",
            "messages": [{
                "role": "user",
                "content": f"""
                Classify this app/website for productivity (reply ONLY with one word):
                - Productive: Work/learning (e.g., VSCode, Coursera)
                - Distracting: Entertainment (e.g., YouTube, games)
                - Blocked: Harmful/illegal (e.g., phishing , sexual websites , not for kids ..)
                - Neutral: Unclassified (e.g., Wikipedia)

                Resource: {resource_name}
                """
            }],
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            if answer in ["Productive", "Neutral", "Distracting", "Blocked"]:
                return answer
        except Exception as e:
            print(f"Groq Error: {e}")
        return "Neutral"
