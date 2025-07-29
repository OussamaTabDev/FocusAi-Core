
from typing import Dict, Optional, Literal
from abc import ABC, abstractmethod
# Types for better code hints
ProductivityCategory = Literal["Productive", "Neutral", "Distracting", "Blocked"]
ValidCategories = Literal[
            "Entertainment",
            "Social Media",
            "Games",
            "Productivity",
            "Communication",
            "Shopping",
            "Finance",
            "News & Information",
            "Utilities",
            "Education",
            "Cloud Storage",
            "Developer Tools",
            "Travel & Navigation",
            "Health & Fitness",
            "Adult Content"
        ]
class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def classify(self, resource_name: str) -> ProductivityCategory:
        pass
    
    # @abstractmethod
    # def cat_classify(self, resource_name: str) -> ValidCategories:
    #     """
    #     Classify a resource into categories.
        
    #     Returns a dictionary with keys as category names and values as their classification.
    #     """
    #     pass
    