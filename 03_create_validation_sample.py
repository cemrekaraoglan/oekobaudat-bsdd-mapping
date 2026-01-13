#!/usr/bin/env python3
"""
STEP 03: Create Validation Sample

Generates a sample of products for manual annotation to create a ground truth dataset.
This allows you to measure actual accuracy of the mapping results from Step 02.

NOTE: This script needs to be updated to work with the new workflow.
      Implementation details will be provided later.
"""

import json
import random
# TODO: Update imports to work with new LLM mapper structure
# from etim_local_loader import EtimLocalLoader
# Load from Step 02 output: etim_oekobaudat_mappings.json


def create_validation_sample(bsdd_classes, categories, sample_size=50, stratified=True):
    """
    Create a validation sample for manual annotation
    
    Args:
        bsdd_classes: List of bsDD classes
        categories: List of Ökobaudat categories
        sample_size: Number of products to sample
        stratified: Whether to stratify by confidence level
    """
    
    if stratified:
        # Get confidence scores for stratification
        matcher = MultilingualSemanticMatcher()
        
        print("Calculating confidence scores for stratification...")
        scored_classes = []
        for i, cls in enumerate(bsdd_classes):
            if i % 50 == 0:
                print(f"  {i}/{len(bsdd_classes)}...")
            
            mapping = matcher.create_mapping(cls, categories)
            if mapping:
                scored_classes.append((cls, mapping.confidence_score))
        
        # Stratify by confidence
        high_conf = [c for c, s in scored_classes if s >= 0.8]
        medium_conf = [c for c, s in scored_classes if 0.5 <= s < 0.8]
        low_conf = [c for c, s in scored_classes if s < 0.5]
        
        print(f"\nConfidence distribution:")
        print(f"  High (>=0.8): {len(high_conf)}")
        print(f"  Medium (0.5-0.8): {len(medium_conf)}")
        print(f"  Low (<0.5): {len(low_conf)}")
        
        # Sample proportionally
        n_high = min(len(high_conf), sample_size // 2)
        n_medium = min(len(medium_conf), sample_size // 3)
        n_low = min(len(low_conf), sample_size - n_high - n_medium)
        
        sample = (
            random.sample(high_conf, n_high) +
            random.sample(medium_conf, n_medium) +
            random.sample(low_conf, n_low)
        )
        
        print(f"\nSampled: {n_high} high + {n_medium} medium + {n_low} low = {len(sample)}")
    else:
        # Simple random sample
        sample = random.sample(bsdd_classes, min(sample_size, len(bsdd_classes)))
    
    return sample


def export_for_annotation(sample, categories, output_file='validation_sample.json'):
    """Export sample with top candidates for easier annotation"""
    
    matcher = MultilingualSemanticMatcher()
    
    validation_data = []
    
    print(f"\nPreparing {len(sample)} products for annotation...")
    for i, cls in enumerate(sample, 1):
        print(f"  [{i}/{len(sample)}] {cls.name}")
        
        # Get top 5 candidates to help annotator
        top_matches = matcher.find_best_matches(cls, categories, top_n=5)
        
        candidates = []
        for cat, score, lang in top_matches:
            candidates.append({
                'id': cat.id,
                'name_en': cat.name_en,
                'name_de': cat.name_de,
                'path_en': cat.full_path_en,
                'confidence': round(score, 3)
            })
        
        validation_data.append({
            'code': cls.code,
            'name': cls.name,
            'definition': cls.definition,
            'uri': cls.uri,
            
            # Top candidates to help with annotation
            'suggested_candidates': candidates,
            
            # To be filled manually:
            'correct_oekobaudat_id': '',
            'correct_category_name': '',
            'confidence_level': '',  # 'certain', 'likely', 'unclear'
            'notes': '',
            'ambiguous': False,
            'annotator': ''
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validation_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Validation sample saved to: {output_file}")
    print("\nNext steps:")
    print("1. Open the JSON file")
    print("2. For each product, fill in:")
    print("   - correct_oekobaudat_id (e.g., '1.3.13')")
    print("   - correct_category_name (e.g., 'Gypsum Board')")
    print("   - confidence_level ('certain', 'likely', or 'unclear')")
    print("   - notes (optional - explain your reasoning)")
    print("   - ambiguous (true if multiple categories could be correct)")
    print("3. Run: python validate_accuracy.py")


def main():
    """Main execution"""
    
    print("=" * 80)
    print("Create Validation Sample")
    print("=" * 80)
    
    # Configuration
    SAMPLE_SIZE = 50
    OUTPUT_FILE = "validation_sample.json"
    ETIM_NAMESPACE = "https://identifier.buildingsmart.org/uri/etim/etim-9.0"
    
    # Load Ökobaudat
    print("\n[1/3] Loading Ökobaudat categories...")
    from bsdd_oekobaudat_mapper_v2 import MultilingualOekobaudatLoader
    
    loader = MultilingualOekobaudatLoader("Mapping/oekobaudat_multilingual.ttl")
    categories = loader.load()
    print(f"  Loaded {len(categories)} categories")
    
    # Fetch bsDD classes
    print("\n[2/3] Fetching bsDD classes...")
    client = BsddClient()
    
    try:
        domains = client.get_domains()
        etim_domain = None
        for domain in domains:
            if 'etim' in domain.get('namespaceUri', '').lower():
                etim_domain = domain.get('namespaceUri')
                break
        
        if etim_domain:
            ETIM_NAMESPACE = etim_domain
        
        bsdd_classes = client.get_all_classes(ETIM_NAMESPACE, limit=500)
        print(f"  Fetched {len(bsdd_classes)} classes")
    
    except Exception as e:
        print(f"  Error: {e}")
        return
    
    # Create sample
    print(f"\n[3/3] Creating validation sample (n={SAMPLE_SIZE})...")
    
    stratified = input("  Use stratified sampling by confidence? (y/n): ").lower() == 'y'
    
    sample = create_validation_sample(
        bsdd_classes, 
        categories, 
        sample_size=SAMPLE_SIZE,
        stratified=stratified
    )
    
    # Export
    export_for_annotation(sample, categories, OUTPUT_FILE)
    
    print("\n" + "=" * 80)
    print("Sample created successfully!")
    print("=" * 80)
    print(f"\nFile: {OUTPUT_FILE}")
    print(f"Products: {len(sample)}")
    print("\nAnnotation tips:")
    print("- Use the suggested_candidates to guide you")
    print("- Search Ökobaudat website if unsure")
    print("- Mark ambiguous cases as ambiguous=true")
    print("- Add notes for tricky decisions")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()


