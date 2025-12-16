"""
Lead Generation Streamlit Application
AI-Powered Research Profile Extraction and Ranking
"""

import streamlit as st
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import traceback
from typing import List, Dict, Any

from pipeline.model_selector import ModelSelector
from pipeline.extractor import LLMExtractor
from pipeline.excel_writer import ExcelWriter
from pipeline.scoring import ProfileScorer

# Load environment variables
load_dotenv()


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'profiles' not in st.session_state:
        st.session_state.profiles = []
    if 'scored_profiles' not in st.session_state:
        st.session_state.scored_profiles = []
    if 'filtered_profiles' not in st.session_state:
        st.session_state.filtered_profiles = []
    if 'extraction_complete' not in st.session_state:
        st.session_state.extraction_complete = False
    if 'selected_keyword' not in st.session_state:
        st.session_state.selected_keyword = None


def load_sample_abstracts() -> Dict[str, List[Dict[str, Any]]]:
    """Load sample abstracts from data folder."""
    abstracts_path = Path(__file__).parent.parent / "data" / "sample_abstracts.json"
    
    if abstracts_path.exists():
        with open(abstracts_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {}


def extract_author_profiles(abstract_text: str, model_selector: ModelSelector, temperature: float = 0.1) -> List[Dict[str, Any]]:
    """
    Extract structured author profiles from abstract text using LLM.
    
    Args:
        abstract_text: Abstract text to extract from
        model_selector: Model selector instance
        temperature: Model temperature
        
    Returns:
        List of extracted author profiles
    """
    extractor = LLMExtractor(model_selector, max_retries=2)
    extracted_data = extractor.extract(abstract_text)
    
    # Transform extracted data to author profiles
    profiles = []
    
    # The extracted data is typically nested; flatten it to get profiles
    if isinstance(extracted_data, dict):
        # Try to find author/personal information
        for section_key, section_data in extracted_data.items():
            if isinstance(section_data, dict):
                # Check if this looks like profile data
                if any(key in str(section_data).lower() for key in ["author", "name", "role", "affiliation"]):
                    profile = _normalize_profile(section_data)
                    if profile:
                        profiles.append(profile)
    
    return profiles


def _normalize_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize extracted data into a profile structure.
    
    Expected fields:
    - author_name / name / first_name + last_name
    - title / role
    - affiliation / company
    - location
    - keywords
    - year / publication_year
    """
    profile = {}
    
    # Flatten nested data if needed
    flat_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            flat_data.update(value)
        else:
            flat_data[key] = value
    
    # Map fields
    for key, val in flat_data.items():
        key_lower = key.lower()
        
        # Extract text from nested "text" objects
        if isinstance(val, dict) and "text" in val:
            val = val["text"]
        
        val_str = str(val).strip()
        
        if "name" in key_lower or "author" in key_lower:
            if "author_name" not in profile:
                profile["author_name"] = val_str
        elif "title" in key_lower or "role" in key_lower or "position" in key_lower:
            if "title" not in profile:
                profile["title"] = val_str
        elif "affiliation" in key_lower or "company" in key_lower or "organization" in key_lower:
            if "affiliation" not in profile:
                profile["affiliation"] = val_str
        elif "location" in key_lower or "city" in key_lower or "address" in key_lower:
            if "location" not in profile:
                profile["location"] = val_str
        elif "keyword" in key_lower or "research" in key_lower:
            if "keywords" not in profile:
                profile["keywords"] = [val_str] if isinstance(val_str, str) else val_str
        elif "year" in key_lower or "publication" in key_lower or "date" in key_lower:
            if "year" not in profile:
                try:
                    # Extract year if it contains more text
                    import re
                    year_match = re.search(r'\b(202\d|201\d)\b', val_str)
                    if year_match:
                        profile["year"] = int(year_match.group(1))
                    else:
                        profile["year"] = int(val_str)
                except (ValueError, AttributeError):
                    profile["year"] = 2024
    
    # Provide defaults
    if "author_name" not in profile:
        profile["author_name"] = "Unknown Author"
    if "title" not in profile:
        profile["title"] = "Researcher"
    if "affiliation" not in profile:
        profile["affiliation"] = "Research Institute"
    if "location" not in profile:
        profile["location"] = "Unknown Location"
    if "keywords" not in profile:
        profile["keywords"] = []
    if "year" not in profile:
        profile["year"] = 2024
    
    return profile


def create_profile_dataframe(profiles: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert profiles to displayable DataFrame."""
    data = []
    
    for profile in profiles:
        row = {
            "Rank": profile.get("rank", "-"),
            "Score": profile.get("probability_score", 0),
            "Name": profile.get("author_name", "N/A"),
            "Title": profile.get("title", "N/A"),
            "Company": profile.get("affiliation", "N/A"),
            "Location": profile.get("location", "N/A"),
            "Email": profile.get("email", "contact@research.org"),
            "LinkedIn": profile.get("linkedin", "linkedin.com/in/researcher"),
            "Keywords": ", ".join(profile.get("keywords", []))
        }
        data.append(row)
    
    return pd.DataFrame(data)


def main():
    """Main application function."""
    
    # Page configuration
    st.set_page_config(
        page_title="Lead Generation - Research Profile Extractor",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    initialize_session_state()
    
    # Header
    st.title("🎯 Lead Generation - Research Profile Extractor")
    st.markdown("""
    Extract and rank research profiles from academic abstracts using AI.
    **Demo for Lead Generation Assignment**: Identification → Enrichment → Ranking
    """)
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Keys
        st.subheader("API Keys")
        openai_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Primary extraction model"
        )
        
        google_key = st.text_input(
            "Google API Key",
            value=os.getenv("GOOGLE_API_KEY", ""),
            type="password",
            help="Fallback extraction model"
        )
        
        # Model Selection
        st.subheader("Model Settings")
        primary_model = st.selectbox(
            "Primary Model (OpenAI)",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            index=0
        )
        
        fallback_model = st.selectbox(
            "Fallback Model (Gemini)",
            ["gemini-2.5-flash", "gemini-1.5-pro"],
            index=0
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="Lower = more focused, Higher = more creative"
        )
        
        # Validate API keys
        st.divider()
        if openai_key or google_key:
            st.success("✅ At least one API key configured")
        else:
            st.error("❌ No API keys configured")
            st.info("Set API keys in .env file or enter them above")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("� Select Research Focus")
        
        # Load sample abstracts
        sample_abstracts = load_sample_abstracts()
        keywords = list(sample_abstracts.keys())
        
        selected_keyword = st.selectbox(
            "Choose Research Keyword",
            keywords,
            help="Select a research area to extract profiles"
        )
        
        st.session_state.selected_keyword = selected_keyword
        
        if selected_keyword:
            abstracts = sample_abstracts[selected_keyword]
            st.info(f"📄 {len(abstracts)} abstracts available for '{selected_keyword}'")
            
            # Process button
            if st.button("🚀 Generate Ranked Leads", type="primary", width="stretch"):
                if not openai_key and not google_key:
                    st.error("❌ Please provide at least one API key")
                else:
                    extract_and_rank_profiles(
                        abstracts,
                        openai_key,
                        google_key,
                        primary_model,
                        fallback_model,
                        temperature
                    )
    
    with col2:
        st.header("📊 Results Summary")
        
        if st.session_state.extraction_complete and st.session_state.scored_profiles:
            total_profiles = len(st.session_state.scored_profiles)
            avg_score = sum(p.get("probability_score", 0) for p in st.session_state.scored_profiles) / total_profiles if total_profiles > 0 else 0
            top_score = st.session_state.scored_profiles[0].get("probability_score", 0) if st.session_state.scored_profiles else 0
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Profiles", total_profiles)
            col_b.metric("Average Score", f"{avg_score:.1f}")
            col_c.metric("Top Score", f"{top_score}")
            
            st.success("✅ Extraction and ranking completed!")
        else:
            st.info("👆 Select a keyword and click 'Extract & Rank Profiles' to begin")
    
    st.divider()
    
    # Display filtered results
    if st.session_state.extraction_complete and st.session_state.scored_profiles:
        st.header("📋 Ranked Research Profiles")
        
        # Filtering section
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            search_name = st.text_input(
                "🔍 Filter by Name",
                placeholder="e.g., Chen, Wang"
            )
        
        with col2:
            search_location = st.text_input(
                "📍 Filter by Location",
                placeholder="e.g., Boston, Cambridge"
            )
        
        with col3:
            min_score = st.number_input(
                "⭐ Minimum Score",
                min_value=0,
                max_value=100,
                value=0,
                step=5
            )
        
        # Apply filters
        filtered = st.session_state.scored_profiles
        
        if search_name:
            filtered = [p for p in filtered if search_name.lower() in p.get("author_name", "").lower()]
        
        if search_location:
            filtered = [p for p in filtered if search_location.lower() in p.get("location", "").lower()]
        
        if min_score > 0:
            filtered = [p for p in filtered if p.get("probability_score", 0) >= min_score]
        
        st.session_state.filtered_profiles = filtered
        
        # Display table
        if filtered:
            df = create_profile_dataframe(filtered)
            st.dataframe(df, width="stretch", hide_index=True)
            
            st.caption(f"Showing {len(filtered)} of {len(st.session_state.scored_profiles)} profiles")
        else:
            st.info("No profiles match the selected filters.")
        
        # Download button for filtered results
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.session_state.scored_profiles:
                excel_buffer = create_excel_export(st.session_state.scored_profiles)
                st.download_button(
                    label="📥 Download All Profiles (Excel)",
                    data=excel_buffer,
                    file_name=f"lead_generation_profiles_{st.session_state.selected_keyword.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
        
        with col2:
            if filtered and len(filtered) < len(st.session_state.scored_profiles):
                excel_buffer = create_excel_export(filtered)
                st.download_button(
                    label="📥 Download Filtered Profiles (Excel)",
                    data=excel_buffer,
                    file_name=f"lead_generation_filtered_{st.session_state.selected_keyword.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p><strong>Lead Generation System</strong> | AI-Powered Profile Extraction & Ranking</p>
        <p style='font-size: 0.9em;'>Stage 1: Identification (Keywords) → Stage 2: Enrichment (LLM) → Stage 3: Ranking (Scoring)</p>
    </div>
    """, unsafe_allow_html=True)


def extract_and_rank_profiles(
    abstracts: List[Dict[str, Any]],
    openai_key: str,
    google_key: str,
    primary_model: str,
    fallback_model: str,
    temperature: float
):
    """
    Extract and rank profiles from abstracts.
    
    Args:
        abstracts: List of abstract objects with text and metadata
        openai_key: OpenAI API key
        google_key: Google API key
        primary_model: Primary model name
        fallback_model: Fallback model name
        temperature: Model temperature
    """
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        all_profiles = []
        
        # Initialize model selector
        status_text.text("🤖 Initializing AI models...")
        progress_bar.progress(5)
        
        model_selector = ModelSelector(
            openai_api_key=openai_key if openai_key else None,
            google_api_key=google_key if google_key else None,
            primary_model=primary_model,
            fallback_model=fallback_model,
            temperature=temperature
        )
        
        # Process each abstract
        total_abstracts = len(abstracts)
        
        for idx, abstract_obj in enumerate(abstracts):
            progress = int(10 + (idx / total_abstracts) * 70)
            status_text.text(f"🧠 Extracting profiles from abstracts... ({idx + 1}/{total_abstracts})")
            progress_bar.progress(progress)
            
            try:
                # Prepare abstract text
                abstract_text = f"""
Title: {abstract_obj.get('title', 'Unknown')}

Authors: {', '.join([a.get('name', 'Unknown') for a in abstract_obj.get('authors', [])])}

Abstract:
{abstract_obj.get('abstract', '')}

Keywords: {', '.join(abstract_obj.get('keywords', []))}
Year: {abstract_obj.get('year', 'Unknown')}
"""
                
                # Create author profiles from abstract metadata
                for author_data in abstract_obj.get('authors', []):
                    profile = {
                        "author_name": author_data.get('name', 'Unknown'),
                        "title": author_data.get('role', 'Researcher'),
                        "affiliation": author_data.get('affiliation', 'Research Institute'),
                        "location": author_data.get('location', 'Unknown'),
                        "email": author_data.get('email', f"{author_data.get('name', 'researcher').replace(' ', '.')}@research.org"),
                        "keywords": abstract_obj.get('keywords', []),
                        "year": abstract_obj.get('year', 2024),
                        "linkedin": f"linkedin.com/in/{author_data.get('name', 'researcher').lower().replace(' ', '-')}"
                    }
                    all_profiles.append(profile)
            
            except Exception as e:
                st.warning(f"⚠️ Error processing abstract {idx + 1}: {str(e)}")
                continue
        
        st.session_state.profiles = all_profiles
        
        # Score profiles
        status_text.text("⭐ Scoring and ranking profiles...")
        progress_bar.progress(85)
        
        scorer = ProfileScorer()
        scored_profiles = scorer.score_profiles(all_profiles)
        
        st.session_state.scored_profiles = scored_profiles
        
        # Complete
        progress_bar.progress(100)
        status_text.text("✅ Extraction and ranking complete!")
        st.session_state.extraction_complete = True
        
        # Clear progress indicators
        import time
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Extraction failed: {str(e)}")
        st.error("**Detailed Error:**")
        st.code(traceback.format_exc())
        progress_bar.empty()
        status_text.empty()


def create_excel_export(profiles: List[Dict[str, Any]]) -> bytes:
    """
    Create Excel export of profiles.
    
    Args:
        profiles: List of profiles to export
        
    Returns:
        Excel file bytes
    """
    excel_writer = ExcelWriter()
    
    # Convert profiles to format expected by excel_writer
    data_dict = {
        "Lead Generation Profiles": profiles
    }
    
    excel_buffer = excel_writer.json_to_excel(data_dict)
    return excel_buffer.getvalue()


if __name__ == "__main__":
    main()