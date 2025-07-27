# category_classifier.py
import re
# Import the loaded categories from our new config manager
from config_manager import CATEGORIES

class CategoryClassifier:
    """Classifies window types based on rules loaded from an external config."""
    def __init__(self):
        # The patterns are now loaded directly from the config manager
        self.patterns = CATEGORIES

    def classify(self, title: str, process_name: str = "", class_name: str = "") -> str:
        """
        Determines the window type by matching against the loaded patterns.
        (This method's logic is unchanged, but its data source is now dynamic)
        """
        if self.is_system(class_name , process_name):
            # print("this is system")
            return "system"
        
        title_lower = title.lower()
        process_lower = (process_name or "").lower()
        for window_type, patterns in self.patterns.items():
            for pattern in patterns:
                if (re.search(pattern, title_lower) or
                    re.search(pattern, process_lower) ):
                    return window_type
        
        return 'Not Calassified'
    
    def browser_classify(self, title: str, classified:str , app_name: str = "") -> str:
        """
        Determines if the window is a browser based on its title or process name.
        """
        app_lower = app_name.lower()
        if classified == 'browser':
            for window_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if (re.search(pattern, app_lower) ):
                        return window_type
            
        return classified
    
#'ApplicationFrameHost' in process_name
# or  'ApplicationFrame' in class_name
    def is_system(self ,class_name: str , process_name: str) -> bool:
        return  'Windows.' in class_name 
    