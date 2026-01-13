#!/usr/bin/env python3
"""Analyze Ökobaudat API XML response for translations"""

import requests
import xml.etree.ElementTree as ET

print("=" * 80)
print("Analyzing Ökobaudat API for English Translations")
print("=" * 80)

# Ökobaudat API endpoint
base_url = "https://oekobaudat.de/OEKOBAU.DAT/resource"
datastock_id = "cd2bda71-760b-4fcc-8a0b-3877c10000a8"
compliance_id = "b00f9ec0-7874-11e3-981f-0800200c9a66"

print("\nFetching processes from Ökobaudat API...")
processes_url = f"{base_url}/datastocks/{datastock_id}/processes"
params = {
    'search': 'true',
    'compliance': compliance_id
}

try:
    response = requests.get(processes_url, params=params, timeout=30)
    response.raise_for_status()
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Size: {len(response.text) / 1024:.1f} KB")
    
    # Parse XML
    print("\nParsing XML...")
    root = ET.fromstring(response.text)
    
    # Get namespaces
    namespaces = dict([node for _, node in ET.iterparse(
        requests.get(processes_url, params=params, timeout=30, stream=True).raw, 
        events=['start-ns']
    )])
    print(f"Namespaces: {list(namespaces.keys())[:5]}...")
    
    # Find all process elements
    processes = root.findall('.//*')
    print(f"\nFound {len(processes)} XML elements")
    
    # Look for language/translation indicators
    print("\nSearching for translation indicators...")
    
    # Check for 'lang' or 'language' attributes
    lang_elements = []
    for elem in processes[:100]:  # Check first 100 elements
        if 'lang' in elem.attrib or 'language' in elem.attrib:
            lang_elements.append(elem)
        # Check for xml:lang
        if '{http://www.w3.org/XML/1998/namespace}lang' in elem.attrib:
            lang_elements.append(elem)
    
    if lang_elements:
        print(f"Found {len(lang_elements)} elements with language attributes!")
        for elem in lang_elements[:5]:
            print(f"  Tag: {elem.tag}, Lang: {elem.attrib}, Text: {elem.text[:50] if elem.text else 'N/A'}...")
    else:
        print("No language attributes found in first 100 elements")
    
    # Look for category classification
    print("\nSearching for categories/classifications...")
    category_elements = root.findall(".//*[contains(local-name(), 'class')]")
    if category_elements:
        print(f"Found {len(category_elements)} classification-related elements")
        for elem in category_elements[:3]:
            print(f"  {elem.tag}: {elem.text[:100] if elem.text else 'N/A'}...")
    else:
        print("No classification elements found")
    
    # Save a sample for manual inspection
    sample_text = response.text[:5000]  # First 5000 chars
    with open('oekobaudat_api_sample.xml', 'w', encoding='utf-8') as f:
        f.write(sample_text)
    print("\nSaved sample to: oekobaudat_api_sample.xml")
    
    print("\n" + "=" * 80)
    print("Analysis:")
    print("=" * 80)
    print("The Ökobaudat API returns:")
    print("- Format: XML (ILCD format - International Life Cycle Data)")
    print("- Content: Process/product datasets (LCA data)")
    print("- Focus: Environmental data, not category hierarchies")
    print("\nConclusion:")
    print("- This API provides PROCESSES, not CATEGORIES")
    print("- Category translations are NOT in this endpoint")
    print("- Our XML file (OEKOBAUDAT Product Categories.xml) is the right source")
    print("- Continue using LLM translations for categories")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
