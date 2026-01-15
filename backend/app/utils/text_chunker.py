"""
Text chunking utility for processing large documents with LLMs.

Implements smart chunking with:
- Token-aware chunking (respects model token limits)
- Overlapping chunks (preserves context)
- Natural boundary detection (paragraphs, sentences)
- Hierarchical summarization (map-reduce pattern)
"""

from typing import List, Dict, Any
import re
from app.utils.logger import logger


class TextChunker:
    """Smart text chunking for LLM processing."""
    
    def __init__(self, max_tokens: int = 6000, overlap_tokens: int = 500):
        """
        Initialize the chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk (leave room for system prompt)
            overlap_tokens: Number of tokens to overlap between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        # Rough approximation: 1 token ≈ 4 characters for English
        self.chars_per_token = 4
        self.max_chars = max_tokens * self.chars_per_token
        self.overlap_chars = overlap_tokens * self.chars_per_token
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 chars per token for English
        # More accurate would use tiktoken, but this avoids dependency
        return len(text) // self.chars_per_token
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of chunks with metadata
        """
        if not text:
            return []
        
        # Check if chunking is needed
        estimated_tokens = self.estimate_tokens(text)
        if estimated_tokens <= self.max_tokens:
            logger.info(f"Text is {estimated_tokens} tokens, no chunking needed")
            return [{
                'text': text,
                'chunk_index': 0,
                'total_chunks': 1,
                'start_pos': 0,
                'end_pos': len(text),
                'estimated_tokens': estimated_tokens
            }]
        
        logger.info(f"Text is {estimated_tokens} tokens, chunking with overlap")
        
        # Split into paragraphs first (natural boundaries)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_start_pos = 0
        
        for para_idx, para in enumerate(paragraphs):
            para_length = len(para)
            
            # If single paragraph exceeds max, split by sentences
            if para_length > self.max_chars:
                # If we have accumulated content, save it first
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'chunk_index': len(chunks),
                        'start_pos': chunk_start_pos,
                        'end_pos': chunk_start_pos + len(chunk_text),
                        'estimated_tokens': self.estimate_tokens(chunk_text)
                    })
                    current_chunk = []
                    current_length = 0
                
                # Split long paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if current_length + len(sentence) > self.max_chars:
                        if current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            chunks.append({
                                'text': chunk_text,
                                'chunk_index': len(chunks),
                                'start_pos': chunk_start_pos,
                                'end_pos': chunk_start_pos + len(chunk_text),
                                'estimated_tokens': self.estimate_tokens(chunk_text)
                            })
                            
                            # Add overlap from previous chunk
                            overlap_text = self._get_overlap(chunk_text)
                            current_chunk = [overlap_text] if overlap_text else []
                            current_length = len(overlap_text) if overlap_text else 0
                            chunk_start_pos += len(chunk_text) - current_length
                        
                        current_chunk.append(sentence)
                        current_length += len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_length += len(sentence)
            
            # Normal paragraph processing
            elif current_length + para_length > self.max_chars:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': len(chunks),
                    'start_pos': chunk_start_pos,
                    'end_pos': chunk_start_pos + len(chunk_text),
                    'estimated_tokens': self.estimate_tokens(chunk_text)
                })
                
                # Start new chunk with overlap from previous
                overlap_text = self._get_overlap(chunk_text)
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_length = len(overlap_text) + para_length if overlap_text else para_length
                chunk_start_pos += len(chunk_text) - (len(overlap_text) if overlap_text else 0)
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': len(chunks),
                'start_pos': chunk_start_pos,
                'end_pos': chunk_start_pos + len(chunk_text),
                'estimated_tokens': self.estimate_tokens(chunk_text)
            })
        
        # Add total_chunks to all chunks
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)
        
        logger.info(f"Created {len(chunks)} chunks with overlap")
        return chunks
    
    def _get_overlap(self, text: str) -> str:
        """
        Get overlap text from end of previous chunk.
        
        Args:
            text: Previous chunk text
            
        Returns:
            Overlap text for next chunk
        """
        if len(text) <= self.overlap_chars:
            return text
        
        # Get last N characters, but try to break at sentence boundary
        overlap_text = text[-self.overlap_chars:]
        
        # Find last sentence boundary in overlap
        last_sentence = overlap_text.rfind('. ')
        if last_sentence > self.overlap_chars // 2:  # At least half the overlap
            overlap_text = overlap_text[last_sentence + 2:]
        
        return overlap_text.strip()


def chunk_and_summarize(text: str, llm_manager, topic: str = "document") -> str:
    """
    Chunk large text and create hierarchical summaries (map-reduce pattern).
    
    Args:
        text: Input text to process
        llm_manager: LLM manager for generating summaries
        topic: Topic/category for better summarization
        
    Returns:
        Final combined summary
    """
    chunker = TextChunker(max_tokens=6000, overlap_tokens=500)
    chunks = chunker.chunk_text(text)
    
    if len(chunks) == 1:
        # No chunking needed, return original text
        return text
    
    logger.info(f"Processing {len(chunks)} chunks for {topic}")
    
    # Phase 1: Map - Summarize each chunk
    chunk_summaries = []
    for chunk in chunks:
        chunk_idx = chunk['chunk_index']
        total = chunk['total_chunks']
        
        prompt = f"""Summarize the following section of a {topic} (chunk {chunk_idx + 1}/{total}).
IMPORTANT: Preserve all specific financial figures, numbers, and tables. 
Do not generalize numerical data. If you see a table, keep its key values.

{chunk['text']}

Provide a data-rich summary of the key points and specific figures in this section."""

        result = llm_manager.generate(prompt, temperature=0.3, max_tokens=1000)
        
        if result.get('success'):
            summary = result.get('text', '').strip()
            chunk_summaries.append({
                'chunk_index': chunk_idx,
                'summary': summary
            })
            logger.info(f"Summarized chunk {chunk_idx + 1}/{total}")
        else:
            logger.warning(f"Failed to summarize chunk {chunk_idx + 1}/{total}")
    
    # Phase 2: Reduce - Combine all summaries
    if not chunk_summaries:
        return text[:10000]  # Fallback to truncated text
    
    combined_summaries = "\n\n".join([
        f"Section {s['chunk_index'] + 1}:\n{s['summary']}" 
        for s in chunk_summaries
    ])
    
    # If combined summaries are still too long, summarize again
    if chunker.estimate_tokens(combined_summaries) > 6000:
        logger.info("Combined summaries too long, creating final summary")
        
        final_prompt = f"""The following are summaries of different sections of a {topic}.
Create a comprehensive final summary that captures all key information.

{combined_summaries}

Provide a cohesive summary of the entire document."""

        result = llm_manager.generate(final_prompt, temperature=0.3, max_tokens=2000)
        
        if result.get('success'):
            return result.get('text', '').strip()
    
    return combined_summaries
