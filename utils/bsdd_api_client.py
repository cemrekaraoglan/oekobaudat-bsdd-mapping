#!/usr/bin/env python3
"""
bsDD API Client

Official buildingSMART Data Dictionary API client for fetching ETIM and other classification data.
Based on: https://technical.buildingsmart.org/services/bsdd/using-the-bsdd-api/

API Documentation: https://api.bsdd.buildingsmart.org/swagger/index.html
"""

import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class BsddClass:
    """bsDD class entry (compatible with local loader)"""
    uri: str
    code: str
    name: str
    definition: str
    domain_namespace: str


class BsddApiClient:
    """
    Client for buildingSMART Data Dictionary API
    
    Usage:
        client = BsddApiClient()
        etim_classes = client.get_etim_classes(version="10.1")
    """
    
    # Official API endpoints
    BASE_URL = "https://api.bsdd.buildingsmart.org"
    BASE_URL_TEST = "https://test.bsdd.buildingsmart.org"
    
    # User agent for tracking (as requested by bsDD)
    USER_AGENT = "bsDD-Oekobaudat-Mapper/1.0"
    
    def __init__(self, use_test: bool = False, timeout: int = 30):
        """
        Initialize bsDD API client
        
        Args:
            use_test: Use test environment instead of production
            timeout: Request timeout in seconds
        """
        self.base_url = self.BASE_URL_TEST if use_test else self.BASE_URL
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json'
        })
    
    def get_dictionaries(self) -> List[Dict]:
        """
        Get list of available dictionaries in bsDD
        
        Returns:
            List of dictionary metadata
        """
        url = f"{self.base_url}/api/Dictionary/v1"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            dictionaries = data.get('dictionaries', [])
            
            print(f"Found {len(dictionaries)} dictionaries in bsDD")
            return dictionaries
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching dictionaries: {e}")
            return []
    
    def find_etim_dictionary(self, version: Optional[str] = None) -> Optional[Dict]:
        """
        Find ETIM dictionary in bsDD
        
        Args:
            version: Specific ETIM version (e.g., "10.1"), or None for latest
        
        Returns:
            Dictionary metadata or None
        """
        dictionaries = self.get_dictionaries()
        
        # Try multiple ways to identify ETIM
        etim_dicts = []
        for d in dictionaries:
            # Check organization name or code
            org_code = d.get('organizationCodeOwner', '').lower()
            org_name = d.get('organizationNameOwner', '').lower()
            dict_name = d.get('name', '').lower()
            dict_code = d.get('code', '').lower()
            
            if 'etim' in org_code or 'etim' in org_name or dict_code == 'etim':
                etim_dicts.append(d)
        
        if not etim_dicts:
            print("No ETIM dictionaries found")
            print(f"Available dictionaries (sample): {[d.get('name') for d in dictionaries[:5]]}")
            return None
        
        if version:
            # Find specific version
            for d in etim_dicts:
                dict_version = d.get('version', '')
                if dict_version == version:
                    return d
            print(f"ETIM version {version} not found")
            print(f"Available ETIM versions: {[d.get('version') for d in etim_dicts]}")
            return None
        else:
            # Return latest (first in list, usually most recent)
            return etim_dicts[0]
    
    def get_dictionary_classes(self, dictionary_uri: str, 
                                include_test_classes: bool = False) -> List[Dict]:
        """
        Get all classes from a dictionary
        
        Args:
            dictionary_uri: Full URI of dictionary (e.g., "https://identifier.buildingsmart.org/uri/etim/etim-10.1")
            include_test_classes: Include test/inactive classes
        
        Returns:
            List of class data from API
        """
        # Use the Dictionary Classes endpoint
        url = f"{self.base_url}/api/Dictionary/v1/Classes"
        
        params = {
            'Uri': dictionary_uri,
            'includeTestClasses': str(include_test_classes).lower()
        }
        
        try:
            print(f"Fetching classes from: {dictionary_uri}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            classes = data.get('classes', [])
            
            print(f"Retrieved {len(classes)} classes")
            return classes
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching classes: {e}")
            return []
    
    def get_class_details(self, class_uri: str) -> Optional[Dict]:
        """
        Get detailed information about a specific class
        
        Args:
            class_uri: Full URI of class
        
        Returns:
            Class details or None
        """
        url = f"{self.base_url}/api/Class/v1"
        
        params = {
            'Uri': class_uri,
            'includeClassProperties': 'false'  # We don't need properties for mapping
        }
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching class details for {class_uri}: {e}")
            return None
    
    def get_etim_classes(self, version: Optional[str] = None, 
                         filter_category: Optional[str] = None) -> List[BsddClass]:
        """
        Get ETIM classes from bsDD API (main method)
        
        Args:
            version: ETIM version (e.g., "10.1"), or None for latest
            filter_category: Optional category filter (e.g., "EC00" for building materials)
        
        Returns:
            List of BsddClass objects
        """
        print("\n" + "=" * 80)
        print("Fetching ETIM Classes from bsDD API")
        print("=" * 80)
        
        # Step 1: Find ETIM dictionary
        print(f"\n[1/3] Finding ETIM dictionary (version: {version or 'latest'})...")
        etim_dict = self.find_etim_dictionary(version)
        
        if not etim_dict:
            print("Failed to find ETIM dictionary")
            return []
        
        dict_uri = etim_dict.get('uri')
        dict_version = etim_dict.get('version', 'unknown')
        dict_name = etim_dict.get('name', 'ETIM')
        
        print(f"   Found: {dict_name} v{dict_version}")
        print(f"   URI: {dict_uri}")
        
        # Step 2: Get all classes
        print(f"\n[2/3] Fetching classes from API...")
        api_classes = self.get_dictionary_classes(dict_uri, include_test_classes=False)
        
        if not api_classes:
            print("No classes retrieved")
            return []
        
        # Step 3: Convert to BsddClass objects
        print(f"\n[3/3] Converting to standard format...")
        bsdd_classes = []
        
        for cls_data in api_classes:
            # Extract data
            code = cls_data.get('code', '')
            name = cls_data.get('name', '')
            definition = cls_data.get('definition', '')
            class_uri = cls_data.get('uri', '')
            
            # Apply filter if specified
            if filter_category and not code.startswith(filter_category):
                continue
            
            # Create BsddClass object
            bsdd_class = BsddClass(
                uri=class_uri,
                code=code,
                name=name,
                definition=definition,
                domain_namespace=dict_uri
            )
            
            bsdd_classes.append(bsdd_class)
        
        print(f"   Loaded {len(bsdd_classes)} active ETIM classes")
        
        if filter_category:
            print(f"   Filtered to category: {filter_category}")
        
        print("\n" + "=" * 80)
        return bsdd_classes
    
    def search_classes(self, search_text: str, dictionary_uri: Optional[str] = None) -> List[Dict]:
        """
        Search for classes by text
        
        Args:
            search_text: Search query
            dictionary_uri: Optional dictionary URI to limit search
        
        Returns:
            List of matching classes
        """
        url = f"{self.base_url}/api/SearchList/v1"
        
        params = {
            'SearchText': search_text
        }
        
        if dictionary_uri:
            params['DictionaryUri'] = dictionary_uri
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('classes', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching classes: {e}")
            return []


def main():
    """Test the API client"""
    client = BsddApiClient()
    
    # Test 1: List available dictionaries
    print("\n=== Available Dictionaries ===")
    dicts = client.get_dictionaries()
    for d in dicts[:5]:  # Show first 5
        print(f"- {d.get('name')} ({d.get('code')}) v{d.get('version')}")
    
    # Test 2: Get ETIM classes
    print("\n=== ETIM Classes ===")
    etim_classes = client.get_etim_classes(version="10.1")
    
    # Show sample
    print("\nSample classes (first 5):")
    for cls in etim_classes[:5]:
        print(f"\n{cls.code}: {cls.name}")
        print(f"  {cls.definition[:100]}..." if cls.definition else "  (no definition)")
    
    print(f"\nTotal: {len(etim_classes)} classes")


if __name__ == '__main__':
    main()
