"""
Scoring Module
Ranks research profiles based on weighted criteria for lead generation.
"""

from typing import Dict, Any, List
from datetime import datetime
import re


class ProfileScorer:
    """Calculates probability scores for research profiles."""
    
    # Weighted scoring criteria
    ROLE_KEYWORDS = ["Toxicology", "Safety", "Hepatic", "3D"]
    ROLE_SCORE = 30
    
    RECENT_YEARS = 2  # Consider "recent" as last N years
    RECENT_SCORE = 40
    
    RESEARCH_KEYWORDS = ["liver", "toxicity", "3D models", "hepatic"]
    RESEARCH_SCORE = 20
    
    HUB_LOCATIONS = ["Boston", "Cambridge", "Bay Area", "Basel", "Palo Alto", "Berkeley", "San Francisco"]
    LOCATION_SCORE = 10
    
    def calculate_score(self, profile: Dict[str, Any]) -> int:
        """
        Calculate probability score for a profile based on weighted criteria.
        
        Args:
            profile: Profile dictionary containing:
                - author_name: Name of researcher
                - title: Job title or role
                - affiliation: Organization/company
                - location: Geographic location
                - keywords: List of research keywords
                - year: Publication year
                
        Returns:
            Integer score (0-100+)
        """
        score = 0
        
        # Criterion 1: Role/Title contains key phrases (+30)
        title = str(profile.get("title", "")).lower()
        for keyword in self.ROLE_KEYWORDS:
            if keyword.lower() in title:
                score += self.ROLE_SCORE
                break  # Count only once per criterion
        
        # Criterion 2: Recent publication (last 2 years) (+40)
        publication_year = profile.get("year")
        if publication_year:
            try:
                current_year = datetime.now().year
                if isinstance(publication_year, str):
                    publication_year = int(publication_year)
                
                if current_year - publication_year <= self.RECENT_YEARS:
                    score += self.RECENT_SCORE
            except (ValueError, TypeError):
                pass  # Skip if year parsing fails
        
        # Criterion 3: Research keywords match (+20)
        keywords = profile.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        
        keywords_lower = [k.lower() for k in keywords]
        for research_kw in self.RESEARCH_KEYWORDS:
            if any(research_kw.lower() in kw for kw in keywords_lower):
                score += self.RESEARCH_SCORE
                break  # Count only once per criterion
        
        # Criterion 4: Location in hub (+10)
        location = str(profile.get("location", "")).lower()
        for hub in self.HUB_LOCATIONS:
            if hub.lower() in location:
                score += self.LOCATION_SCORE
                break  # Count only once per criterion
        
        return score
    
    def score_profiles(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score multiple profiles and add score field.
        
        Args:
            profiles: List of profile dictionaries
            
        Returns:
            List of profiles with added 'probability_score' field, sorted by score descending
        """
        scored_profiles = []
        
        for profile in profiles:
            profile_copy = profile.copy()
            score = self.calculate_score(profile_copy)
            profile_copy["probability_score"] = score
            scored_profiles.append(profile_copy)
        
        # Sort by score descending
        scored_profiles.sort(key=lambda x: x.get("probability_score", 0), reverse=True)
        
        # Add rank
        for rank, profile in enumerate(scored_profiles, 1):
            profile["rank"] = rank
        
        return scored_profiles


def calculate_score(profile: Dict[str, Any]) -> int:
    """
    Standalone function to calculate probability score for a profile.
    
    Args:
        profile: Profile dictionary
        
    Returns:
        Integer score (0-100+)
    """
    scorer = ProfileScorer()
    return scorer.calculate_score(profile)
