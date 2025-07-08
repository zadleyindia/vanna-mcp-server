"""
Embedding service for generating text embeddings
"""
import logging
from typing import List, Optional
import asyncio

from openai import AsyncOpenAI
from ..config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        
        if not text:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [t for t in texts if t]
        if not valid_texts:
            return [[]] * len(texts)
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=valid_texts
            )
            
            # Map results back to original order
            embeddings = []
            valid_idx = 0
            
            for text in texts:
                if text:
                    embeddings.append(response.data[valid_idx].embedding)
                    valid_idx += 1
                else:
                    embeddings.append([])
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise