"""
UserSkillProfile - Adaptive UI Based on User Expertise (Phase 4)

Tracks user expertise across different domains to enable:
- Adaptive interface complexity
- Personalized suggestions
- Progressive disclosure of advanced features
- Learning curve optimization

The profile learns from:
- Code complexity user works with
- Feature usage patterns
- Verification preferences
- Error recovery patterns
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import math


class SkillLevel(str, Enum):
    """User skill levels for adaptive UI."""
    NOVICE = "novice"           # New to coding or AXIOM
    INTERMEDIATE = "intermediate"  # Comfortable with basics
    ADVANCED = "advanced"        # Power user
    EXPERT = "expert"           # Deep expertise


class SkillDomain(str, Enum):
    """Domains for skill tracking."""
    INTENT_AUTHORING = "intent_authoring"
    CODE_REVIEW = "code_review"
    VERIFICATION = "verification"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"


@dataclass
class DomainSkill:
    """Skill level for a specific domain."""
    domain: SkillDomain
    level: SkillLevel = SkillLevel.NOVICE
    score: float = 0.0  # 0-100
    confidence: float = 0.5  # How confident we are in this assessment
    sample_count: int = 0  # Number of samples used for assessment
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Learning rate params (exponential moving average)
    learning_rate: float = 0.1
    
    def update_score(self, performance_signal: float):
        """
        Update skill score based on performance signal.
        
        Args:
            performance_signal: 0-100 indicating performance (e.g., verification pass rate)
        """
        self.sample_count += 1
        self.confidence = min(0.95, self.confidence + 0.01)
        
        # Exponential moving average
        self.score = (1 - self.learning_rate) * self.score + self.learning_rate * performance_signal
        
        # Update level based on score
        if self.score >= 85:
            self.level = SkillLevel.EXPERT
        elif self.score >= 65:
            self.level = SkillLevel.ADVANCED
        elif self.score >= 40:
            self.level = SkillLevel.INTERMEDIATE
        else:
            self.level = SkillLevel.NOVICE
        
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "level": self.level.value,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class UserSkillProfile:
    """
    Complete user skill profile for adaptive UI.
    
    Tracks expertise across domains and provides recommendations
    for UI complexity and feature exposure.
    """
    user_id: str
    org_id: str
    
    # Per-domain skills
    skills: Dict[SkillDomain, DomainSkill] = field(default_factory=dict)
    
    # Overall level (computed from domain skills)
    overall_level: SkillLevel = SkillLevel.NOVICE
    overall_score: float = 0.0
    
    # Preferences learned from behavior
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Feature usage tracking
    feature_usage: Dict[str, int] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Initialize all domain skills if not present
        for domain in SkillDomain:
            if domain not in self.skills:
                self.skills[domain] = DomainSkill(domain=domain)
    
    def update_skill(self, domain: SkillDomain, performance_signal: float):
        """Update a specific domain skill."""
        if domain not in self.skills:
            self.skills[domain] = DomainSkill(domain=domain)
        
        self.skills[domain].update_score(performance_signal)
        self._recalculate_overall()
        self.updated_at = datetime.utcnow()
    
    def _recalculate_overall(self):
        """Recalculate overall skill level from domain skills."""
        if not self.skills:
            return
        
        # Weighted average (give more weight to high-confidence skills)
        total_weight = 0.0
        weighted_sum = 0.0
        
        for skill in self.skills.values():
            weight = skill.confidence * skill.sample_count
            weighted_sum += skill.score * weight
            total_weight += weight
        
        if total_weight > 0:
            self.overall_score = weighted_sum / total_weight
        
        # Determine overall level
        if self.overall_score >= 85:
            self.overall_level = SkillLevel.EXPERT
        elif self.overall_score >= 65:
            self.overall_level = SkillLevel.ADVANCED
        elif self.overall_score >= 40:
            self.overall_level = SkillLevel.INTERMEDIATE
        else:
            self.overall_level = SkillLevel.NOVICE
    
    def record_feature_usage(self, feature_name: str):
        """Record usage of a feature."""
        self.feature_usage[feature_name] = self.feature_usage.get(feature_name, 0) + 1
        self.updated_at = datetime.utcnow()
    
    def get_ui_recommendations(self) -> Dict[str, Any]:
        """
        Get UI recommendations based on skill profile.
        
        Returns recommendations for:
        - Interface complexity
        - Feature visibility
        - Help level
        - Suggested tutorials
        """
        recommendations = {
            "interface_complexity": self._get_complexity_level(),
            "show_advanced_features": self.overall_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT],
            "show_tutorials": self.overall_level in [SkillLevel.NOVICE, SkillLevel.INTERMEDIATE],
            "auto_suggestions": self.overall_level != SkillLevel.EXPERT,
            "confirmation_prompts": self.overall_level == SkillLevel.NOVICE,
            "detailed_explanations": self.overall_level in [SkillLevel.NOVICE, SkillLevel.INTERMEDIATE],
            "keyboard_shortcuts_hint": self.overall_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT],
            
            # Domain-specific recommendations
            "verification_detail_level": self._get_verification_detail_level(),
            "code_complexity_limit": self._get_code_complexity_limit(),
            
            # Suggested next steps
            "suggested_learning": self._get_learning_suggestions(),
        }
        
        return recommendations
    
    def _get_complexity_level(self) -> str:
        """Get recommended interface complexity."""
        if self.overall_level == SkillLevel.NOVICE:
            return "simplified"
        elif self.overall_level == SkillLevel.INTERMEDIATE:
            return "standard"
        elif self.overall_level == SkillLevel.ADVANCED:
            return "full"
        else:
            return "power"
    
    def _get_verification_detail_level(self) -> str:
        """Get verification detail level based on verification skill."""
        verification_skill = self.skills.get(SkillDomain.VERIFICATION)
        if not verification_skill:
            return "summary"
        
        if verification_skill.level in [SkillLevel.ADVANCED, SkillLevel.EXPERT]:
            return "detailed"
        elif verification_skill.level == SkillLevel.INTERMEDIATE:
            return "standard"
        else:
            return "summary"
    
    def _get_code_complexity_limit(self) -> int:
        """Get recommended max code complexity."""
        complexity_map = {
            SkillLevel.NOVICE: 10,
            SkillLevel.INTERMEDIATE: 25,
            SkillLevel.ADVANCED: 50,
            SkillLevel.EXPERT: 100
        }
        return complexity_map.get(self.overall_level, 25)
    
    def _get_learning_suggestions(self) -> List[str]:
        """Get suggested learning topics based on weak areas."""
        suggestions = []
        
        # Find domains with low scores
        for domain, skill in sorted(self.skills.items(), key=lambda x: x[1].score):
            if skill.score < 50 and skill.sample_count > 5:
                suggestions.append(f"Practice {domain.value.replace('_', ' ')}")
                if len(suggestions) >= 3:
                    break
        
        return suggestions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "overall_level": self.overall_level.value,
            "overall_score": round(self.overall_score, 2),
            "skills": {k.value: v.to_dict() for k, v in self.skills.items()},
            "preferences": self.preferences,
            "feature_usage": self.feature_usage,
            "ui_recommendations": self.get_ui_recommendations(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class SkillProfileService:
    """
    Service for managing user skill profiles.
    """
    
    def __init__(self, db_service=None):
        self.db = db_service
        self._cache: Dict[str, UserSkillProfile] = {}
    
    def get_profile(self, user_id: str, org_id: str) -> UserSkillProfile:
        """Get or create a user skill profile."""
        cache_key = f"{org_id}:{user_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Create new profile
        profile = UserSkillProfile(user_id=user_id, org_id=org_id)
        self._cache[cache_key] = profile
        return profile
    
    def update_from_verification(
        self,
        user_id: str,
        org_id: str,
        verification_passed: bool,
        confidence: float
    ):
        """Update profile based on verification outcome."""
        profile = self.get_profile(user_id, org_id)
        
        # Calculate performance signal
        signal = confidence * 100 if verification_passed else (1 - confidence) * 50
        
        profile.update_skill(SkillDomain.VERIFICATION, signal)
        profile.update_skill(SkillDomain.CODE_REVIEW, signal * 0.8)
    
    def update_from_intent(
        self,
        user_id: str,
        org_id: str,
        intent_complexity: int,
        parse_success: bool
    ):
        """Update profile based on intent parsing."""
        profile = self.get_profile(user_id, org_id)
        
        # Higher complexity successful intents = higher skill
        signal = min(100, intent_complexity * 10) if parse_success else 30
        
        profile.update_skill(SkillDomain.INTENT_AUTHORING, signal)
    
    def record_feature_use(
        self,
        user_id: str,
        org_id: str,
        feature: str
    ):
        """Record feature usage for learning preferences."""
        profile = self.get_profile(user_id, org_id)
        profile.record_feature_usage(feature)


# Global service instance
_skill_service: Optional[SkillProfileService] = None


def get_skill_service(db_service=None) -> SkillProfileService:
    """Get or create the skill profile service."""
    global _skill_service
    if _skill_service is None:
        _skill_service = SkillProfileService(db_service)
    return _skill_service
