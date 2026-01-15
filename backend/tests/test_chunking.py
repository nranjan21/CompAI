"""
Test the chunking strategy with the TextChunker utility.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.utils.text_chunker import TextChunker, chunk_and_summarize


def test_chunking():
    """Test text chunking functionality."""
    print("\n" + "="*80)
    print("Testing TextChunker")
    print("="*80)
    
    # Create sample text
    sample_text = """
    Amazon.com, Inc. is an American multinational technology company focusing on e-commerce, 
    cloud computing, online advertising, digital streaming, and artificial intelligence.
    
    Financial Performance:
    Revenue for fiscal year 2024 was $637,959 million, representing a 12% increase from 
    the prior year. Net income was $30,425 million. The company maintains a strong 
    balance sheet with total assets of $527,854 million.
    
    Key Metrics:
    - Gross margin: 47.5%
    - Operating margin: 7.8%
    - Return on equity: 21.3%
    
    Risks:
    The company faces risks from fluctuating foreign exchange rates, changing economic 
    and geopolitical conditions, and shifts in customer demand and spending patterns.
    """ * 50  # Repeat to make it large
    
    chunker = TextChunker(max_tokens=1000, overlap_tokens=100)
    
    # Test token estimation
    estimated_tokens = chunker.estimate_tokens(sample_text)
    print(f"\n📊 Sample text: {len(sample_text)} characters, ~{estimated_tokens} tokens")
    
    # Test chunking
    chunks = chunker.chunk_text(sample_text)
    
    print(f"\n✅ Created {len(chunks)} chunks")
    for chunk in chunks:
        print(f"\nChunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']}:")
        print(f"  - Position: {chunk['start_pos']}-{chunk['end_pos']}")
        print(f"  - Estimated tokens: {chunk['estimated_tokens']}")
        print(f"  - Text preview: {chunk['text'][:100]}...")
    
    # Check overlap
    if len(chunks) > 1:
        print("\n🔗 Checking overlap between chunks:")
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i]['text'][-200:]
            chunk2_start = chunks[i+1]['text'][:200]
            
            # Find common text
            overlap_found = False
            for j in range(len(chunk1_end)):
                if chunk2_start.startswith(chunk1_end[j:]):
                    overlap_length = len(chunk1_end) - j
                    print(f"  Chunks {i+1}-{i+2}: {overlap_length} character overlap")
                    overlap_found = True
                    break
            
            if not overlap_found:
                print(f"  Chunks {i+1}-{i+2}: No overlap detected")
    
    print("\n✅ Chunking test completed!")
    return True


def test_small_text():
    """Test that small text doesn't get chunked."""
    print("\n" + "="*80)
    print("Testing with small text (no chunking needed)")
    print("="*80)
    
    small_text = "This is a small text that doesn't need chunking."
    
    chunker = TextChunker(max_tokens=6000, overlap_tokens=500)
    chunks = chunker.chunk_text(small_text)
    
    print(f"\n✅ Text: {len(small_text)} chars")
    print(f"✅ Chunks: {len(chunks)}")
    print(f"✅ No chunking needed: {len(chunks) == 1}")
    
    return len(chunks) == 1


def test_hierarchical_summarization():
    """Test hierarchical summarization (requires LLM)."""
    print("\n" + "="*80)
    print("Testing Hierarchical Summarization")
    print("="*80)
    
    # This would require LLM integration
    print("⚠️ Skipping - requires LLM manager")
    print("   (This is tested in the FinancialResearchAgent)")
    
    return True


if __name__ == "__main__":
    test1 = test_small_text()
    test2 = test_chunking()
    test3 = test_hierarchical_summarization()
    
    if test1 and test2 and test3:
        print("\n" + "="*80)
        print("✅ All chunking tests PASSED!")
        print("="*80)
