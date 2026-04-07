"""
Vector Memory Store for DCF Valuation Agent
Provides semantic memory storage and retrieval using embeddings
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
import uuid
import os

logger = logging.getLogger(__name__)

# Try to import ChromaDB, fallback to simple storage if not available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, using fallback memory storage")


@dataclass
class MemoryEntry:
    """A single memory entry"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    last_accessed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            embedding=data.get('embedding'),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            access_count=data.get('access_count', 0),
            last_accessed=data.get('last_accessed')
        )


class VectorMemoryStore:
    """
    Vector-based memory store for DCF Agent
    
    Features:
    - Semantic search using embeddings
    - Company-specific memory tracking
    - Analysis history persistence
    - Cross-session memory retention
    
    Uses ChromaDB for vector storage when available, falls back to SQLite
    """
    
    COLLECTION_NAME = "dcf_agent_memory"
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize the vector memory store
        
        Args:
            persist_directory: Directory to persist data. If None, uses default
        """
        self.persist_directory = persist_directory or os.path.join(
            os.path.dirname(__file__), '../../data/memory'
        )
        os.makedirs(self.persist_directory, exist_ok=True)
        
        if CHROMADB_AVAILABLE:
            self._init_chroma()
        else:
            self._init_fallback()
        
        logger.info(f"VectorMemoryStore initialized at {self.persist_directory}")
    
    def _init_chroma(self):
        """Initialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "DCF Agent memory store"}
            )
        except Exception as e:
            logger.warning(f"Failed to get collection, recreating: {e}")
            self.client.delete_collection(self.COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME
            )
        
        self._use_chroma = True
        logger.info("Using ChromaDB for vector storage")
    
    def _init_fallback(self):
        """Initialize fallback storage (JSON file based)"""
        self.fallback_file = os.path.join(self.persist_directory, 'memory_store.json')
        self._memories: Dict[str, MemoryEntry] = {}
        self._load_fallback()
        self._use_chroma = False
        logger.info("Using fallback JSON storage")
    
    def _load_fallback(self):
        """Load fallback storage from file"""
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._memories = {
                        k: MemoryEntry.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                logger.error(f"Failed to load fallback storage: {e}")
                self._memories = {}
    
    def _save_fallback(self):
        """Save fallback storage to file"""
        try:
            with open(self.fallback_file, 'w', encoding='utf-8') as f:
                data = {k: v.to_dict() for k, v in self._memories.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fallback storage: {e}")
    
    # =========================================================================
    # Core Memory Operations
    # =========================================================================
    
    def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a new memory entry
        
        Args:
            content: Text content to store
            metadata: Associated metadata (ticker, timestamp, etc.)
            
        Returns:
            Memory entry ID
        """
        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata or {}
        )
        
        if self._use_chroma:
            self._add_chroma(entry)
        else:
            self._memories[memory_id] = entry
            self._save_fallback()
        
        logger.debug(f"Added memory: {memory_id}")
        return memory_id
    
    def _add_chroma(self, entry: MemoryEntry):
        """Add entry to ChromaDB"""
        self.collection.add(
            ids=[entry.id],
            documents=[entry.content],
            metadatas=[entry.metadata]
        )
    
    def add_analysis(self, analysis: Dict[str, Any]) -> str:
        """
        Add a complete analysis result to memory
        
        This is the primary method for storing valuation analyses
        """
        # Generate searchable content
        content = self._generate_analysis_content(analysis)
        
        metadata = {
            'type': 'analysis',
            'ticker': analysis.get('ticker', 'UNKNOWN'),
            'company_name': analysis.get('company_name', ''),
            'industry': analysis.get('industry', ''),
            'action': analysis.get('action', 'UNKNOWN'),
            'upside_percent': analysis.get('upside_percent', 0),
            'confidence': analysis.get('confidence', 'unknown'),
            'timestamp': analysis.get('timestamp', datetime.now().isoformat()),
            'valuation_method': analysis.get('primary_method', 'unknown')
        }
        
        return self.add(content, metadata)
    
    def _generate_analysis_content(self, analysis: Dict) -> str:
        """Generate searchable text from analysis data"""
        parts = [
            f"Stock: {analysis.get('ticker')} - {analysis.get('company_name', '')}",
            f"Industry: {analysis.get('industry', 'Unknown')}",
            f"Valuation Method: {analysis.get('primary_method', 'Unknown')}",
            f"Investment Action: {analysis.get('action', 'Unknown')}",
            f"Upside: {analysis.get('upside_percent', 0):.1f}%",
            f"Confidence: {analysis.get('confidence', 'Unknown')}",
            f"Fair Value: ${analysis.get('fair_value', 0):.2f}" if analysis.get('fair_value') else "",
            f"Current Price: ${analysis.get('current_price', 0):.2f}" if analysis.get('current_price') else "",
        ]
        
        # Add reasoning if available
        if analysis.get('reasoning'):
            parts.append(f"Reasoning: {analysis['reasoning']}")
        
        # Add warnings
        if analysis.get('warnings'):
            parts.append(f"Warnings: {', '.join(analysis['warnings'])}")
        
        return '\n'.join(filter(None, parts))
    
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID"""
        if self._use_chroma:
            return self._get_chroma(memory_id)
        else:
            entry = self._memories.get(memory_id)
            if entry:
                entry.access_count += 1
                entry.last_accessed = datetime.now().isoformat()
            return entry
    
    def _get_chroma(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get entry from ChromaDB"""
        try:
            results = self.collection.get(ids=[memory_id])
            if results['ids']:
                return MemoryEntry(
                    id=results['ids'][0],
                    content=results['documents'][0],
                    metadata=results['metadatas'][0] if results['metadatas'] else {}
                )
        except Exception as e:
            logger.error(f"Failed to get from ChromaDB: {e}")
        return None
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry"""
        if self._use_chroma:
            try:
                self.collection.delete(ids=[memory_id])
                return True
            except Exception as e:
                logger.error(f"Failed to delete from ChromaDB: {e}")
                return False
        else:
            if memory_id in self._memories:
                del self._memories[memory_id]
                self._save_fallback()
                return True
            return False
    
    # =========================================================================
    # Semantic Search
    # =========================================================================
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Dict[str, Any] = None
    ) -> List[MemoryEntry]:
        """
        Semantic search for similar memories
        
        Args:
            query: Search query text
            n_results: Maximum number of results
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching MemoryEntry objects
        """
        if self._use_chroma:
            return self._search_chroma(query, n_results, filter_metadata)
        else:
            return self._search_fallback(query, n_results)
    
    def _search_chroma(
        self,
        query: str,
        n_results: int,
        filter_metadata: Dict[str, Any] = None
    ) -> List[MemoryEntry]:
        """Search using ChromaDB"""
        try:
            where_clause = filter_metadata if filter_metadata else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
            
            entries = []
            if results['ids']:
                for i, mem_id in enumerate(results['ids']):
                    entries.append(MemoryEntry(
                        id=mem_id,
                        content=results['documents'][i],
                        metadata=results['metadatas'][i] if results['metadatas'] else {},
                        embedding=results.get('embeddings', [[]])[0] if results.get('embeddings') else None
                    ))
            
            return entries
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    def _search_fallback(self, query: str, n_results: int) -> List[MemoryEntry]:
        """Simple keyword-based fallback search"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored = []
        for entry in self._memories.values():
            content_lower = entry.content.lower()
            # Simple scoring based on word matches
            matches = sum(1 for word in query_words if word in content_lower)
            if matches > 0:
                scored.append((matches, entry))
        
        scored.sort(key=lambda x: -x[0])
        return [entry for _, entry in scored[:n_results]]
    
    def retrieve_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve similar analyses
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of analysis dictionaries with similarity info
        """
        entries = self.search(query, n_results=limit)
        
        results = []
        for entry in entries:
            results.append({
                'memory_id': entry.id,
                'content': entry.content,
                'metadata': entry.metadata,
                'similarity_score': 1.0,  # ChromaDB doesn't return scores by default
                'created_at': entry.created_at
            })
        
        return results
    
    # =========================================================================
    # Specialized Retrieval Methods
    # =========================================================================
    
    def get_company_history(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get analysis history for a specific company"""
        entries = self.search(
            f"{ticker} analysis valuation",
            n_results=limit,
            filter_metadata={'ticker': ticker}
        )
        
        return [
            {
                'memory_id': e.id,
                'analysis': e.metadata,
                'content': e.content,
                'created_at': e.created_at
            }
            for e in entries
        ]
    
    def get_insights(self, ticker: str) -> Dict[str, Any]:
        """
        Get aggregated insights for a company based on historical analyses
        """
        history = self.get_company_history(ticker, limit=20)
        
        if not history:
            return {
                'has_history': False,
                'message': 'No historical analysis found'
            }
        
        # Aggregate insights
        actions = [h['analysis'].get('action') for h in history if h['analysis'].get('action')]
        confidences = [h['analysis'].get('confidence') for h in history if h['analysis'].get('confidence')]
        
        # Count action distribution
        action_counts = {}
        for action in actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Calculate average metrics
        upsides = [h['analysis'].get('upside_percent', 0) for h in history]
        avg_upside = sum(upsides) / len(upsides) if upsides else 0
        
        return {
            'has_history': True,
            'analysis_count': len(history),
            'action_distribution': action_counts,
            'average_upside': avg_upside,
            'confidence_trend': confidences[-1] if confidences else 'unknown',
            'latest_analysis': history[0] if history else None,
            'similar_cases': self._find_similar_outcomes(ticker, history)
        }
    
    def _find_similar_outcomes(self, current_ticker: str, history: List) -> List[Dict]:
        """Find cases with similar characteristics that have resolved"""
        # This would require tracking actual outcomes
        # Simplified implementation
        return []
    
    def get_sector_insights(self, sector: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get insights for a sector/industry"""
        entries = self.search(
            f"{sector} industry valuation",
            n_results=limit,
            filter_metadata={'industry': sector}
        )
        
        return [
            {
                'memory_id': e.id,
                'metadata': e.metadata,
                'content': e.content
            }
            for e in entries
        ]
    
    # =========================================================================
    # Memory Management
    # =========================================================================
    
    def update(self, memory_id: str, content: str = None, metadata: Dict = None) -> bool:
        """Update an existing memory entry"""
        entry = self.get(memory_id)
        if not entry:
            return False
        
        if content:
            entry.content = content
        if metadata:
            entry.metadata.update(metadata)
        
        entry.updated_at = datetime.now().isoformat()
        
        if self._use_chroma:
            try:
                self.collection.update(
                    ids=[memory_id],
                    documents=[entry.content],
                    metadatas=[entry.metadata]
                )
                return True
            except Exception as e:
                logger.error(f"Failed to update in ChromaDB: {e}")
                return False
        else:
            self._memories[memory_id] = entry
            self._save_fallback()
            return True
    
    def clear(self, older_than: datetime = None) -> int:
        """
        Clear memories, optionally only those older than a date
        
        Args:
            older_than: Optional datetime threshold
            
        Returns:
            Number of entries cleared
        """
        if self._use_chroma:
            try:
                if older_than:
                    # ChromaDB doesn't support datetime comparison directly
                    # Would need to filter by metadata timestamp
                    pass
                else:
                    self.client.delete_collection(self.COLLECTION_NAME)
                    self.collection = self.client.get_or_create_collection(self.COLLECTION_NAME)
                return 0  # Cannot accurately count
            except Exception as e:
                logger.error(f"Failed to clear ChromaDB: {e}")
                return 0
        else:
            if older_than:
                threshold = older_than.isoformat()
                to_delete = [
                    k for k, v in self._memories.items()
                    if v.created_at < threshold
                ]
                for k in to_delete:
                    del self._memories[k]
                self._save_fallback()
                return len(to_delete)
            else:
                count = len(self._memories)
                self._memories.clear()
                self._save_fallback()
                return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        if self._use_chroma:
            count = self.collection.count()
        else:
            count = len(self._memories)
        
        return {
            'total_entries': count,
            'storage_type': 'chromadb' if self._use_chroma else 'json_fallback',
            'persist_directory': self.persist_directory,
            'collection_name': self.COLLECTION_NAME
        }


# =============================================================================
# Global Memory Instance
# =============================================================================

# Lazy initialization to avoid import issues
_memory_store: Optional[VectorMemoryStore] = None


def get_memory_store() -> VectorMemoryStore:
    """Get or create the global memory store instance"""
    global _memory_store
    if _memory_store is None:
        _memory_store = VectorMemoryStore()
    return _memory_store


def initialize_memory(persist_directory: str = None) -> VectorMemoryStore:
    """Explicitly initialize the memory store"""
    global _memory_store
    _memory_store = VectorMemoryStore(persist_directory)
    return _memory_store
