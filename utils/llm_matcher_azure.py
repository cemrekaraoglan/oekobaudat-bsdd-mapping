#!/usr/bin/env python3
"""
Azure OpenAI-based Semantic Matcher

Enhanced LLM matcher with Azure OpenAI support for comparing with SKOS matching.
"""

import json
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False


@dataclass
class LLMMatchResult:
    """Result from LLM matching"""
    category_id: str
    category_name: str
    confidence: float
    reasoning: str
    match_type: str  # 'exactMatch', 'closeMatch', 'relatedMatch', 'noMatch'


class AzureOpenAIMatcher:
    """Semantic matcher using Azure OpenAI"""
    
    def __init__(self, endpoint: str, api_key: str, deployment: str, 
                 api_version: str = "2025-04-01-preview"):
        """
        Initialize Azure OpenAI matcher
        
        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            deployment: Deployment name (e.g., 'gpt-5-mini')
            api_version: API version (default: 2025-04-01-preview for GPT-5)
        """
        if not AZURE_OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment = deployment
    
    def create_prompt(self, bsdd_class_name: str, bsdd_definition: str,
                     oekobaudat_categories: List[Tuple[str, str, str, str]]) -> str:
        """
        Create a prompt for Azure OpenAI
        
        Args:
            bsdd_class_name: Name of the bsDD class (English)
            bsdd_definition: Definition of the bsDD class
            oekobaudat_categories: List of (id, name_de, name_en, full_path_en) tuples
        """
        categories_text = "\n".join([
            f"{i+1}. ID: {cat[0]}\n   German: {cat[1]}\n   English: {cat[2]}\n   Path: {cat[3]}"
            for i, cat in enumerate(oekobaudat_categories)
        ])
        
        prompt = f"""You are an expert in building materials and construction product classification systems.

Your task is to find the best matching Ökobaudat category for the following building product from ETIM:

Product Name (ETIM): {bsdd_class_name}
Definition: {bsdd_definition if bsdd_definition else "Not provided"}

Available Ökobaudat categories (top candidates):
{categories_text}

Please analyze semantically and determine:
1. Which category is the BEST match based on the product's actual use and material type?
2. Your confidence level (0.0 to 1.0 - be realistic, not all matches are perfect)
3. The match type according to SKOS:
   - exactMatch (0.9-1.0): Semantically identical concepts
   - closeMatch (0.7-0.89): Very similar, same product category
   - relatedMatch (0.5-0.69): Related but different specific products
   - noMatch (<0.5): No meaningful relationship
4. Your reasoning

Respond ONLY with valid JSON in this exact format:
{{
  "category_id": "selected category ID",
  "category_name": "selected category name in English",
  "confidence": 0.85,
  "match_type": "exactMatch",
  "reasoning": "Brief explanation of why this is the best match"
}}

Consider:
- The actual material type and use case
- Building construction domain knowledge
- Both English and German category names
- The hierarchical context (full path)
- Be conservative with confidence scores - only use >0.9 for truly identical concepts"""

        return prompt
    
    def query_azure_openai(self, prompt: str) -> str:
        """Query Azure OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a building materials classification expert. Always respond with valid JSON only."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}  # Ensures JSON output
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error querying Azure OpenAI: {e}")
            raise
    
    def find_best_match_llm(self, bsdd_class_name: str, bsdd_definition: str,
                           oekobaudat_categories: List[Tuple[str, str, str, str]],
                           top_n: int = 10) -> Optional[LLMMatchResult]:
        """
        Use Azure OpenAI to find the best matching category
        
        Args:
            bsdd_class_name: Name of the bsDD class
            bsdd_definition: Definition of the bsDD class
            oekobaudat_categories: List of (id, name_de, name_en, full_path_en) tuples
            top_n: Number of top candidates to present to LLM
        
        Returns:
            LLMMatchResult or None if no match found
        """
        # Limit to top N candidates
        candidates = oekobaudat_categories[:top_n]
        
        # Create prompt
        prompt = self.create_prompt(bsdd_class_name, bsdd_definition, candidates)
        
        # Query LLM
        try:
            response_text = self.query_azure_openai(prompt)
            
            # Parse JSON response
            response_text = response_text.strip()
            
            # Handle markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(response_text)
            
            return LLMMatchResult(
                category_id=result["category_id"],
                category_name=result["category_name"],
                confidence=float(result["confidence"]),
                match_type=result.get("match_type", "closeMatch"),  # Default if not provided
                reasoning=result["reasoning"]
            )
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response_text}")
            return None
        except Exception as e:
            print(f"Error in LLM matching: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Azure OpenAI credentials (from environment variables)
    from .config import get_azure_config
    azure_config = get_azure_config()
    AZURE_OPENAI_ENDPOINT = azure_config['endpoint']
    AZURE_OPENAI_API_KEY = azure_config['api_key']
    AZURE_OPENAI_DEPLOYMENT = azure_config['deployment']
    
    # Initialize matcher
    matcher = AzureOpenAIMatcher(
        endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        deployment=AZURE_OPENAI_DEPLOYMENT
    )
    
    # Example bsDD class
    bsdd_name = "Gypsum board"
    bsdd_def = "A board made of gypsum plaster pressed between two thick sheets of paper, used for interior walls and ceilings"
    
    # Example Ökobaudat categories (id, name_de, name_en, full_path_en)
    categories = [
        ("1.3.13", "Gipsplatten", "Gypsum Board", "Mineral Building Materials/Bricks and Elements/Gypsum Board"),
        ("1.3.14", "Trockenestrich", "Dry Screed", "Mineral Building Materials/Bricks and Elements/Dry Screed"),
        ("1.3.15", "Deckenplatten", "Ceiling Panels", "Mineral Building Materials/Bricks and Elements/Ceiling Panels"),
        ("1.3.18", "Brandschutzplatten", "Fire Protection Boards", "Mineral Building Materials/Bricks and Elements/Fire Protection Boards"),
        ("1.1.03", "Gips", "Gypsum", "Mineral Building Materials/Binders/Gypsum"),
    ]
    
    # Find match
    print("Testing Azure OpenAI Matcher...")
    print(f"Product: {bsdd_name}")
    print(f"Definition: {bsdd_def}")
    print("\nQuerying Azure OpenAI...\n")
    
    result = matcher.find_best_match_llm(bsdd_name, bsdd_def, categories)
    
    if result:
        print("=" * 80)
        print("Azure OpenAI Match Result:")
        print("=" * 80)
        print(f"Category: {result.category_name} (ID: {result.category_id})")
        print(f"Match Type: {result.match_type}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning: {result.reasoning}")
        print("=" * 80)
    else:
        print("No match found")


