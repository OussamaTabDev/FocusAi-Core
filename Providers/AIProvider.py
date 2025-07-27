
from typing import Dict, Optional, Literal
from abc import ABC, abstractmethod
# Types for better code hints
ProductivityCategory = Literal["Productive", "Neutral", "Distracting", "Blocked"]

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def classify(self, resource_name: str) -> ProductivityCategory:
        pass
    
    # @abstractmethod
    # def cat_classify(self, resource_name: str) -> str:
    #     """
    #     Classify a resource into categories.
        
    #     Returns a dictionary with keys as category names and values as their classification.
    #     """
    #     pass