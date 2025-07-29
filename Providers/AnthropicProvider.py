import requests
from .AIProvider import AIProvider , ProductivityCategory , ValidCategories

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
    
    # TODO: Implement category classification (POST-MVP)
    # def cat_classify(self, resource_name: str) -> ValidCategories:
    #     headers = {
    #         "x-api-key": self.api_key,
    #         "Content-Type": "application/json",
    #         "anthropic-version": "2023-06-01"
    #     }
        
    #     data = {
    #         "model": "claude-3-haiku-20240307",
    #         "max_tokens": 20,
    #         "messages": [{
    #             "role": "user",
    #             "content": f"""
    #             Classify this app/website into one of these categories (reply ONLY with one word):
    #             - Games: Online and offline games, gaming platforms (e.g., Steam, Epic Games, Roblox)
    #             - Entertainment: Video and music streaming (e.g., YouTube, Netflix, Spotify)
    #             - Social Media: Networking platforms (e.g., Facebook, Twitter, Instagram, TikTok)
    #             - Productivity: Work and study tools (e.g., Google Docs, Notion, Microsoft Office)
    #             - Communication: Messaging and voice/video apps (e.g., WhatsApp, Discord, Zoom)
    #             - Shopping: E-commerce and retail platforms (e.g., Amazon, eBay, AliExpress)
    #             - Finance: Banking, payments, crypto, and investing (e.g., PayPal, Binance, Robinhood)
    #             - News & Information: News sites and knowledge bases (e.g., BBC, Wikipedia, Quora)
    #             - Utilities: System tools and services (e.g., antivirus, file managers, VPNs)
    #             - Education: Learning platforms and resources (e.g., Coursera, Khan Academy, Duolingo)
    #             - Cloud Storage: File syncing and hosting services (e.g., Google Drive, Dropbox)
    #             - Developer Tools: Coding, documentation, and collaboration (e.g., GitHub, Stack Overflow, VS Code)
    #             - Travel & Navigation: Maps, booking, and ride services (e.g., Google Maps, Uber, Airbnb)
    #             - Health & Fitness: Wellness, workouts, and tracking apps (e.g., Fitbit, MyFitnessPal, Headspace)
    #             - Adult Content: Explicit and NSFW websites (e.g., OnlyFans, Pornhub, Stripchat)
                
    #             Resource: {resource_name}
    #             """
    #         }]
    #     }
        
    #     try:
    #         response = requests.post(self.base_url, headers=headers, json=data)
    #         response.raise_for_status()
    #         result = response.json()
    #         answer = result['content'][0]['text'].strip()
    #         if answer in ValidCategories :
    #             return answer
    #         return "Other"  # Default category for unclassified resources
    #     except Exception as e:
    #         print(f"Anthropic Error: {e}")
    #     return "Other"  # Default category on error