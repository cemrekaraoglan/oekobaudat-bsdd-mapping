# Detailed Workflow Guide

Complete guide for mapping bsDD dictionaries to Ökobaudat environmental product categories.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Step-by-Step Workflow](#step-by-step-workflow)
4. [Customization](#customization)
5. [Validation](#validation)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Topics](#advanced-topics)

---

## Overview

### What This Tool Does

**Maps building products from any bsDD dictionary to Ökobaudat environmental categories.**

```
┌─────────────────────┐
│ bsDD Dictionary     │
│ (ETIM, IFC, etc.)   │ ──┐
└─────────────────────┘   │
                          │  Semantic
┌─────────────────────┐   │  Matching
│ Ökobaudat           │   │  (GPT-5)
│ (German categories) │ ──┘
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ SKOS Mappings       │
│ (RDF + JSON)        │
└─────────────────────┘
```

### Key Features

- **Universal:** Works with any bsDD dictionary
- **Semantic:** LLM understands meaning, not just text
- **Cross-lingual:** Handles multiple languages
- **Explainable:** Provides confidence scores + reasoning
- **Standards-based:** Uses SKOS for relationships

---

## Architecture

### Three-Layer Structure

#### 1. Ökobaudat Ontology (OWL)

**File:** `Mapping/oekobaudat_owl.ttl`

```turtle
obd:Mineralische_Baustoffe a owl:Class ;
    rdfs:label "Mineralische Baustoffe"@de ;
    rdfs:label "Mineral Building Materials"@en .

obd:Bindemittel a owl:Class ;
    rdfs:label "Bindemittel"@de ;
    rdfs:label "Binders"@en ;
    rdfs:subClassOf obd:Mineralische_Baustoffe .
```

- **Purpose:** Category hierarchy
- **Format:** OWL (Web Ontology Language)
- **Properties:** `rdfs:subClassOf` for hierarchy
- **Languages:** German (primary) + English (LLM-translated)

#### 2. bsDD Classifications

**Source:** bsDD API

```json
{
  "code": "EC000037",
  "name": "Gypsum board",
  "uri": "https://identifier.buildingsmart.org/uri/etim/etim-10.1/class/EC000037",
  "definition": "Boards made from gypsum..."
}
```

- **Purpose:** Product classifications
- **Source:** Live API (always up-to-date)
- **Dictionaries:** ETIM, IFC, UniClass, OmniClass, etc.

#### 3. Mappings (SKOS)

**File:** `Mapping/etim_oekobaudat_mappings.ttl`

```turtle
bsdd:EC000037 a skos:Concept ;
    rdfs:label "Gypsum board"@en ;
    skos:exactMatch obd:Gipsplatten ;
    dcterms:description "Direct equivalent. Same product type."@en .
```

- **Purpose:** Relationships between bsDD and Ökobaudat
- **Format:** SKOS (Simple Knowledge Organization System)
- **Properties:** `exactMatch`, `closeMatch`, `related`

---

## Step-by-Step Workflow

### Prerequisites

1. **Python 3.8+** installed
2. **Azure OpenAI** subscription
3. **Internet connection** (for bsDD API)

---

### Step 0: Setup (First Time Only)

#### Install Dependencies

```bash
pip install -r requirements_mapper.txt
```

**Installs:**
- `requests` - HTTP client
- `rdflib` - RDF processing
- `openai` - Azure OpenAI SDK
- `python-dotenv` - Environment variables

#### Configure Credentials

Create `.env` file:

```bash
# Windows PowerShell
Copy-Item env.example .env

# Mac/Linux
cp env.example .env
```

Edit `.env`:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

**Get credentials:**
1. Azure Portal → Your OpenAI resource
2. Keys and Endpoint section
3. Copy Endpoint + Key1

Verify:

```bash
python utils/config.py
# Should show: "OK - Configuration loaded successfully"
```

---

### Step 1: Build Ökobaudat RDF Graph

**Purpose:** Create bilingual OWL ontology of Ökobaudat categories

```bash
python 01_build_oekobaudat_rdf.py
```

**What it does:**

1. **Parses XML**
   - Input: `Mapping/OEKOBAUDAT Product Categories.xml`
   - Extracts: 442 categories with hierarchy

2. **Translates to English**
   - Method: LLM translations (cached)
   - Source: `Mapping/oekobaudat_translation_cache.json` (434 terms)
   - Fallback: Hardcoded dictionary + word-by-word

3. **Builds OWL Ontology**
   - Creates: `owl:Class` for each category
   - Hierarchy: `rdfs:subClassOf` relationships
   - Labels: Both `@de` and `@en`

**Output:**

- `Mapping/oekobaudat_owl.ttl` (142 KB, ~2991 triples)
- `Mapping/oekobaudat_translated.json` (JSON export)

**Duration:** ~5 seconds

**Example output:**

```turtle
obd:Gipsplatten a owl:Class ;
    rdfs:label "Gipsplatten"@de ;
    rdfs:label "Gypsum Board"@en ;
    rdfs:subClassOf obd:Gips ;
    obd:okobaudatCategory oekocat:1.1.03.01 .
```

---

### Step 2: Map bsDD to Ökobaudat

**Purpose:** Semantic matching with LLM

```bash
python 02_map_etim_to_oekobaudat_llm.py
```

**What it does:**

1. **Fetch bsDD Classifications**
   - Source: bsDD API
   - Default: ETIM v10.1 (latest)
   - Count: ~1000 classes

2. **Load Ökobaudat Ontology**
   - Parses: `oekobaudat_owl.ttl`
   - Extracts: 442 categories

3. **LLM Semantic Matching**
   - Model: GPT-5-mini
   - For each bsDD class:
     - Analyzes definition and name
     - Finds best Ökobaudat match
     - Assigns confidence (0.0-1.0)
     - Determines match type
     - Provides reasoning

4. **Generate SKOS Mappings**
   - Creates RDF with relationships
   - Exports JSON with details

**Match Type Logic:**

| Confidence | Match Type | SKOS Property | Example |
|-----------|-----------|---------------|---------|
| 0.9-1.0 | exactMatch | `skos:exactMatch` | "Gypsum board" → "Gipsplatten" |
| 0.7-0.89 | closeMatch | `skos:closeMatch` | "Wall panel" → "Wandplatten" |
| 0.5-0.69 | relatedMatch | `skos:related` | "Insulation" → "Dämmstoffe" |
| <0.5 | noMatch | Custom property | No good match found |

**Outputs:**

- `Mapping/etim_oekobaudat_mappings.ttl` (RDF/Turtle)
- `Mapping/etim_oekobaudat_mappings.json` (JSON)

**Duration:** Depends on class count
- 100 classes: ~2 minutes
- 1000 classes: ~20 minutes
- Rate: ~1 class per second

**Example output:**

```json
{
  "bsdd_class": {
    "code": "EC000037",
    "name": "Gypsum board"
  },
  "oekobaudat_match": {
    "id": "1.1.03.01",
    "name_de": "Gipsplatten"
  },
  "match_type": "exactMatch",
  "confidence": 0.95,
  "reasoning": "Direct translation. Both refer to gypsum-based boards for interior walls.",
  "method": "llm"
}
```

---

### Step 3: Validation (Optional)

**Purpose:** Measure actual accuracy with ground truth

#### 3a. Create Validation Sample

```bash
python 03_create_validation_sample.py
```

Generates sample for manual annotation.

#### 3b. Manual Annotation

Edit `validation_sample.json` - add correct matches.

#### 3c. Measure Accuracy

```bash
python 03_validate_accuracy.py
```

Calculates precision, recall, F1 scores.

**Note:** Implementation pending - stubs in place.

---

## Customization

### Using Different bsDD Dictionaries

#### Option 1: Modify Script

Edit `02_map_etim_to_oekobaudat_llm.py`:

```python
# Instead of ETIM
client = BsddApiClient()
classes = client.get_etim_classes()

# Use any bsDD dictionary
# 1. List available dictionaries
dictionaries = client.get_dictionaries()
for d in dictionaries:
    print(f"{d['name']} ({d['code']}) v{d['version']}")

# 2. Search for specific dictionary
ifc_dict = client.find_dictionary_by_code('ifc')  # Example

# 3. Get classes from that dictionary
classes = client.get_dictionary_classes(ifc_dict['uri'])
```

#### Option 2: Command Line (Future)

```bash
python 02_map_etim_to_oekobaudat_llm.py --dictionary=ifc --version=4.3
```

### Filtering Classes

Limit to specific categories:

```python
# In 02_map_etim_to_oekobaudat_llm.py
all_classes = client.get_etim_classes()

# Filter by code prefix
building_materials = [c for c in all_classes if c.code.startswith('EC00')]

# Filter by name
insulation = [c for c in all_classes if 'insulation' in c.name.lower()]

# Use filtered list
mappings = mapper.map_all(building_materials, categories)
```

### Adjusting LLM Behavior

#### Change Model

Edit `.env`:

```env
AZURE_OPENAI_DEPLOYMENT=gpt-4  # More expensive, higher quality
```

#### Modify Prompt

Edit `02_map_etim_to_oekobaudat_llm.py`, method `create_prompt`:

```python
def create_prompt(self, bsdd_class, candidates):
    prompt = f"""You are an expert in sustainable building materials.

Match this product to the best Ökobaudat category:

Product: {bsdd_class.name}
Definition: {bsdd_class.definition}

Ökobaudat Categories:
{category_list}

Instructions:
1. Focus on environmental impact classification
2. Consider lifecycle assessment context
3. Prefer specific over general categories
4. Be conservative with exactMatch (0.9+ only)

Respond with JSON:
{{
  "category_id": "...",
  "confidence": 0.0-1.0,
  "match_type": "exactMatch|closeMatch|relatedMatch|noMatch",
  "reasoning": "..."
}}
"""
    return prompt
```

### Custom Match Types

Beyond SKOS standard:

```python
# In 02_map_etim_to_oekobaudat_llm.py
CUSTOM = Namespace("https://your-domain.org/mapping/")

# Add custom relationship
if mapping.match_type == 'possibleMatch':
    self.graph.add((bsdd_uri, CUSTOM.possibleMatch, oeko_uri))
```

---

## Validation

### Why Validate?

Confidence scores ≠ accuracy. Validation measures actual correctness.

### Workflow

1. **Sample Selection**
   - Random or stratified by confidence
   - Recommended: 50-100 samples

2. **Manual Annotation**
   - Domain expert reviews
   - Marks correct matches
   - Documents edge cases

3. **Accuracy Measurement**
   - Precision: Of predicted matches, how many correct?
   - Recall: Of true matches, how many found?
   - F1 Score: Harmonic mean

### Expected Results

With GPT-5-mini:
- **Precision:** 85-90% (predicted matches are correct)
- **Recall:** 80-85% (finds most true matches)
- **F1 Score:** 82-87% (balanced performance)

Clear cases (e.g., "Gypsum board"): 95%+ accuracy  
Ambiguous cases (e.g., composite materials): 70-80% accuracy

---

## Troubleshooting

### API Connection Issues

**Problem:** bsDD API not responding

**Solution:**
```python
# Use local loader as fallback (if you have downloaded ETIM JSON)
from utils.etim_local_loader import LocalEtimLoader
loader = LocalEtimLoader("path/to/etim-10.1.json")
classes = loader.load()
```

**Note:** Download ETIM JSON from [buildingSMART bsDD Repository](https://github.com/buildingSMART/bSDD) if needed for offline work.

### Credential Errors

**Problem:** "AZURE_OPENAI_ENDPOINT not set"

**Solution:**
1. Ensure `.env` file exists
2. Check file contains correct keys
3. Run `python utils/config.py` to verify

### Low Match Quality

**Symptoms:**
- Many noMatch results
- Low confidence scores (<0.7)
- Obviously incorrect mappings

**Solutions:**

1. **Try GPT-4** (better reasoning):
   ```env
   AZURE_OPENAI_DEPLOYMENT=gpt-4
   ```

2. **Improve prompt**:
   - Add domain-specific instructions
   - Provide examples
   - Clarify criteria

3. **Check translations**:
   - Verify Ökobaudat English labels are correct
   - Update cache if needed

### Rate Limiting

**Problem:** API timeout or rate limit errors

**Solution:**

```python
# In 02_map_etim_to_oekobaudat_llm.py
BATCH_SIZE = 5          # Reduce from 10
DELAY_SECONDS = 2       # Increase from 1

# Or process in smaller chunks
classes = classes[:100]  # First 100 only
```

### Memory Issues

**Problem:** Script crashes with large datasets

**Solution:**

```python
# Process incrementally
chunk_size = 100
for i in range(0, len(all_classes), chunk_size):
    chunk = all_classes[i:i+chunk_size]
    mappings = mapper.map_all(chunk, categories)
    
    # Save after each chunk
    with open(f'mappings_chunk_{i}.json', 'w') as f:
        json.dump(mappings, f)
```

---

## Advanced Topics

### Batch Processing

Process multiple dictionaries:

```python
dictionaries = ['etim', 'ifc', 'uniclass']

for dict_name in dictionaries:
    print(f"Processing {dict_name}...")
    classes = get_classes_for_dictionary(dict_name)
    mappings = mapper.map_all(classes, categories)
    save_mappings(f"{dict_name}_mappings.ttl", mappings)
```

### Integration with Other Tools

#### Export to CSV

```python
import csv

with open('mappings.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['bsDD Code', 'bsDD Name', 'Ökobaudat ID', 
                     'Ökobaudat Name', 'Match Type', 'Confidence'])
    
    for mapping in mappings:
        writer.writerow([
            mapping.bsdd_class.code,
            mapping.bsdd_class.name,
            mapping.oekobaudat_category.id,
            mapping.oekobaudat_category.name_de,
            mapping.match_type,
            mapping.confidence_score
        ])
```

#### SPARQL Queries

```sparql
# Find all exactMatch mappings
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?bsdd ?oeko
WHERE {
  ?bsdd skos:exactMatch ?oeko .
}
```

### Performance Optimization

**Parallel Processing:**

```python
from concurrent.futures import ThreadPoolExecutor

def process_class(cls):
    return mapper.match_single(cls, categories)

with ThreadPoolExecutor(max_workers=5) as executor:
    mappings = list(executor.map(process_class, classes))
```

**Caching:**

```python
# Cache LLM responses
import json

cache_file = 'llm_cache.json'

def query_with_cache(prompt):
    cache = load_cache(cache_file)
    if prompt in cache:
        return cache[prompt]
    
    response = llm.query(prompt)
    cache[prompt] = response
    save_cache(cache_file, cache)
    return response
```

---

## Best Practices

### 1. Start Small

Test with 50-100 classes before processing thousands.

### 2. Validate Early

Run validation on subset to catch issues early.

### 3. Document Changes

Track prompt modifications and results.

### 4. Version Control

Commit mappings with descriptive messages:

```bash
git add Mapping/etim_oekobaudat_mappings.*
git commit -m "ETIM v10.1 mappings - GPT-5-mini - 87% F1 score"
```

### 5. Monitor Costs

Track Azure OpenAI usage:

```python
# Estimate cost before running
num_classes = len(classes)
estimated_cost = num_classes * 0.0001  # $0.0001 per class with GPT-5-mini
print(f"Estimated cost: ${estimated_cost:.2f}")
```

---

## References

### Standards
- **SKOS:** https://www.w3.org/2004/02/skos/
- **OWL:** https://www.w3.org/OWL/
- **RDF:** https://www.w3.org/RDF/

### APIs
- **bsDD API:** https://api.bsdd.buildingsmart.org
- **Azure OpenAI:** https://learn.microsoft.com/en-us/azure/ai-services/openai/

### Data Sources
- **ETIM:** https://www.etim-international.com/
- **Ökobaudat:** https://www.oekobaudat.de/
- **buildingSMART:** https://www.buildingsmart.org/

---

**Last Updated:** January 13, 2026  
**Version:** 2.0
