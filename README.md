# bsDD to Ökobaudat Mapper

**Semantic mapping tool for buildingSMART Data Dictionary (bsDD) classifications to German Ökobaudat environmental product categories.**

Map any bsDD dictionary (ETIM, IFC, UniClass, etc.) to Ökobaudat using GPT-5-mini powered semantic matching.

## 🎯 What It Does

Automatically maps building materials and products from bsDD dictionaries onto the Ökobaudat category hierarchy:

**Input:** List of products from any bsDD dictionary (e.g., ETIM "Gypsum board")  
**Process:** Semantic matching with LLM (GPT-5-mini)  
**Output:** RDF graph with SKOS relationships + confidence scores

**Example:**
- ETIM "Gypsum board" → Ökobaudat "Gipsplatten" (`skos:exactMatch`, confidence: 0.95)
- IFC "IfcWall" → Ökobaudat "Wände" (`skos:closeMatch`, confidence: 0.85)

## 📋 Prerequisites

- **Python 3.8+**
- **Internet connection** (for bsDD API and Azure OpenAI)
- **Azure OpenAI** subscription with GPT-5-mini deployment

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/bsDD.git
cd bsDD
pip install -r requirements_mapper.txt
```

### 2. Configure Credentials

**⚠️ Important:** Credentials are stored in `.env` file (not committed to git)

```bash
# Copy template
cp env.example .env  # or: Copy-Item env.example .env (Windows)

# Edit .env with your Azure OpenAI credentials
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-api-key-here
# AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

Get credentials from [Azure Portal](https://portal.azure.com) → Azure OpenAI → Keys and Endpoint

```bash
# Verify setup
python utils/config.py
```

### 3. Run Workflow

#### Step 1: Build Ökobaudat RDF Graph

```bash
python 01_build_oekobaudat_rdf.py
```

**Output:** `Mapping/oekobaudat_owl.ttl` (OWL ontology with DE/EN labels)

#### Step 2: Map bsDD Dictionary to Ökobaudat

```bash
python 02_map_etim_to_oekobaudat_llm.py
```

**What it does:**
- Fetches classifications from bsDD API (default: ETIM)
- Semantic matching with GPT-5-mini
- Generates SKOS mappings

**Outputs:**
- `Mapping/etim_oekobaudat_mappings.ttl` (RDF with SKOS relationships)
- `Mapping/etim_oekobaudat_mappings.json` (JSON with confidence + reasoning)

**Match types:**
- `skos:exactMatch` - Same concept (confidence 0.9-1.0)
- `skos:closeMatch` - Very similar (0.7-0.89)
- `skos:relatedMatch` - Related (0.5-0.69)
- `noMatch` - No good match (<0.5)

#### Step 3: View Results

Open `mapping_viewer.html` in your browser to explore mappings interactively.

## 🔧 Configuration

### Using Different bsDD Dictionaries

Edit `02_map_etim_to_oekobaudat_llm.py` to use other bsDD dictionaries:

```python
# Default: ETIM
classes = client.get_etim_classes()

# Or fetch any bsDD dictionary
# See: https://api.bsdd.buildingsmart.org
```

### Adjusting LLM Model

Change deployment in `.env`:

```env
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini  # Fast & cost-effective
# or
AZURE_OPENAI_DEPLOYMENT=gpt-4       # Higher quality, more expensive
```

## 📁 Project Structure

```
bsDD/
├── 01_build_oekobaudat_rdf.py       # Build Ökobaudat OWL ontology
├── 02_map_etim_to_oekobaudat_llm.py # Map bsDD → Ökobaudat
├── 03_create_validation_sample.py   # Create validation dataset
├── 03_validate_accuracy.py          # Measure mapping accuracy
│
├── utils/                           # Helper modules
│   ├── bsdd_api_client.py          # bsDD API client
│   ├── config.py                   # Credential management
│   └── ...
│
├── docs/                            # Documentation
│   └── WORKFLOW.md                 # Detailed workflow guide
│
├── Mapping/                         # Data & outputs
│   ├── oekobaudat_owl.ttl          # Ökobaudat ontology (generated)
│   ├── etim_oekobaudat_mappings.*  # Mapping results (generated)
│   └── ...
│
├── .env                             # Your credentials (gitignored)
├── env.example                      # Template
└── README.md                        # This file
```

## 🔐 Security

**Credentials are protected:**
- `.env` file is ignored by git (never committed)
- `env.example` is a template with placeholders (safe to commit)
- See `PRE_PUSH_CHECKLIST.md` before pushing to GitHub

## 📊 Output Formats

### RDF (Turtle)

```turtle
@prefix bsdd: <https://identifier.buildingsmart.org/uri/etim/etim-10.1/class/> .
@prefix obd: <https://oekobaudat.de/class/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

bsdd:EC000037 a skos:Concept ;
    rdfs:label "Gypsum board"@en ;
    skos:exactMatch obd:Gipsplatten ;
    rdfs:comment "Direct translation. Same product category."@en .
```

### JSON

```json
{
  "bsdd_class": {
    "code": "EC000037",
    "name": "Gypsum board",
    "uri": "https://identifier.buildingsmart.org/uri/etim/etim-10.1/class/EC000037"
  },
  "oekobaudat_match": {
    "id": "1.1.03.01",
    "name_de": "Gipsplatten",
    "path_de": "Mineralische Baustoffe/Bindemittel/Gips/Gipsplatten"
  },
  "match_type": "exactMatch",
  "confidence": 0.95,
  "reasoning": "Direct translation and identical product category.",
  "method": "llm"
}
```

## 🧪 Testing

```bash
# Test bsDD API connection
python test_bsdd_api.py

# Test Azure OpenAI credentials
python -m utils.test_azure_openai

# Verify configuration
python utils/config.py
```

## 📚 Documentation

- **[docs/WORKFLOW.md](docs/WORKFLOW.md)** - Complete guide: architecture, workflow, customization, validation
- **[docs/SECURITY_SETUP.md](docs/SECURITY_SETUP.md)** - Credential management & GitHub security
- **[PRE_PUSH_CHECKLIST.md](PRE_PUSH_CHECKLIST.md)** - Quick security checklist before pushing

## 🔗 Data Sources

- **bsDD API:** https://api.bsdd.buildingsmart.org
- **ETIM:** https://www.etim-international.com
- **Ökobaudat:** https://www.oekobaudat.de
- **buildingSMART:** https://www.buildingsmart.org

## 💰 Cost Estimation

Using GPT-5-mini:
- ~$0.10 per 1000 product classifications
- Typical project (500 classes): ~$0.05

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

**Security:** Never commit `.env` file! See `PRE_PUSH_CHECKLIST.md`

## 📄 License

This project is open source. For bsDD data terms, see [buildingSMART License](https://github.com/buildingSMART/bSDD).

---

**Questions?** See [docs/WORKFLOW.md](docs/WORKFLOW.md) for detailed documentation.
