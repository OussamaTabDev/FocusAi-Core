from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Set, Union
from config_manager import last_url
from models import  WindowInfo

# def window_to_tab_info(window: WindowInfo) -> Optional[TabInfo]:
#     """
#     Convert WindowInfo to TabInfo if the window is a browser tab.
#     Returns None if not a browser window.
#     """
#     if window.window_type != 'browser':
#         return None
    
#     try:
#         # Get the most recent URL from your URL tracking system
#         url_data = last_url()
        
#         # Extract domain from URL if not already present
#         domain = url_data.get('domain')
#         if not domain and 'url' in url_data:
#             parsed = urlparse(url_data['url'])
#             domain = parsed.netloc
        
#         return TabInfo(
#             url=url_data.get('url', ''),
#             title=window.raw_title,
#             domain=domain,
#             timestamp=window.timestamp,
#             server_timestamp=datetime.now().isoformat(),
#             window_id=window.window_id,
#             is_active=window.is_active,
#             # Browser-specific metadata
#             status=window.status,
#             category=window.context,
#             extra_info={
#                 'process_name': window.process_name,
#                 'browser_name': window.original_app,
#                 'app': window.app,
#                 'window_state': {
#                     'position': window.position,
#                     'size': window.size,
#                     'z_order': window.z_order
#                 }
#             }
#         )
#     except Exception as e:
#         print(f"Error converting window to tab info: {e}")
#         return None