"""
Pinecone vector store integration for legal document retrieval and semantic search.
"""
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PineconeVectorStore:
    """
    Vector store for legal documents, case law, and firm knowledge base.
    Uses Pinecone for semantic search and similarity matching.
    """
    
    def __init__(
        self,
        api_key: str,
        environment: str = "us-west-2",
        index_name: str = "legal-assistant-index",
        dimension: int = 1536,  # OpenAI embeddings dimension
    ):
        """
        Initialize Pinecone vector store.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the Pinecone index
            dimension: Embedding dimension
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.index = None
        self._initialized = False
    
    def _initialize(self):
        """Lazy initialization of Pinecone client."""
        if self._initialized:
            return
        
        try:
            from pinecone import Pinecone, ServerlessSpec
            
            # Initialize Pinecone client
            pc = Pinecone(api_key=self.api_key)
            
            # Create index if it doesn't exist
            existing_indexes = pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating index: {self.index_name}")
                pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment
                    )
                )
            
            # Connect to index
            self.index = pc.Index(self.index_name)
            self._initialized = True
            
        except ImportError:
            logger.error("pinecone-client not installed. Install with: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            from langchain_openai import OpenAIEmbeddings
            
            embeddings = OpenAIEmbeddings()
            return embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _generate_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate unique ID for vector based on content and metadata."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{metadata.get('type', 'doc')}_{content_hash[:16]}"
    
    def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        id: Optional[str] = None,
    ) -> str:
        """
        Add a document to the vector store.
        
        Args:
            content: Document text content
            metadata: Document metadata (type, matter_id, jurisdiction, etc.)
            id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        self._initialize()
        
        doc_id = id or self._generate_id(content, metadata)
        
        # Generate embedding
        embedding = self._get_embedding(content)
        
        # Add metadata
        full_metadata = {
            **metadata,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Upsert to Pinecone
        self.index.upsert(
            vectors=[(doc_id, embedding, full_metadata)]
        )
        
        logger.info(f"Added document to vector store: {doc_id}")
        return doc_id
    
    def add_documents(
        self,
        documents: List[Tuple[str, Dict[str, Any], Optional[str]]],
        batch_size: int = 100,
    ) -> List[str]:
        """
        Add multiple documents to the vector store.
        
        Args:
            documents: List of (content, metadata, id) tuples
            batch_size: Batch size for upserts
            
        Returns:
            List of document IDs
        """
        self._initialize()
        
        doc_ids = []
        batch = []
        
        for i, (content, metadata, doc_id) in enumerate(documents):
            doc_id = doc_id or self._generate_id(content, metadata)
            doc_ids.append(doc_id)
            
            embedding = self._get_embedding(content)
            full_metadata = {
                **metadata,
                "content": content,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            batch.append((doc_id, embedding, full_metadata))
            
            # Upsert batch
            if len(batch) >= batch_size or i == len(documents) - 1:
                self.index.upsert(vectors=batch)
                batch = []
        
        logger.info(f"Added {len(doc_ids)} documents to vector store")
        return doc_ids
    
    def search(
        self,
        query: str,
        filter: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            filter: Metadata filter (e.g., {"matter_id": "123"})
            top_k: Number of results to return
            include_metadata: Include metadata in results
            
        Returns:
            List of matching documents with scores
        """
        self._initialize()
        
        # Generate query embedding
        query_embedding = self._get_embedding(query)
        
        # Search
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            include_metadata=include_metadata,
            include_values=False,
        )
        
        # Format results
        formatted_results = []
        for match in results.matches:
            result = {
                "id": match.id,
                "score": match.score,
                "content": match.metadata.get("content", ""),
                "metadata": {k: v for k, v in match.metadata.items() if k != "content"},
            }
            formatted_results.append(result)
        
        return formatted_results
    
    def search_by_matter(
        self,
        matter_id: str,
        query: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search documents within a specific matter.
        
        Args:
            matter_id: Matter ID to filter by
            query: Optional query text (if None, returns all documents)
            top_k: Number of results to return
            
        Returns:
            List of matching documents
        """
        filter = {"matter_id": matter_id}
        
        if query:
            return self.search(query, filter=filter, top_k=top_k)
        else:
            # Return all documents for matter
            self._initialize()
            results = self.index.query(
                vector=[0.0] * self.dimension,
                filter=filter,
                top_k=top_k,
                include_metadata=True,
            )
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "content": match.metadata.get("content", ""),
                    "metadata": {k: v for k, v in match.metadata.items() if k != "content"},
                }
                for match in results.matches
            ]
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted successfully
        """
        self._initialize()
        self.index.delete(ids=[doc_id])
        logger.info(f"Deleted document from vector store: {doc_id}")
        return True
    
    def delete_by_matter(self, matter_id: str) -> int:
        """
        Delete all documents for a matter.
        
        Args:
            matter_id: Matter ID to delete
            
        Returns:
            Number of documents deleted
        """
        self._initialize()
        
        # Get all document IDs for matter
        results = self.search_by_matter(matter_id, top_k=10000)
        doc_ids = [r["id"] for r in results]
        
        if doc_ids:
            self.index.delete(ids=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents for matter: {matter_id}")
        
        return len(doc_ids)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Statistics about the index
        """
        self._initialize()
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "dimension": stats.get("dimension", self.dimension),
                "total_vectors": stats.get("total_vector_count", 0),
                "index_name": self.index_name,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "dimension": self.dimension,
                "total_vectors": 0,
                "index_name": self.index_name,
                "error": str(e),
            }


# ============================================================
# LangChain Integration
# ============================================================

class LangChainPineconeVectorStore:
    """
    LangChain-compatible vector store wrapper.
    """
    
    def __init__(self, pinecone_store: PineconeVectorStore):
        self.pinecone_store = pinecone_store
    
    def similarity_search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search.
        
        Args:
            query: Search query
            k: Number of results
            filter: Metadata filter
            
        Returns:
            List of matching documents
        """
        return self.pinecone_store.search(query, filter=filter, top_k=k)
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: List of metadata dicts
            ids: List of IDs
            
        Returns:
            List of document IDs
        """
        metadatas = metadatas or [{}] * len(texts)
        ids = ids or [None] * len(texts)
        
        documents = list(zip(texts, metadatas, ids))
        return self.pinecone_store.add_documents(documents)


# ============================================================
# Factory Function
# ============================================================

def create_vector_store(
    api_key: str,
    environment: str = "us-west-2",
    index_name: str = "legal-assistant-index",
) -> PineconeVectorStore:
    """
    Create a Pinecone vector store instance.
    
    Args:
        api_key: Pinecone API key
        environment: Pinecone environment
        index_name: Index name
        
    Returns:
        Initialized PineconeVectorStore
    """
    return PineconeVectorStore(
        api_key=api_key,
        environment=environment,
        index_name=index_name,
    )
