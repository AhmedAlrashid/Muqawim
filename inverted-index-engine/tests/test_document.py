import os
import sys
import json
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from build_index import Document


def test_specific_file():
    """Test the Document class with the specific AI Club file"""
    # Path to the specific file
    specific_file = Path(__file__).parent.parent / "data" / "developer" / "DEV" / "aiclub_ics_uci_edu" / "8ef6d99d9f9264fc84514cdd2e680d35843785310331e1db4bbd06dd2b8eda9b.json"
    
    print(f"Testing with specific file: {specific_file}")
    print("=" * 80)
    
    if not specific_file.exists():
        print(f"ERROR: File {specific_file} does not exist!")
        return
    
    try:
        # Load the JSON data
        data = json.loads(specific_file.read_text(encoding="utf-8", errors="ignore"))
        
        print(f"=== RAW JSON DATA ===")
        print(f"URL: {data['url']}")
        print(f"Encoding: {data.get('encoding', 'not specified')}")
        print(f"Content length: {len(data['content'])} characters")
        print(f"Content preview (first 300 chars):")
        print(data['content'][:300])
        print()
        
        # Create Document object
        document = Document(
            url=data["url"],
            content=data["content"],
            encoding=data.get("encoding", "utf-8")
        )
        
        print(f"=== DOCUMENT OBJECT (Before Tokenization) ===")
        print(f"Document: {document}")  # This will show tokens=0, unique=0
        print(f"Cleaned URL: {document.url}")
        print(f"Parsed text length: {len(document.parsed_text)} characters")
        print(f"Parsed text preview (first 500 chars):")
        print(document.parsed_text[:500])
        print()
        
        # Tokenize
        tokens = document.tokenize()
        
        print(f"=== DOCUMENT OBJECT (After Tokenization) ===")
        print(f"Document: {document}")  # Now this will show correct counts
        
        print(f"=== TOKENIZATION RESULTS ===")
        print(f"Total tokens: {document.get_total_tokens()}")
        print(f"Unique tokens: {document.get_unique_token_count()}")
        print(f"First 20 tokens: {list(document.tokens.keys())[:20]}")
        print()
        
        # Show top 10 most frequent tokens
        sorted_tokens = sorted(document.tokens.items(), key=lambda x: x[1], reverse=True)
        print(f"Top 10 most frequent tokens:")
        for i, (token, freq) in enumerate(sorted_tokens[:10]):
            print(f"  {i+1:2d}. {token:15s} (freq: {freq})")
        print()
        
        # Test specific token frequency lookup
        if sorted_tokens:
            test_token = sorted_tokens[0][0]  # Most frequent token
            freq = document.get_token_frequency(test_token) if hasattr(document, 'get_token_frequency') else document.tokens.get(test_token, 0)
            print(f"Testing token frequency lookup for '{test_token}': {freq}")
            
            # Test with non-existent token
            fake_freq = document.get_token_frequency("thisdoesnotexist123") if hasattr(document, 'get_token_frequency') else document.tokens.get("thisdoesnotexist123", 0)
            print(f"Testing with non-existent token 'thisdoesnotexist123': {fake_freq}")
            print()
        
        # Test all methods
        print(f"=== METHOD TESTING ===")
        print(f"get_unique_tokens(): {len(document.get_unique_tokens())} tokens")
        print(f"get_total_tokens(): {document.get_total_tokens()}")
        print(f"get_unique_token_count(): {document.get_unique_token_count()}")
        
        # Show some interesting tokens from AI Club content
        ai_related = [token for token in document.tokens.keys() if any(word in token for word in ['ai', 'artificial', 'intelligence', 'machine', 'learning', 'uci'])]
        if ai_related:
            print(f"AI-related tokens found: {ai_related[:10]}")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()


def test_document_methods():
    """Test Document class methods with sample data"""
    print("\n" + "=" * 80)
    print("TESTING DOCUMENT METHODS")
    print("=" * 80)
    
    # Create a simple test document
    html_content = """
    <html>
        <head><title>AI Club at UCI Test Page</title></head>
        <body>
            <h1>Artificial Intelligence Club</h1>
            <p>We are the <strong>AI Club</strong> at UCI. We focus on machine learning and AI research.</p>
            <h2>Our Activities</h2>
            <p>Machine learning workshops, AI seminars, and coding sessions.</p>
        </body>
    </html>
    """
    
    doc = Document(
        url="http://test.example.com#fragment",
        content=html_content,
        encoding="utf-8"
    )
    
    print(f"Test document: {doc}")
    print(f"URL (fragment removed): {doc.url}")
    print(f"Parsed text: {doc.parsed_text}")
    
    # Tokenize
    tokens = doc.tokenize()
    print(f"Tokens found: {tokens}")
    print(f"Token frequencies: {doc.tokens}")
    
    # Test all getter methods
    print(f"Total tokens: {doc.get_total_tokens()}")
    print(f"Unique tokens: {doc.get_unique_token_count()}")
    print(f"Unique token list: {doc.get_unique_tokens()}")


if __name__ == "__main__":
    print("DOCUMENT CLASS TESTS")
    print("=" * 80)
    
    # Test with the specific file
    test_specific_file()
    
    # Test with sample data
    test_document_methods()
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETED")