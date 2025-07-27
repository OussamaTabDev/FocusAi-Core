# productivity_tracker.py
import json
import os
import requests
from typing import Dict, Optional, Literal
from abc import ABC, abstractmethod
from Providers.AIProvider import AIProvider , ProductivityCategory

class ProductivityTracker:
    """
    A smart productivity classifier that:
    1. Uses hardcoded rules first (fast)
    2. Falls back to AI (multiple providers) for unknown cases
    3. Persists all data in a JSON file
    4. Allows user overrides
    """

    def __init__(
        self,
        config_path: str = "config/productivity_config.json",
        ai_provider: Optional[AIProvider] = None,
        auto_save: bool = True
    ):
        """
        Args:
            config_path: Where to store/load JSON data
            ai_provider: AI provider instance (OpenAI, Anthropic, Gemini, etc.)
            auto_save: Whether to save changes immediately
        """
        self.config_path = config_path
        self.auto_save = auto_save
        self.ai_provider = ai_provider
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load config from JSON or create default"""
        default_config = {
            "rules": {
                "Productive": ["vscode", "github", "notion", "stackoverflow", "docs.google", "coursera", "wikipedia", "khan", "udemy", "linkedin", "medium", "dev.to"],
                "Distracting": ["youtube", "tiktok", "instagram", "netflix", "facebook", "twitter", "reddit", "twitch", "discord", "snapchat"],
                "Blocked": ["malicioussite", "piratedcontent", "adultcontent", "gambling", "phishing"],
                "Neutral": ["weather", "calculator", "calendar", "settings", "system", "control panel", "task manager", "file explorer", "notepad", "clock"]
            },
            "ai_cache": {},
            "user_overrides": {}
        }

        if not os.path.exists(self.config_path):
            self._save_config(default_config)
            return default_config

        with open(self.config_path, "r") as f:
            config = json.load(f)
            
            # Merge with default to ensure all keys exist
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            
            return config

    def _save_config(self, config: Optional[Dict] = None):
        """Save config to JSON file"""
        with open(self.config_path, "w") as f:
            json.dump(config or self.config, f, indent=2)

    def detect_status(self, resource_name: str) -> ProductivityCategory:
        """
        Classify a resource with this priority:
        1. User overrides
        2. Hardcoded rules
        3. AI cache
        4. Fresh AI query (if enabled)
        """
        resource_name = resource_name.lower()
        
        # 1. Check user overrides (highest priority)
        override = self.config["user_overrides"].get(resource_name)
        if override:
            return override

        # 2. Rule-based matching
        for category, items in self.config["rules"].items():
            if any(item in resource_name for item in items):
                return category

        # 3. Check AI cache
        cached = self.config["ai_cache"].get(resource_name)
        if cached:
            return cached

        # print(f"ai_provider: {self.ai_provider}")
        # 4. AI fallback
        if self.ai_provider:
            ai_response = self.ai_provider.classify(resource_name)
            self.config["ai_cache"][resource_name] = ai_response
            if self.auto_save:
                self._save_config()
            return ai_response

        return "Neutral"  # Default fallback

    def add_rule(
        self,
        resource_name: str,
        category: ProductivityCategory,
        permanent: bool = True
    ):
        """Add a new rule or override"""
        resource_name = resource_name.lower()

        # Remove from other categories first
        for cat in self.config["rules"]:
            if resource_name in self.config["rules"][cat]:
                self.config["rules"][cat].remove(resource_name)

        # Add to specified category
        if resource_name not in self.config["rules"][category]:
            self.config["rules"][category].append(resource_name)

        if permanent and self.auto_save:
            self._save_config()

    def add_user_override(
        self,
        resource_name: str,
        category: ProductivityCategory,
        permanent: bool = True
    ):
        """Manually correct a classification"""
        self.config["user_overrides"][resource_name.lower()] = category
        if permanent and self.auto_save:
            self._save_config()

    def export_rules(self, file_path: str):
        """Backup rules to another JSON file"""
        with open(file_path, "w") as f:
            json.dump(self.config["rules"], f, indent=2)

    def import_rules(self, file_path: str):
        """Load rules from backup"""
        with open(file_path, "r") as f:
            self.config["rules"] = json.load(f)
        if self.auto_save:
            self._save_config()

    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            "rules_count": {cat: len(items) for cat, items in self.config["rules"].items()},
            "ai_cache_size": len(self.config["ai_cache"]),
            "user_overrides_count": len(self.config["user_overrides"])
        }


# # Example Usage
# if __name__ == "__main__":
#     # Choose your AI provider
#     print("Available AI providers:")
#     print("1. OpenAI (GPT)")
#     print("2. Anthropic (Claude)")
#     print("3. Google (Gemini)")
#     print("4. Groq (Fast Llama)")
#     print("5. No AI (rules only)")
    
#     choice = input("Choose provider (1-5): ")
    
    
    
#     # Initialize tracker
#     # tracker = ProductivityTracker(ai_provider=ai_provider)

#     # Test classifications
#     test_sites = ["github.com", "youtube.com", "reddit.com", "notion.so", "stackoverflow.com"]
    
#     print("\nTesting classifications:")
#     for site in test_sites:
#         status = tracker.detect_status(site)
#         print(f"{site}: {status}")

#     # Add manual corrections
#     tracker.add_user_override("facebook.com", "Distracting")
#     tracker.add_rule("mytimetracker.com", "Productive")

#     # Show stats
#     print("\nStats:", tracker.get_stats())

#     # Backup rules
#     tracker.export_rules("backup_rules.json")
#     print("Rules backed up to backup_rules.json")