# parser.py
from models import WindowInfo
from category_classifier import CategoryClassifier
from config_manager import ensure_process_mapped , processed_domain , PREFIXES , get_domain



class WindowTitleParser:
    """Parses a raw window title into a structured format."""

    def __init__(self, classifier: CategoryClassifier):
        self.cat_classifier = classifier

    def parse(self, raw_title: str, process_name: str, class_name: str) -> dict:
        """
        Parses the window title and returns a dictionary of parsed components.
        
        Returns:
            A dictionary with keys like 'app', 'context', 'display_title', and 'window_type'.
        """
        # Get window type from classifier
        window_type = self.cat_classifier.classify(raw_title, process_name, class_name)
        
        # Initialize parsed data structure
        parsed_data = {
            "window_type": window_type,
            "app": "",
            "sub_app": "",
            "context": raw_title,
            "display_title": raw_title,
            "original_app": "",
            "domain": "",
        }
        
        # Handle different window types
        if window_type == "file_manager":
            self._handle_file_manager(raw_title, parsed_data)
        elif window_type in ["system", "search"]:
            self._handle_system(raw_title, parsed_data)
        elif window_type == "browser":
            # parsed_data["original_app"] = parsed_data
            # print(f" orgins ,: {parsed_data['original_app']}")
            url_app = processed_domain()
            # print("Urls: " , url_app )
            if url_app :
                parsed_data["domain"] = get_domain()
                raw_title = handle_raw_title(raw_title, process_name , url_app)
                self._handle_browser(raw_title, process_name, parsed_data , url_app)
        else:
            raw_title = process_raw_title(raw_title, process_name, parsed_data)
            self._handle_generic(raw_title, process_name, parsed_data)
        
        # Create final display title
        self._create_display_title(parsed_data)
        
        return parsed_data

    def _handle_file_manager(self, raw_title: str, parsed_data: dict):
        """Handle file manager windows."""
        parsed_data['app'] = "File Explorer"
        parsed_data['sub_app'] = "File Explorer"
        
        # Extract path from title
        path_context = raw_title.replace("File Explorer", "").strip()
        parsed_data['context'] = path_context

    def _handle_system(self, raw_title: str, parsed_data: dict):
        """Handle system and search windows."""
        parsed_data['app'] = "System"
        parsed_data['sub_app'] = "System"
        parsed_data['context'] = raw_title

    def _handle_browser(self, raw_title: str, process_name: str, parsed_data: dict , url_app: str):
        """Handle browser windows."""
        # First parse the generic format
        self._parse_title_parts(raw_title, process_name, parsed_data)
        
        # # Then adjust for browser-specific formatting
        if  url_app != "browser":
            browser_sub_app = parsed_data["sub_app"]
            parsed_data["sub_app"] = f"Browser ({parsed_data['app']})"
            parsed_data["app"] = browser_sub_app
            # print(f"window type before: {parsed_data['window_type']}")
            parsed_data['window_type'] = self.cat_classifier.browser_classify(raw_title, parsed_data["window_type"], parsed_data["app"])
            # print(f"window type after: {parsed_data['window_type']}")

    def _handle_generic(self, raw_title: str, process_name: str, parsed_data: dict):
        """Handle generic windows with standard formatting."""
        self._parse_title_parts(raw_title, process_name, parsed_data)

    def _parse_title_parts(self, raw_title: str, process_name: str, parsed_data: dict):
        """Parse title parts in 'Context - App' format."""
        parts = [part.strip() for part in raw_title.split(" - ") if part.strip()]
        
        if len(parts) == 1:
            # Just app name or document name
            if 'ApplicationFrameHost' in process_name:
                parsed_data['context'] = parts[0]
                parsed_data['sub_app'] = parts[0]
                parsed_data['app'] = parts[0]
            else: 
                parsed_data['app'] = ensure_process_mapped(process_name) if  process_name.endswith(".exe") else process_name
                parsed_data['sub_app'] = ensure_process_mapped(process_name) if  process_name.endswith(".exe") else process_name
                parsed_data['context'] = parts[0]
            
        elif len(parts) == 2:
            # Common format: "Document - Application"
            parsed_data['context'] = parts[0]
            parsed_data['sub_app'] = parts[0]
            parsed_data['app'] = parts[1]
            
        else:
            # Multiple parts: "Context - SubApp - App"
            parsed_data['context'] = " - ".join(parts[:-2])
            # print("context: ", parsed_data['context'])
            parsed_data['sub_app'] = parts[-2]
            parsed_data['app'] = parts[-1]
            
        parsed_data['original_app'] = parts[-1]
        # print(parsed_data['original_app'])

    def _create_display_title(self, parsed_data: dict):
        """Create the final display title."""
        context = parsed_data.get('context', '')
        app = parsed_data.get('app', '')
        
        if context and app:
            parsed_data['display_title'] = f"{context} - {app}"
        elif context:
            parsed_data['display_title'] = context
        elif app:
            parsed_data['display_title'] = app
        else:
            parsed_data['display_title'] = "Unknown Window"


# def process_raw_title(raw_title, process_name, class_name):
#     """Placeholder for additional raw title processing."""
#     p_raw_title = raw_title
#     parts = [part.strip() for part in p_raw_title.split(" - ") if part.strip()] 
#     sub_parts = [part.strip() for part in parts[-1].split(" ") if part.strip()] 
#     # Remove any parts that are in our prefixes list
#     cleaned_parts = [part for part in sub_parts if part.lower() not in PREFIXES]
#     #combine to one 
#     combined_part = cleaned_parts
#     PREFIXES
#     return p_raw_title

def process_raw_title(raw_title, process_name, class_name):
    """Clean the raw title by removing specified prefixes from the last segment.
    
    Args:
        raw_title (str): The original title to process
        process_name (str): The process name (unused)
        class_name (str): The class name (unused)
    
    Returns:
        str: The cleaned title with prefixes removed from the last segment
    """
    # Split into main parts separated by " - "
    parts = [part.strip() for part in raw_title.split(" - ") if part.strip()]
    
    if not parts:
        return raw_title
    
    # Process the last part by splitting into words and removing prefixes
    last_part = parts[-1]
    sub_parts = [word.strip() for word in last_part.split(" ") if word.strip()]
    cleaned_words = [word for word in sub_parts if word.lower() not in PREFIXES]
    
    # Rebuild the last part without prefixes
    parts[-1] = " ".join(cleaned_words)
    
    # Recombine all parts with " - " separator
    return " - ".join(parts)

def handle_raw_title(raw_title, process_name, url_app):
    p_raw_title = raw_title
    
    # If the url_app is browser, we don't need to process the title
    if url_app == "browser":
        p_raw_title =  process_name
    else:
        parts = [part.strip() for part in p_raw_title.split(" - ") if part.strip()] 
        if len(parts) == 2:
            if parts[-2].lower() != url_app:
                p_raw_title = parts[-2] + " - " + url_app.capitalize() + " - " + parts[-1]
                
        else:
            if parts[-3].lower() == url_app:
                # flip the last two parts
                p_raw_title = parts[-2] + " - " + parts[-3] + " - " + parts[-1]
            else:
                # if not exits
                p_raw_title = parts[-2] + " - " + url_app.capitalize() + " - " + parts[-1]
                
            
    return p_raw_title