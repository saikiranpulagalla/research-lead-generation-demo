# Lead Generation – Research Profile Extraction Demo

## Project Overview

This application demonstrates an AI-powered lead generation system designed to identify, enrich, and rank research profiles from scientific abstracts. Built as a demo for a lead-generation assignment, the system automates the discovery of qualified researchers based on domain-specific research topics.

**Problem Statement:** Manually identifying relevant research professionals from scientific literature is time-consuming and inconsistent. This system uses natural language processing to extract structured researcher profiles and applies intelligent scoring to prioritize the most relevant contacts.

**Business Context:** This demo mirrors a business development workflow for identifying and prioritizing researchers likely to adopt 3D in-vitro models for therapeutic development—enabling BD teams to rapidly identify high-intent scientific decision-makers.

## System Workflow

The application implements a three-stage pipeline:

### Stage 1: Identification
- User selects a research focus area (e.g., Drug-Induced Liver Injury, 3D Cell Culture, Toxicology)
- System loads pre-curated scientific abstracts matching the selected topic
- Abstracts are prepared for information extraction

### Stage 2: Enrichment
- Large Language Models (LLM) analyze each abstract to extract structured researcher profiles
- Extracted data includes: researcher name, title, affiliation, location, email, and research keywords
- Fallback model ensures robustness if primary extraction fails

### Stage 3: Ranking
- Each profile is scored using a weighted algorithm across four criteria:
  - **Role/Seniority** (30 points): Professor, PI, Director roles rank higher
  - **Publication Recency** (40 points): Recent publications indicate active research
  - **Research Relevance** (20 points): Keyword alignment with selected topic
  - **Geographic/Institutional Fit** (10 points): Location and affiliation considerations
- Profiles are ranked by total score in descending order
- Users can filter and export results

## Data Source

The application uses **curated scientific abstracts** that mirror PubMed structure for demonstration purposes. The demo dataset includes 9 realistic research abstracts across 3 research domains.

**Architecture Note:** The demo uses static PubMed-like data for reliability and reproducibility, but the pipeline is API-ready for live PubMed (NCBI E-utilities) integration without architectural changes. The modular design allows seamless transition from demo data to real-time sources.

## Extraction Details

The LLM extraction pipeline automatically identifies and structures the following information from each abstract:

- **Researcher Name** – First and last name of corresponding authors
- **Role/Title** – Position (e.g., Professor, Postdoctoral Researcher, Senior Scientist)
- **Affiliation** – Institution or organization name
- **Location** – City/country of the researcher's primary institution
- **Email** – Contact email (when available in abstract metadata)
- **Research Keywords** – Topic areas and methodologies mentioned
- **Research Summary** – Concise description of the researcher's work

## Scoring & Ranking Logic

Profiles are ranked using a deterministic scoring algorithm (max 100 points):

| Criterion | Points | Rationale |
|-----------|--------|-----------|
| Role Seniority | 30 | Senior researchers (PI, Professor, Director) signal decision-making authority |
| Publication Recency | 40 | Active publication within last 5 years indicates current engagement |
| Research Keywords | 20 | Direct keyword alignment with selected research focus |
| Location/Institution | 10 | Geographic/institutional fit for partnership opportunity |

**Scoring Rationale:** The combined score acts as a proxy for "propensity to engage"—prioritizing senior, actively publishing researchers working on relevant methodologies.

## User Interface

The Streamlit-based interface provides:

- **Research Topic Selection** – Dropdown menu to choose research area
- **Extract & Rank Button** – Initiates profile extraction and scoring
- **Results Dashboard** – Displays total profiles extracted, average score, and top score
- **Ranked Profiles Table** – Shows all profiles sorted by score with columns:
  - Rank, Score, Name, Title, Company, Location, Email, LinkedIn, Keywords
- **Filtering Options**:
  - Filter by researcher name
  - Filter by location
  - Minimum score threshold
- **Export Functionality**:
  - Download all profiles as Excel
  - Download filtered profiles as Excel

## Design Choices

**Single Research Focus Per Run:** The application enforces a single research focus per run to maintain intent clarity and ensure meaningful lead ranking. This design choice prevents dilution of scoring criteria and guarantees that all ranked profiles are directly comparable on domain-specific relevance metrics.

## Business Value

