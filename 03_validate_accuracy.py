#!/usr/bin/env python3
"""
STEP 03: Validate Accuracy Against Ground Truth

Measures actual accuracy of LLM mapping (from Step 02) against manually annotated validation dataset.
Provides precision, recall, and F1 scores.

NOTE: This script needs to be updated to work with the new workflow.
      Implementation details will be provided later.
"""

import json
from collections import defaultdict
# TODO: Update imports to work with new LLM mapper structure
# from etim_local_loader import EtimLocalLoader
# Load from Step 02 output: etim_oekobaudat_mappings.json
# Load from validation sample: validation_sample.json (manually annotated)

try:
    from llm_matcher_azure import AzureOpenAIMatcher
    LLM_AVAILABLE = True
except:
    LLM_AVAILABLE = False


def load_validation_data(file_path='validation_sample.json'):
    """Load annotated validation dataset"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if annotated
    unannotated = [d for d in data if not d.get('correct_oekobaudat_id')]
    if unannotated:
        print(f"⚠️  Warning: {len(unannotated)}/{len(data)} products not yet annotated")
        print("   Only validating annotated products")
    
    # Return only annotated products
    annotated = [d for d in data if d.get('correct_oekobaudat_id')]
    return annotated


def evaluate_method(method_name, predictions, ground_truth):
    """Evaluate a method against ground truth"""
    
    total = len(ground_truth)
    correct = 0
    errors = []
    
    # Create lookup
    gt_dict = {v['code']: v['correct_oekobaudat_id'] for v in ground_truth}
    
    for pred in predictions:
        code = pred.bsdd_class.code if hasattr(pred, 'bsdd_class') else pred.get('code')
        
        if code in gt_dict:
            predicted_id = pred.oekobaudat_category.id if hasattr(pred, 'oekobaudat_category') else pred.get('oekobaudat_category_id')
            actual_id = gt_dict[code]
            
            if predicted_id == actual_id:
                correct += 1
            else:
                errors.append({
                    'code': code,
                    'predicted': predicted_id,
                    'actual': actual_id,
                    'confidence': pred.confidence_score if hasattr(pred, 'confidence_score') else pred.get('confidence', 0)
                })
    
    accuracy = correct / total if total > 0 else 0
    
    print(f"\n{method_name} Results:")
    print(f"  Correct: {correct}/{total}")
    print(f"  Accuracy: {accuracy:.1%}")
    
    # Error analysis
    if errors:
        low_conf = [e for e in errors if e['confidence'] < 0.7]
        high_conf = [e for e in errors if e['confidence'] >= 0.7]
        
        print(f"  Errors with confidence <0.7: {len(low_conf)}")
        print(f"  Errors with confidence >=0.7: {len(high_conf)} ⚠️")
    
    return accuracy, errors


def compare_methods(skos_predictions, llm_predictions, ground_truth):
    """Compare SKOS vs LLM on same validation set"""
    
    print("\n" + "=" * 80)
    print("Method Comparison")
    print("=" * 80)
    
    skos_acc, skos_errors = evaluate_method("SKOS", skos_predictions, ground_truth)
    llm_acc, llm_errors = evaluate_method("LLM", llm_predictions, ground_truth)
    
    diff = llm_acc - skos_acc
    print(f"\n{'LLM' if diff > 0 else 'SKOS'} is better by {abs(diff):.1%}")
    
    # Analyze disagreements
    print("\n" + "=" * 80)
    print("Where They Differ")
    print("=" * 80)
    
    gt_dict = {v['code']: v['correct_oekobaudat_id'] for v in ground_truth}
    
    skos_dict = {p.bsdd_class.code: p.oekobaudat_category.id for p in skos_predictions}
    llm_dict = {p.bsdd_class.code: p.oekobaudat_category.id for p in llm_predictions}
    
    both_correct = 0
    both_wrong = 0
    only_skos = 0
    only_llm = 0
    
    for code, correct_id in gt_dict.items():
        skos_pred = skos_dict.get(code)
        llm_pred = llm_dict.get(code)
        
        skos_correct = (skos_pred == correct_id)
        llm_correct = (llm_pred == correct_id)
        
        if skos_correct and llm_correct:
            both_correct += 1
        elif not skos_correct and not llm_correct:
            both_wrong += 1
        elif skos_correct:
            only_skos += 1
        elif llm_correct:
            only_llm += 1
    
    print(f"Both correct: {both_correct}")
    print(f"Only SKOS correct: {only_skos}")
    print(f"Only LLM correct: {only_llm}")
    print(f"Both wrong: {both_wrong}")
    
    # Conclusion
    print("\n" + "=" * 80)
    print("Recommendation")
    print("=" * 80)
    
    if diff > 0.10:
        print("✓ LLM is significantly more accurate (+10pp)")
        print("  → Use LLM by default")
    elif diff > 0.05:
        print("✓ LLM is moderately more accurate (+5pp)")
        print("  → Consider hybrid: SKOS first, LLM if confidence < 0.7")
    elif diff > -0.05:
        print("✓ Both methods are comparable")
        print("  → Use SKOS (faster, cheaper)")
    else:
        print("✓ SKOS is more accurate")
        print("  → Use SKOS")


def main():
    """Main execution"""
    
    print("=" * 80)
    print("Validate Accuracy Against Ground Truth")
    print("=" * 80)
    
    # Configuration
    VALIDATION_FILE = "validation_sample.json"
    VALIDATE_LLM = False  # Set to True to also validate LLM
    
    # Azure OpenAI credentials (from environment variables)
    from utils.config import get_azure_config
    azure_config = get_azure_config()
    AZURE_ENDPOINT = azure_config['endpoint']
    AZURE_KEY = azure_config['api_key']
    AZURE_DEPLOYMENT = azure_config['deployment']
    
    # Check if LLM validation requested
    if input("\nValidate LLM method too? (costs ~$0.10 for 50 products) (y/n): ").lower() == 'y':
        VALIDATE_LLM = True
        if not LLM_AVAILABLE:
            print("❌ LLM matcher not available. Install: pip install openai")
            VALIDATE_LLM = False
    
    # Load validation data
    print(f"\n[1/4] Loading validation dataset: {VALIDATION_FILE}")
    try:
        validation_data = load_validation_data(VALIDATION_FILE)
        print(f"  Loaded {len(validation_data)} annotated products")
    except FileNotFoundError:
        print(f"❌ Validation file not found: {VALIDATION_FILE}")
        print("   Run: python create_validation_sample.py first")
        return
    except Exception as e:
        print(f"❌ Error loading validation data: {e}")
        return
    
    # Load Ökobaudat
    print("\n[2/4] Loading Ökobaudat categories...")
    loader = MultilingualOekobaudatLoader("Mapping/oekobaudat_multilingual.ttl")
    categories = loader.load()
    
    # Create bsDD class objects from validation data
    print("\n[3/4] Creating bsDD class objects...")
    bsdd_classes = []
    for v in validation_data:
        cls = BsddClass(
            uri=v['uri'],
            code=v['code'],
            name=v['name'],
            definition=v['definition'],
            domain_namespace="etim"
        )
        bsdd_classes.append(cls)
    
    # Run SKOS matching
    print("\n[4/4] Running validation...")
    print("\n--- SKOS Method ---")
    skos_matcher = MultilingualSemanticMatcher()
    skos_predictions = []
    
    for i, cls in enumerate(bsdd_classes, 1):
        if i % 10 == 0:
            print(f"  {i}/{len(bsdd_classes)}...")
        mapping = skos_matcher.create_mapping(cls, categories)
        if mapping:
            skos_predictions.append(mapping)
    
    skos_accuracy, skos_errors = evaluate_method("SKOS", skos_predictions, validation_data)
    
    # Run LLM matching if requested
    if VALIDATE_LLM:
        print("\n--- LLM Method ---")
        llm_matcher = AzureOpenAIMatcher(AZURE_ENDPOINT, AZURE_KEY, AZURE_DEPLOYMENT)
        llm_predictions = []
        
        for i, cls in enumerate(bsdd_classes, 1):
            print(f"  {i}/{len(bsdd_classes)}...")
            
            # Get candidates from SKOS
            candidates = skos_matcher.find_best_matches(cls, categories, top_n=10)
            llm_candidates = [(c.id, c.name_de, c.name_en, c.full_path_en) 
                            for c, _, _ in candidates]
            
            result = llm_matcher.find_best_match_llm(
                cls.name, cls.definition, llm_candidates
            )
            
            if result:
                # Convert to mapping-like object
                class LLMMapping:
                    def __init__(self, cls, result):
                        self.bsdd_class = cls
                        class OekoCategory:
                            def __init__(self, cat_id):
                                self.id = cat_id
                        self.oekobaudat_category = OekoCategory(result.category_id)
                        self.confidence_score = result.confidence
                
                llm_predictions.append(LLMMapping(cls, result))
        
        llm_accuracy, llm_errors = evaluate_method("LLM", llm_predictions, validation_data)
        
        # Compare
        compare_methods(skos_predictions, llm_predictions, validation_data)
    
    else:
        # Just SKOS results
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"SKOS Accuracy: {skos_accuracy:.1%}")
        
        if skos_accuracy >= 0.8:
            print("\n✓ SKOS performs well (>80% accuracy)")
        elif skos_accuracy >= 0.6:
            print("\n⚠️  SKOS moderate performance (60-80% accuracy)")
            print("   Consider trying LLM method")
        else:
            print("\n❌ SKOS low performance (<60% accuracy)")
            print("   Definitely try LLM method or improve translations")
    
    # Save detailed results
    output_file = "validation_results.json"
    results = {
        'validation_dataset': VALIDATION_FILE,
        'sample_size': len(validation_data),
        'skos_accuracy': skos_accuracy,
        'skos_errors': skos_errors,
    }
    
    if VALIDATE_LLM:
        results['llm_accuracy'] = llm_accuracy
        results['llm_errors'] = llm_errors
        results['accuracy_difference'] = llm_accuracy - skos_accuracy
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()


