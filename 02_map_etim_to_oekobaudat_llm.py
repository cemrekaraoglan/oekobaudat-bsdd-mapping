#!/usr/bin/env python3
"""
STEP 02: Map ETIM Entries to Ökobaudat RDF Graph (LLM Method)

Uses Azure OpenAI to match English ETIM entries to German Ökobaudat categories.
Outputs SKOS relationships: exactMatch, closeMatch, relatedMatch, noMatch.

No translation needed - LLM understands both languages natively.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import SKOS, RDF, RDFS, DCTERMS
import json
import time

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False


@dataclass
class OekobaudatCategory:
    """Ökobaudat category (German only, no translation needed)"""
    id: str
    name_de: str
    parent_id: Optional[str]
    full_path_de: str
    uri: str


@dataclass
class BsddClass:
    """bsDD class entry"""
    uri: str
    code: str
    name: str
    definition: str
    domain_namespace: str


@dataclass
class Mapping:
    """Mapping with LLM reasoning"""
    bsdd_class: BsddClass
    oekobaudat_category: OekobaudatCategory
    match_type: str
    confidence_score: float
    reasoning: str
    method: str = "llm-only"


class OekobaudatParser:
    """Parses Ökobaudat XML (German only)"""
    
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.categories: List[OekobaudatCategory] = []
        
    def parse(self) -> List[OekobaudatCategory]:
        """Parse the XML and extract categories"""
        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        
        ns = {
            'ns2': 'http://lca.jrc.it/ILCD/Categories',
            'common': 'http://lca.jrc.it/ILCD/Common'
        }
        
        categories_elem = root.find('.//ns2:categories[@dataType="Process"]', ns)
        if categories_elem is not None:
            self._parse_categories(categories_elem, ns, None, "")
        
        return self.categories
    
    def _parse_categories(self, parent_elem, ns, parent_id, parent_path):
        """Recursively parse category hierarchy"""
        for category in parent_elem.findall('ns2:category', ns):
            cat_id = category.get('id')
            cat_name_de = category.get('name')
            
            full_path_de = f"{parent_path}/{cat_name_de}" if parent_path else cat_name_de
            
            cat_obj = OekobaudatCategory(
                id=cat_id,
                name_de=cat_name_de,
                parent_id=parent_id,
                full_path_de=full_path_de,
                uri=f"https://oekobaudat.de/category/{cat_id}"
            )
            self.categories.append(cat_obj)
            
            self._parse_categories(category, ns, cat_id, full_path_de)


class BsddClient:
    """Client for bsDD API"""
    
    def __init__(self, base_url: str = "https://api.bsdd.buildingsmart.org"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'bsDD-Oekobaudat-Mapper-LLM/1.0',
            'Accept': 'application/json'
        })
    
    def get_domains(self) -> List[Dict]:
        """Get available domains"""
        url = f"{self.base_url}/api/Domain/v4"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_all_classes(self, domain_namespace: str, limit: int = 1000) -> List[BsddClass]:
        """Get all classes from domain"""
        url = f"{self.base_url}/api/Class/v4/search"
        params = {
            'DomainNamespaceUri': domain_namespace,
            'SearchText': '',
            'LanguageCode': 'en',
            'Limit': limit
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        bsdd_classes = []
        for cls in data.get('classes', []):
            bsdd_class = BsddClass(
                uri=cls.get('uri', ''),
                code=cls.get('code', ''),
                name=cls.get('name', ''),
                definition=cls.get('definition', ''),
                domain_namespace=domain_namespace
            )
            bsdd_classes.append(bsdd_class)
        
        return bsdd_classes


class LLMOnlyMatcher:
    """Uses LLM to match English ETIM to German Ökobaudat directly"""
    
    def __init__(self, endpoint: str, api_key: str, deployment: str):
        """Initialize Azure OpenAI matcher"""
        if not AZURE_OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-04-01-preview"  # Updated for GPT-5-mini
        )
        self.deployment = deployment
    
    def create_prompt(self, bsdd_class: BsddClass, 
                     candidates: List[OekobaudatCategory]) -> str:
        """Create prompt for LLM (English input, German categories)"""
        
        candidates_text = "\n".join([
            f"{i+1}. ID: {cat.id}\n   Name (German): {cat.name_de}\n   Path: {cat.full_path_de}"
            for i, cat in enumerate(candidates[:10])  # Top 10 only
        ])
        
        prompt = f"""You are an expert in building materials and construction product classification.

Your task: Match this English building product to the most appropriate German Ökobaudat category.

ENGLISH PRODUCT (from ETIM):
Name: {bsdd_class.name}
Definition: {bsdd_class.definition if bsdd_class.definition else "Not provided"}

GERMAN ÖKOBAUDAT CATEGORIES (choose from):
{candidates_text}

Instructions:
1. Understand both the English product and ILCD product category names in German
2. Match based on actual material type and use case
3. Determine confidence (0.0-1.0) - be realistic!
4. Choose match type:
   - exactMatch (0.9-1.0): Same concept
   - closeMatch (0.7-0.89): Very similar
   - relatedMatch (0.5-0.69): Related
   - noMatch (<0.5): No good match

