"""
SDO History System for Undo/Rollback

Manages snapshots of SDO state for reversible operations.
Each modification creates a snapshot that can be restored.
"""
import json
import uuid
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class Snapshot:
    """A point-in-time snapshot of an SDO."""
    id: str
    sdo_id: str
    timestamp: float
    operation: str  # What operation created this snapshot
    state: Dict[str, Any]  # Serialized SDO state
    parent_id: Optional[str] = None  # Previous snapshot in chain
    
    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Snapshot':
        return cls(**data)


class SDOHistory:
    """
    Manages SDO state history for undo/redo operations.
    
    Features:
    - Automatic snapshots before state changes
    - Linked snapshot chain for multi-level undo
    - Persistence to disk
    - Memory limit with LRU eviction
    
    Usage:
        history = SDOHistory()
        
        # Before modifying SDO
        history.snapshot(sdo, "generate_candidates")
        
        # To undo
        previous_state = history.undo(sdo.id)
        sdo = SDO(**previous_state)
    """
    
    def __init__(
        self, 
        persistence_dir: Optional[str] = None,
        max_snapshots_per_sdo: int = 10
    ):
        self.persistence_dir = persistence_dir
        self.max_snapshots = max_snapshots_per_sdo
        
        # In-memory cache: sdo_id -> [snapshots] (newest first)
        self._cache: Dict[str, List[Snapshot]] = {}
        
        # Current position for redo: sdo_id -> snapshot_id
        self._current: Dict[str, str] = {}
        
        if persistence_dir:
            Path(persistence_dir).mkdir(parents=True, exist_ok=True)
    
    def snapshot(self, sdo, operation: str) -> str:
        """
        Create a snapshot of the current SDO state.
        
        Args:
            sdo: The SDO object to snapshot
            operation: Description of the operation about to be performed
        
        Returns:
            Snapshot ID
        """
        sdo_id = sdo.id
        
        # Get current snapshot (if any) as parent
        parent_id = self._current.get(sdo_id)
        
        # Create snapshot
        snapshot = Snapshot(
            id=str(uuid.uuid4()),
            sdo_id=sdo_id,
            timestamp=time.time(),
            operation=operation,
            state=self._serialize_sdo(sdo),
            parent_id=parent_id
        )
        
        # Add to cache
        if sdo_id not in self._cache:
            self._cache[sdo_id] = []
        
        self._cache[sdo_id].insert(0, snapshot)  # Newest first
        self._current[sdo_id] = snapshot.id
        
        # Enforce limit
        if len(self._cache[sdo_id]) > self.max_snapshots:
            self._cache[sdo_id] = self._cache[sdo_id][:self.max_snapshots]
        
        # Persist if enabled
        if self.persistence_dir:
            self._persist_snapshot(snapshot)
        
        return snapshot.id
    
    def undo(self, sdo_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore previous state.
        
        Returns:
            Previous state dict, or None if no history
        """
        snapshots = self._cache.get(sdo_id, [])
        if len(snapshots) < 2:
            return None  # Need at least 2: current + previous
        
        # Get current and move to previous
        current_idx = 0
        current_snapshot = snapshots[current_idx]
        
        if current_idx + 1 >= len(snapshots):
            return None
        
        previous_snapshot = snapshots[current_idx + 1]
        self._current[sdo_id] = previous_snapshot.id
        
        return previous_snapshot.state
    
    def redo(self, sdo_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore next state (after undo).
        
        Returns:
            Next state dict, or None if at latest
        """
        snapshots = self._cache.get(sdo_id, [])
        current_id = self._current.get(sdo_id)
        
        if not current_id or not snapshots:
            return None
        
        # Find current position
        for i, snap in enumerate(snapshots):
            if snap.id == current_id and i > 0:
                # Move forward
                next_snapshot = snapshots[i - 1]
                self._current[sdo_id] = next_snapshot.id
                return next_snapshot.state
        
        return None  # Already at latest
    
    def list_snapshots(self, sdo_id: str) -> List[dict]:
        """Get all snapshots for an SDO."""
        snapshots = self._cache.get(sdo_id, [])
        current_id = self._current.get(sdo_id)
        
        return [
            {
                "id": s.id,
                "operation": s.operation,
                "created_at": s.created_at.isoformat(),
                "is_current": s.id == current_id
            }
            for s in snapshots
        ]
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific snapshot's state."""
        for snapshots in self._cache.values():
            for snap in snapshots:
                if snap.id == snapshot_id:
                    return snap.state
        return None
    
    def restore(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore to a specific snapshot.
        
        Returns:
            State dict, or None if snapshot not found
        """
        for sdo_id, snapshots in self._cache.items():
            for snap in snapshots:
                if snap.id == snapshot_id:
                    self._current[sdo_id] = snapshot_id
                    return snap.state
        return None
    
    def clear(self, sdo_id: str):
        """Clear all snapshots for an SDO."""
        if sdo_id in self._cache:
            del self._cache[sdo_id]
        if sdo_id in self._current:
            del self._current[sdo_id]
    
    def _serialize_sdo(self, sdo) -> Dict[str, Any]:
        """Serialize SDO to dict (handles Pydantic models)."""
        if hasattr(sdo, 'model_dump'):
            return sdo.model_dump()
        elif hasattr(sdo, 'dict'):
            return sdo.dict()
        elif hasattr(sdo, '__dict__'):
            return {k: v for k, v in sdo.__dict__.items() if not k.startswith('_')}
        else:
            raise ValueError(f"Cannot serialize SDO: {type(sdo)}")
    
    def _persist_snapshot(self, snapshot: Snapshot):
        """Save snapshot to disk."""
        if not self.persistence_dir:
            return
        
        sdo_dir = Path(self.persistence_dir) / snapshot.sdo_id
        sdo_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = sdo_dir / f"{snapshot.id}.json"
        with open(filepath, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)
    
    def load_history(self, sdo_id: str):
        """Load snapshots from disk for an SDO."""
        if not self.persistence_dir:
            return
        
        sdo_dir = Path(self.persistence_dir) / sdo_id
        if not sdo_dir.exists():
            return
        
        snapshots = []
        for filepath in sdo_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                snapshots.append(Snapshot.from_dict(data))
            except Exception as e:
                print(f"Failed to load snapshot {filepath}: {e}")
        
        # Sort by timestamp (newest first)
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        self._cache[sdo_id] = snapshots
        
        if snapshots:
            self._current[sdo_id] = snapshots[0].id


class SDOHistoryManager:
    """
    Global history manager with singleton pattern.
    Use for consistent history across the application.
    """
    _instance: Optional['SDOHistoryManager'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persistence_dir: Optional[str] = None):
        if self._initialized:
            return
        
        self.history = SDOHistory(persistence_dir=persistence_dir)
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'SDOHistoryManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
