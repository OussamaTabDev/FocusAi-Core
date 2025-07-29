import os

from Providers.OpenAIProvider import OpenAIProvider
from Providers.AnthropicProvider import AnthropicProvider
from Providers.GroqProvider import GroqProvider
from Providers.GeminiProvider import GeminiProvider




# files 
CONFIG_FILE = 'config/process_map.json'
DATA_FILE = 'config/url_history.json'

#Api keys
apikey = ''

# pass-code
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "config/device_history.json")
# PROVIDER_FILE = os.path.join(os.path.dirname(__file__), "config/provider.json")
PASSCODE = "2025"   # <-- change this
provider_name = "provider.json"
provider_path = os.path.join(os.path.dirname(__file__), "config")
# # Providers and APIs
# def ProviderChosing(choice , api_key):
#     ai_provider = None
#     if choice == "1":
#         ai_provider = OpenAIProvider(api_key)
#     elif choice == "2":
#         ai_provider = AnthropicProvider(api_key)
#     elif choice == "3":
#         ai_provider = GeminiProvider(api_key)
#     elif choice == "4":
#         ai_provider = GroqProvider(api_key)
#     return ai_provider

# AI_PROVIDER =  ProviderChosing("3" , apikey)

# AiConfig