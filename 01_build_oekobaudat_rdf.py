#!/usr/bin/env python3
"""
STEP 01: Build Ökobaudat RDF Graph (OWL Edition)

Converts Ökobaudat product categories XML into an OWL ontology.
Uses cached LLM translations for English labels.
Creates OWL classes with rdfs:subClassOf hierarchy.

SKOS is NOT used here - reserved for Step 02 mapping.
"""

import xml.etree.ElementTree as ET
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import re


@dataclass
class OekobaudatCategory:
    """Represents an Ökobaudat category"""
    id: str
    name_de: str
    name_en: Optional[str]
    parent_id: Optional[str]
    children_ids: List[str]
    level: int
    full_path_de: str
    full_path_en: Optional[str]


class OekobaudatRdfBuilder:
    """Builds OWL ontology from Ökobaudat XML"""
    
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.graph = Graph()
        
        # Define namespaces
        self.OBD = Namespace("https://oekobaudat.de/class/")  # OWL classes
        self.OEKOCAT = Namespace("https://oekobaudat.de/category/")  # Category IDs
        
        # Bind namespaces
        self.graph.bind("obd", self.OBD)
        self.graph.bind("oekocat", self.OEKOCAT)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dcterms", DCTERMS)
        
        # Store categories
        self.categories: Dict[str, OekobaudatCategory] = {}
        
        # Define custom property
        self._define_custom_property()
    
    def _define_custom_property(self):
        """Define the okobaudatCategory property"""
        prop_uri = self.OBD["okobaudatCategory"]
        self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
        self.graph.add((prop_uri, RDFS.label, Literal("ÖKOBAUDAT category reference", lang='en')))
        self.graph.add((prop_uri, RDFS.label, Literal("ÖKOBAUDAT Kategorie-Referenz", lang='de')))
        self.graph.add((prop_uri, RDFS.comment, Literal("Links an OWL class to its Ökobaudat category ID", lang='en')))
    
    def _name_to_class_name(self, name_de: str) -> str:
        """Convert German name to valid class name"""
        # Replace spaces and special chars with underscores
        class_name = re.sub(r'[^\w\s-]', '', name_de)
        class_name = re.sub(r'[\s-]+', '_', class_name)
        return class_name
    
    def parse_xml(self) -> Dict[str, OekobaudatCategory]:
        """Parse Ökobaudat XML"""
        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        
        ns = {
            'ns2': 'http://lca.jrc.it/ILCD/Categories',
            'common': 'http://lca.jrc.it/ILCD/Common'
        }
        
        categories_elem = root.find('.//ns2:categories[@dataType="Process"]', ns)
        if categories_elem is not None:
            self._parse_categories_recursive(categories_elem, ns, None, "", 0)
        
        return self.categories
    
    def _parse_categories_recursive(self, parent_elem, ns, parent_id, parent_path, level):
        """Recursively parse category hierarchy"""
        for category in parent_elem.findall('ns2:category', ns):
            cat_id = category.get('id')
            cat_name_de = category.get('name')
            
            full_path_de = f"{parent_path}/{cat_name_de}" if parent_path else cat_name_de
            
            cat_obj = OekobaudatCategory(
                id=cat_id,
                name_de=cat_name_de,
                name_en=None,  # Will be filled by translator
                parent_id=parent_id,
                children_ids=[],
                level=level,
                full_path_de=full_path_de,
                full_path_en=None
            )
            
            self.categories[cat_id] = cat_obj
            
            if parent_id and parent_id in self.categories:
                self.categories[parent_id].children_ids.append(cat_id)
            
            self._parse_categories_recursive(category, ns, cat_id, full_path_de, level + 1)
    
    def add_category_to_graph(self, cat_id: str):
        """Add category as OWL class"""
        category = self.categories.get(cat_id)
        if not category:
            return
        
        # Create class URI from German name
        class_name = self._name_to_class_name(category.name_de)
        class_uri = self.OBD[class_name]
        
        # Define as OWL Class
        self.graph.add((class_uri, RDF.type, OWL.Class))
        
        # Add labels (multilingual)
        self.graph.add((class_uri, RDFS.label, Literal(category.name_de, lang='de')))
        if category.name_en:
            self.graph.add((class_uri, RDFS.label, Literal(category.name_en, lang='en')))
        
        # Add comments/descriptions (path as description)
        self.graph.add((class_uri, RDFS.comment, Literal(category.full_path_de, lang='de')))
        if category.full_path_en:
            self.graph.add((class_uri, RDFS.comment, Literal(category.full_path_en, lang='en')))
        
        # Link to category ID using custom property
        cat_id_uri = self.OEKOCAT[cat_id]
        self.graph.add((class_uri, self.OBD["okobaudatCategory"], cat_id_uri))
        
        # Add hierarchy using rdfs:subClassOf
        if category.parent_id:
            parent_cat = self.categories.get(category.parent_id)
            if parent_cat:
                parent_class_name = self._name_to_class_name(parent_cat.name_de)
                parent_class_uri = self.OBD[parent_class_name]
                self.graph.add((class_uri, RDFS.subClassOf, parent_class_uri))
    
    def build_complete_graph(self) -> Graph:
        """Build the complete OWL ontology"""
        print("Building OWL ontology for Ökobaudat...")
        
        # Parse XML if not already done
        if not self.categories:
            self.parse_xml()
            print(f"  Parsed {len(self.categories)} categories")
        
        # Add all categories as OWL classes
        for cat_id in self.categories.keys():
            self.add_category_to_graph(cat_id)
        
        print(f"  Created {len(self.categories)} OWL classes")
        print(f"  Total triples: {len(self.graph)}")
        
        return self.graph
    
    def serialize(self, output_path: str, format: str = 'turtle'):
        """Serialize the graph"""
        self.graph.serialize(destination=output_path, format=format)
        print(f"  Saved to: {output_path}")
    
    def export_for_translation(self, output_path: str):
        """Export categories with translations to JSON"""
        translation_data = []
        
        for cat in self.categories.values():
            translation_data.append({
                'id': cat.id,
                'name_de': cat.name_de,
                'name_en': cat.name_en or '',  # Include actual translation
                'full_path_de': cat.full_path_de,
                'full_path_en': cat.full_path_en or '',  # Include actual translation
                'level': cat.level
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, indent=2, ensure_ascii=False)
        
        print(f"  Exported {len(translation_data)} items with translations to: {output_path}")


class AutoTranslator:
    """Automatically translates German terms to English"""
    
    def __init__(self, cache_path: Optional[str] = None):
        """Initialize translator with optional cache file"""
        self.cache = {}
        if cache_path:
            self.load_cache(cache_path)
    
    def load_cache(self, cache_path: str):
        """Load cached translations from JSON file"""
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
            print(f"  Loaded {len(self.cache)} cached translations")
        except FileNotFoundError:
            print(f"  Cache file not found: {cache_path}")
        except Exception as e:
            print(f"  Error loading cache: {e}")
    
    # Common building material translations (fallback)
    TRANSLATION_DICT = {
        # Main categories
        "Mineralische Baustoffe": "Mineral Building Materials",
        "Dämmstoffe": "Insulation Materials",
        "Holz": "Wood",
        "Metalle": "Metals",
        "Beschichtungen": "Coatings",
        "Kunststoffe": "Plastics",
        "Komponenten von Fenstern und Vorhangfassaden": "Components of Windows and Curtain Facades",
        "Gebäudetechnik": "Building Services",
        "Sonstige": "Other",
        "Komposite": "Composites",
        "End of Life": "End of Life",
        
        # Binders
        "Bindemittel": "Binders",
        "Zement": "Cement",
        "Kalk": "Lime",
        "Gips": "Gypsum",
        "Lehm": "Clay",
        
        # Aggregates
        "Zuschläge": "Aggregates",
        "Sand und Kies": "Sand and Gravel",
        "Naturstein": "Natural Stone",
        
        # Stones and elements
        "Steine und Elemente": "Bricks and Elements",
        "Kalksandstein": "Calcium Silicate Brick",
        "Ziegel": "Brick",
        "Porenbeton": "Aerated Concrete",
        "Leichtbeton": "Lightweight Concrete",
        "Betonfertigteile und Betonwaren": "Precast Concrete Elements",
        "Gipsplatten": "Gypsum Board",
        "Fliesen und Platten": "Tiles and Slabs",
        
        # Mortar and concrete
        "Mörtel und Beton": "Mortar and Concrete",
        "Beton": "Concrete",
        "Mauermörtel": "Masonry Mortar",
        "Estrich trocken": "Dry Screed",
        
        # Insulation
        "Mineralwolle": "Mineral Wool",
        "Glaswolle": "Glass Wool",
        "Steinwolle": "Stone Wool",
        "Holzfaserdämmplatte": "Wood Fiber Insulation Board",
        
        # Wood
        "Vollholz": "Solid Wood",
        "Holzwerkstoffe": "Wood-Based Materials",
        
        # Metals
        "Stahl": "Steel",
        "Stahlprofile": "Steel Profiles",
        "Aluminium": "Aluminum",
        
        # Common terms
        "Platten": "Boards",
        "und": "and",
        "mit": "with",
        "für": "for"
    }
    
    def translate(self, german_text: str) -> str:
        """Translate German text to English"""
        # 1. Check cache first (LLM translations)
        if german_text in self.cache:
            return self.cache[german_text]
        
        # 2. Check hardcoded dictionary
        if german_text in self.TRANSLATION_DICT:
            return self.TRANSLATION_DICT[german_text]
        
        # 3. Try word-by-word from both sources
        words = german_text.split()
        translated_words = []
        for word in words:
            if word in self.cache:
                translated_words.append(self.cache[word])
            elif word in self.TRANSLATION_DICT:
                translated_words.append(self.TRANSLATION_DICT[word])
            else:
                translated_words.append(word)
        
        return ' '.join(translated_words)
    
    def translate_category(self, category: OekobaudatCategory) -> OekobaudatCategory:
        """Translate a category"""
        category.name_en = self.translate(category.name_de)
        
        # Translate path
        path_parts = category.full_path_de.split('/')
        translated_parts = [self.translate(part) for part in path_parts]
        category.full_path_en = '/'.join(translated_parts)
        
        return category


def main():
    """Main execution"""
    print("=" * 80)
    print("Ökobaudat RDF Builder - OWL Edition")
    print("=" * 80)
    
    # Configuration
    XML_PATH = "Mapping/OEKOBAUDAT Product Categories.xml"
    OUTPUT_RDF = "Mapping/oekobaudat_owl.ttl"
    OUTPUT_JSON = "Mapping/oekobaudat_translated.json"
    CACHE_PATH = "Mapping/oekobaudat_translation_cache.json"
    
    # Build RDF
    builder = OekobaudatRdfBuilder(XML_PATH)
    
    # Parse first
    builder.parse_xml()
    print(f"  Parsed {len(builder.categories)} categories")
    
    # Translate
    print("\nTranslating categories...")
    translator = AutoTranslator(cache_path=CACHE_PATH)
    for cat in builder.categories.values():
        translator.translate_category(cat)
    print("  Translated categories")
    
    # Build graph
    print("\nBuilding OWL ontology...")
    for cat_id in builder.categories.keys():
        builder.add_category_to_graph(cat_id)
    print(f"  Created {len(builder.categories)} OWL classes")
    print(f"  Total triples: {len(builder.graph)}")
    
    # Serialize
    print("\nSaving outputs...")
    builder.serialize(OUTPUT_RDF)
    builder.export_for_translation(OUTPUT_JSON)
    
    # Show examples
    print("\n" + "=" * 80)
    print("Example OWL Classes (first 5):")
    print("=" * 80)
    
    for i, cat in enumerate(list(builder.categories.values())[:5], 1):
        class_name = builder._name_to_class_name(cat.name_de)
        print(f"\n{i}. obd:{class_name}")
        print(f"   rdfs:label \"{cat.name_de}\"@de")
        if cat.name_en:
            print(f"   rdfs:label \"{cat.name_en}\"@en")
        print(f"   obd:okobaudatCategory oekocat:{cat.id}")
        if cat.parent_id:
            parent = builder.categories.get(cat.parent_id)
            if parent:
                parent_class = builder._name_to_class_name(parent.name_de)
                print(f"   rdfs:subClassOf obd:{parent_class}")
    
    print("\n" + "=" * 80)
    print("Complete! Now use SKOS only for mapping (next step)")
    print("=" * 80)


if __name__ == "__main__":
    main()
