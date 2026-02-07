"""
Lesson Store

Manages persistence and retrieval of learned lessons (constraints).
Lessons are generalized rules derived from past failures/successes.
"""
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

@dataclass
class Lesson:
    """A learned lesson/constraint."""
    id: str
    intent_pattern: str # Keyword or regex or semantic embedding key
    constraint: str
    source_ivcu_id: str
    created_at: str
    confidence: float = 1.0

class LessonStore:
    """
    Store for learned lessons.
    Currently uses simple keyword matching. In production, use Vector DB.
    """
    
    def __init__(self):
        self._lessons: List[Lesson] = []
        
    def add_lesson(self, intent_pattern: str, constraint: str, source_ivcu_id: str):
        """Add a new lesson."""
        lesson = Lesson(
            id=str(uuid.uuid4()),
            intent_pattern=intent_pattern.lower(),
            constraint=constraint,
            source_ivcu_id=source_ivcu_id,
            created_at=datetime.utcnow().isoformat()
        )
        self._lessons.append(lesson)
        print(f"LESSON LEARNED: [{intent_pattern}] -> {constraint}")
        
    def get_relevant_lessons(self, current_intent: str) -> List[str]:
        """
        Retrieve lessons relevant to the current intent.
        
        Args:
            current_intent: The intent text to match against.
            
        Returns:
            List of constraint strings to inject into the prompt.
        """
        relevant = []
        intent_lower = current_intent.lower()
        
        for lesson in self._lessons:
            # Simple keyword overlap (very basic "semantic" approximation)
            # If the lesson's pattern words appear in the current intent
            keywords = lesson.intent_pattern.split()
            match = any(k in intent_lower for k in keywords if len(k) > 3)
            
            if match or lesson.intent_pattern == "*":
                relevant.append(lesson.constraint)
                
        return list(set(relevant)) # Dedupe

# Singleton
_lesson_store = LessonStore()

def get_lesson_store() -> LessonStore:
    return _lesson_store