Respond ONLY with valid JSON:
{{
  "category_id": "selected ID",
  "confidence": 0.85,
  "match_type": "exactMatch",
  "reasoning": "Brief explanation"
}}"""

        return prompt
    
    def query_llm(self, prompt: str) -> str:
        """Query Azure OpenAI"""
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": "You are a building materials expert. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            # temperature not supported in GPT-5-mini, uses default (1.0)
            max_completion_tokens=500,  # Updated for GPT-5-mini
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    def create_mapping(self, bsdd_class: BsddClass, 
                      categories: List[OekobaudatCategory], 
                      debug: bool = False) -> Optional[Mapping]:
        """Create mapping using LLM"""
        
        # Create prompt
        prompt = self.create_prompt(bsdd_class, categories)
        
        try:
            # Query LLM
            response = self.query_llm(prompt)
            
            # Debug: Show raw response
            if debug:
                print(f"\n  DEBUG - Raw LLM response:")
                print(f"  {response[:200]}..." if len(response) > 200 else f"  {response}")
            
            # Check if response is empty
            if not response or not response.strip():
                print(f"  ⚠️  Error: LLM returned empty response")
                return None
            
            result = json.loads(response.strip())
            
            # Find the category
            category = next((c for c in categories if c.id == result['category_id']), None)
            if not category:
                print(f"  ⚠️  LLM returned unknown category ID: {result['category_id']}")
                return None
            
            # Check confidence threshold (minimum 0.5 for meaningful matches)
            confidence = float(result['confidence'])
            if confidence < 0.5:
                print(f"  ⚠️  Low confidence ({confidence:.2f}) - marked as noMatch")
                # Still create mapping but mark as noMatch
                return Mapping(
                    bsdd_class=bsdd_class,
                    oekobaudat_category=category,
                    match_type='noMatch',
                    confidence_score=confidence,
                    reasoning=result['reasoning'],
                    method="llm-only"
                )
            
            return Mapping(
                bsdd_class=bsdd_class,
                oekobaudat_category=category,
                match_type=result.get('match_type', 'closeMatch'),
                confidence_score=confidence,
                reasoning=result['reasoning'],
                method="llm-only"
            )
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON Error: Invalid response format - {str(e)[:50]}")
            return None
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            return None


class RdfGenerator:
    """Generates SKOS-compliant RDF"""
    
    def __init__(self):
        self.graph = Graph()
        
        self.BSDD = Namespace("https://identifier.buildingsmart.org/uri/")
        self.OEKOBAUDAT = Namespace("https://oekobaudat.de/category/")
        
        self.graph.bind("skos", SKOS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("bsdd", self.BSDD)
        self.graph.bind("oekobaudat", self.OEKOBAUDAT)
    
    def add_mapping(self, mapping: Mapping):
        """Add SKOS mapping"""
        if not mapping:
            return
        
        bsdd_uri = URIRef(mapping.bsdd_class.uri) if mapping.bsdd_class.uri else URIRef(
            f"{self.BSDD}{mapping.bsdd_class.domain_namespace}/class/{mapping.bsdd_class.code}"
        )
        
        oeko_uri = URIRef(mapping.oekobaudat_category.uri)
        
        # Add bsDD class
        self.graph.add((bsdd_uri, RDF.type, SKOS.Concept))
        self.graph.add((bsdd_uri, SKOS.prefLabel, Literal(mapping.bsdd_class.name, lang='en')))
        self.graph.add((bsdd_uri, SKOS.notation, Literal(mapping.bsdd_class.code)))
        
        # Add mapping relationship (SKOS standard + custom noMatch)
        if mapping.match_type == 'exactMatch':
            self.graph.add((bsdd_uri, SKOS.exactMatch, oeko_uri))
        elif mapping.match_type == 'closeMatch':
            self.graph.add((bsdd_uri, SKOS.closeMatch, oeko_uri))
        elif mapping.match_type == 'relatedMatch':
            self.graph.add((bsdd_uri, SKOS.related, oeko_uri))
        elif mapping.match_type == 'noMatch':
            # Custom property for negative matches (not in SKOS standard)
            self.graph.add((bsdd_uri, URIRef(str(self.BSDD) + "noMatch"), oeko_uri))
            self.graph.add((bsdd_uri, RDFS.comment, Literal(f"No good match found. Best candidate: {mapping.oekobaudat_category.name_de}")))
    
    def serialize(self, output_path: str, format: str = 'turtle'):
        """Serialize graph"""
        self.graph.serialize(destination=output_path, format=format)


def main():
    """Main execution"""
    print("=" * 80)
    print("bsDD to Ökobaudat Mapper")
    print("=" * 80)
    
    # Configuration
    OEKOBAUDAT_XML = "Mapping/OEKOBAUDAT Product Categories.xml"
    OUTPUT_RDF = "Mapping/etim_oekobaudat_mappings.ttl"
    OUTPUT_JSON = "Mapping/etim_oekobaudat_mappings.json"
        
    # Azure OpenAI credentials (from environment variables)
    from utils.config import get_azure_config
    
    try:
        azure_config = get_azure_config()
        AZURE_ENDPOINT = azure_config['endpoint']
        AZURE_KEY = azure_config['api_key']
        AZURE_DEPLOYMENT = azure_config['deployment']
        print(f"   Using Azure OpenAI: {AZURE_DEPLOYMENT}")
    except ValueError as e:
        print(f"   ERROR: {e}")
        print("   Please set up your .env file (see env.example)")
        return
    
    # Step 1: Parse German Ökobaudat (no translation!)
    print("\n[1/4] Loading German Ökobaudat categories...")
    parser = OekobaudatParser(OEKOBAUDAT_XML)
    categories = parser.parse()
    print(f"   Loaded {len(categories)} categories")
    
    # Step 2: Fetch ETIM from bsDD API
    print("\n[2/4] Fetching ETIM classes from bsDD API...")
    from utils.bsdd_api_client import BsddApiClient
    
    try:
        # Initialize API client (production)
        api_client = BsddApiClient(use_test=False)
        
        # Fetch ETIM classes - Building Materials only (EC00* codes)
        # ETIM sectors:
        #   - EC00*: Building materials (Baustoffe)
        #   - EC01*: Electrotechnical (Elektrotechnik)
        #   - etc.
        print("   Filtering: Building Materials sector only (EC00)")
        bsdd_classes = api_client.get_etim_classes(filter_category="EC00")
        
        # Optional: Limit for testing
        # bsdd_classes = bsdd_classes[:50]
        
        if not bsdd_classes:
            print("   ERROR: No classes retrieved from bsDD API")
            print("   Check internet connection or API status")
            print("   Tip: Remove filter_category to get all sectors")
            return
            
    except Exception as e:
        print(f"   ERROR: {e}")
        print("   Tip: Use LocalEtimLoader as fallback for offline work")
        return
    
    # Step 3: LLM matching (English ETIM → German Ökobaudat)
    print("\n[3/4] LLM matching...")
    print("   Note: Showing debug output for first 10 items to inspect LLM responses\n")
    
    matcher = LLMOnlyMatcher(AZURE_ENDPOINT, AZURE_KEY, AZURE_DEPLOYMENT)
    
    mappings = []
    for i, cls in enumerate(bsdd_classes, 1):
        print(f"   [{i}/{len(bsdd_classes)}] {cls.name}")
        
        # Enable debug for first 10 items to see what LLM returns
        debug_mode = (i <= 10)
        mapping = matcher.create_mapping(cls, categories, debug=debug_mode)
        
        if mapping:
            mappings.append(mapping)
            print(f"      → {mapping.oekobaudat_category.name_de} ({mapping.confidence_score:.2f})")
        
        # Rate limiting
        if i < len(bsdd_classes):
            time.sleep(0.5)
    
    print(f"\n   Created {len(mappings)} mappings")
    
    # Statistics
    match_types = {}
    for mapping in mappings:
        match_types[mapping.match_type] = match_types.get(mapping.match_type, 0) + 1
    
    print("\n   Match type distribution:")
    for match_type, count in sorted(match_types.items()):
        print(f"   - {match_type}: {count}")
    
    avg_conf = sum(m.confidence_score for m in mappings) / len(mappings) if mappings else 0
    print(f"\n   Average confidence: {avg_conf:.3f}")
    
    # Step 4: Generate outputs
    print("\n[4/4] Generating outputs...")
    
    # RDF (SKOS format)
    rdf_gen = RdfGenerator()
    for mapping in mappings:
        rdf_gen.add_mapping(mapping)
    rdf_gen.serialize(OUTPUT_RDF)
    print(f"   RDF (SKOS): {OUTPUT_RDF}")
    
    # JSON
    json_report = []
    for mapping in mappings:
        json_report.append({
            'bsdd': {
                'uri': mapping.bsdd_class.uri,
                'code': mapping.bsdd_class.code,
                'name': mapping.bsdd_class.name,
                'definition': mapping.bsdd_class.definition
            },
            'oekobaudat': {
                'id': mapping.oekobaudat_category.id,
                'name_de': mapping.oekobaudat_category.name_de,
                'path_de': mapping.oekobaudat_category.full_path_de
            },
            'match_type': mapping.match_type,
            'confidence': mapping.confidence_score,
            'reasoning': mapping.reasoning,
            'method': 'llm-only'
        })
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    print(f"   JSON: {OUTPUT_JSON}")
    
    # Examples
    print("\n" + "=" * 80)
    print("Example Mappings (top 10):")
    print("=" * 80)
    
    sorted_mappings = sorted(mappings, key=lambda x: x.confidence_score, reverse=True)[:10]
    for i, m in enumerate(sorted_mappings, 1):
        print(f"\n{i}. {m.bsdd_class.name} (English)")
        print(f"   → {m.oekobaudat_category.name_de} (German)")
        print(f"   Match: {m.match_type} ({m.confidence_score:.2f})")
        print(f"   Reason: {m.reasoning}")
    
    print("\n" + "=" * 80)
    print("✓ LLM-only mapping complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