This system enables Business Development teams to:
- **Identify** high-intent scientific decision-makers from research publications
- **Prioritize** leads by seniority, activity, and research alignment
- **Export** structured profiles for targeted outreach campaigns
- **Scale** lead generation beyond manual literature review

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit (Python web framework) |
| **LLM - Primary** | OpenAI GPT-4o |
| **LLM - Fallback** | Google Gemini 2.5 Flash |
| **Backend** | Python 3.11+ |
| **Data Format** | JSON (abstracts), Excel (export) |
| **Data Processing** | Pandas, openpyxl |
| **API Integration** | LangChain |

## Limitations & Future Enhancements

### Current Limitations
- **Static Demo Data**: Currently uses pre-curated abstracts; not real-time data
- **Extraction Accuracy**: LLM performance depends on abstract quality and structure
- **Limited to 2 LLM Providers**: OpenAI and Gemini only; others can be added

### Planned Enhancements
- **PubMed API Integration**: Real-time abstract fetching using NCBI E-utilities
- **Advanced Lead Scoring**: Customizable weighting per research domain
- **RAG Support**: Retrieve and rank based on full-text paper analysis
- **Batch Processing**: Multi-keyword analysis and comparative ranking
- **Database Integration**: Persist extracted profiles for duplicate detection and historical tracking

## System Architecture (Lead Identification & Scoring Pipeline)


```mermaid
%%{init: {
  "theme": "default",
  "themeVariables": {
    "primaryColor": "#E3F2FD",
    "primaryTextColor": "#0D0D0D",
    "secondaryColor": "#FFF3E0",
    "secondaryTextColor": "#0D0D0D",
    "tertiaryColor": "#E8F5E9",
    "tertiaryTextColor": "#0D0D0D",
    "lineColor": "#424242",
    "fontSize": "14px"
  }
}}%%

graph TB
    User["👤 Business / Research Analyst"]
    UI["🖥 Streamlit UI<br/>Research Topic Selection"]
    Data["📄 Scientific Abstracts<br/>(Demo / PubMed-ready)"]

    Extract["🧠 Profile Identification & Enrichment<br/>(LLM Extraction)"]
    Signals["📊 Signal Generator<br/>• Role / Seniority<br/>• Publication Recency<br/>• Keyword Relevance<br/>• Location / Institution"]

    Score["⭐ Propensity Scoring Engine<br/>(0–100 Lead Score)"]
    Rank["📈 Ranking & Filtering"]
    Export["📤 Export Leads<br/>(Excel / CSV)"]

    User --> UI
    UI --> Data
    Data --> Extract
    Extract --> Signals
    Signals --> Score
    Score --> Rank
    Rank --> Export
    Export --> User

```

## How to Run

### Prerequisites
- Python 3.11 or higher
- `uv` package manager ([install uv](https://docs.astral.sh/uv/))
- API keys for OpenAI and/or Google (set in `.env` file)

### Quick Start with `uv`

1. **Clone the repository**
   ```bash
   git clone https://github.com/saikiranpulagalla/research-lead-generation-demo.git
   cd research-lead-generation-demo
   ```

2. **Create virtual environment with uv**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies with uv**
   ```bash
   uv sync
   ```

4. **Set up API keys**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

### Alternative: Traditional pip Setup

If you prefer traditional Python setup:

   ```bash
   git clone https://github.com/saikiranpulagalla/research-lead-generation-demo.git
   cd research-lead-generation-demo
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Running the Application

Start the Streamlit application:
```bash
streamlit run app/streamlit_app.py
```

The app will open at `http://localhost:8501`

## Project Structure

### Essential Files Only

```
research-lead-generation-demo/
├── app/
│   ├── streamlit_app.py              # Main Streamlit UI
│   └── pipeline/
│       ├── model_selector.py         # LLM model selection logic
│       ├── extractor.py              # LLM extraction engine
│       ├── scoring.py                # Profile scoring algorithm
│       └── excel_writer.py           # Excel export handler
├── data/
│   └── sample_abstracts.json         # Demo dataset (9 abstracts, 3 keywords)
├── .env.example                      # Example environment variables
├── prompts/
│   └── extraction_prompt.txt         # LLM extraction instructions
├── pyproject.toml                    # Project metadata & dependencies (uv)
├── requirements.txt                  # Python dependencies (pip)
└── README.md                         # This file
```

**Note:** Non-essential files (test configs, legacy modules, pycache) are removed for a clean, production-ready structure.

## Notes

- The application gracefully handles LLM failures by falling back to a secondary model
- All extracted data is processed locally; no profiles are stored without explicit export
- Scoring algorithm is reproducible and deterministic for consistent ranking

## Compliance Note

This demo uses publicly available or synthetic data and does not scrape private platforms such as LinkedIn or ResearchGate.

---

**Status:** Demo Application | Lead Generation Assignment | v1.0
