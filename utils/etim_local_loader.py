#!/usr/bin/env python3
"""
Local ETIM JSON Loader

Loads ETIM classes from local JSON file instead of bsDD API.
Use when API is unavailable or for faster/offline processing.
"""

import json
from typing import List
from dataclasses import dataclass


@dataclass
class BsddClass:
    """bsDD class entry (compatible with API version)"""
    uri: str
    code: str
    name: str
    definition: str
    domain_namespace: str


class LocalEtimLoader:
    """Load ETIM classes from local JSON file"""
    
    def __init__(self, json_path: str = "bsDD Repo/etim-10.1.json"):
        """Initialize with path to ETIM JSON file"""
        self.json_path = json_path
        self.data = None
    
    def load(self) -> List[BsddClass]:
        """Load ETIM classes from JSON file"""
        print(f"Loading ETIM classes from local file: {self.json_path}")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        classes = []
        domain_namespace = f"https://identifier.buildingsmart.org/uri/{self.data['OrganizationCode']}/{self.data['DictionaryCode']}-{self.data['DictionaryVersion']}"
        
        for cls_data in self.data.get('Classes', []):
            # Skip non-active or group classes if needed
            if cls_data.get('Status') != 'Active':
                continue
            
            # Create BsddClass object
            cls = BsddClass(
                uri=cls_data.get('Uri', ''),
                code=cls_data.get('Code', ''),
                name=cls_data.get('Name', ''),
                definition=cls_data.get('Definition', ''),
                domain_namespace=domain_namespace
            )
            
            # Generate URI if not present
            if not cls.uri:
                cls.uri = f"{domain_namespace}/class/{cls.code}"
            
            classes.append(cls)
        
        print(f"OK - Loaded {len(classes)} active ETIM classes")
        return classes
    
    def get_info(self) -> dict:
        """Get dictionary information"""
        if not self.data:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        
        return {
            'name': self.data.get('DictionaryName'),
            'version': self.data.get('DictionaryVersion'),
            'language': self.data.get('LanguageIsoCode'),
            'release_date': self.data.get('ReleaseDate'),
            'status': self.data.get('Status'),
            'total_classes': len(self.data.get('Classes', []))
        }


def main():
    """Test the loader"""
    print("=" * 80)
    print("Local ETIM JSON Loader - Test")
    print("=" * 80)
    
    loader = LocalEtimLoader()
    
    # Get info
    info = loader.get_info()
    print("\nETIM Dictionary Info:")
    print(f"  Name: {info['name']}")
    print(f"  Version: {info['version']}")
    print(f"  Language: {info['language']}")
    print(f"  Release: {info['release_date']}")
    print(f"  Status: {info['status']}")
    print(f"  Total classes: {info['total_classes']}")
    
    # Load classes
    print("\nLoading classes...")
    classes = loader.load()
    
    # Show examples
    print("\n" + "=" * 80)
    print(f"Example Classes (first 10 of {len(classes)}):")
    print("=" * 80)
    
    for i, cls in enumerate(classes[:10], 1):
        print(f"\n{i}. {cls.name}")
        print(f"   Code: {cls.code}")
        print(f"   Definition: {cls.definition[:80]}...")
        print(f"   URI: {cls.uri}")
    
    print("\n" + "=" * 80)
    print("OK - Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

