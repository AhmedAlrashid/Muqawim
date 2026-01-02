import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from build_index import Document

def verify_parsing():
    """Verify that our HTML parsing is extracting the expected content"""
    
    # Load the AI club file
    file_path = Path(__file__).parent.parent / "data" / "developer" / "DEV" / "aiclub_ics_uci_edu" / "8ef6d99d9f9264fc84514cdd2e680d35843785310331e1db4bbd06dd2b8eda9b.json"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create document
    doc = Document(data['url'], data['content'], data.get('encoding', 'utf-8'))
    
    print("=== PARSING VERIFICATION ===")
    print(f"Original HTML length: {len(data['content'])}")
    print(f"Parsed text length: {len(doc.parsed_text)}")
    print()
    
    # Check for key terms that should be present
    expected_terms = [
        "Artificial Intelligence",
        "UCI", 
        "Shaping the Future of AI",
        "AI@UCI",
        "University of California, Irvine",
        "nonprofit student-run organization",
        "machine learning",
        "Bi-weekly events",
        "workshops",
        "Amy Elsayed",
        "President",
        "Jason Kahn", 
        "Vice President",
        "PSCB 120",
        "6pm - 7pm",
        "Monday Only",
        "Alexander Ihler",
        "advisor"
    ]
    
    print("=== CHECKING FOR EXPECTED CONTENT ===")
    found_terms = []
    missing_terms = []
    
    for term in expected_terms:
        if term.lower() in doc.parsed_text.lower():
            found_terms.append(term)
            print(f"✅ FOUND: '{term}'")
        else:
            missing_terms.append(term)
            print(f"❌ MISSING: '{term}'")
    
    print(f"\nSUMMARY:")
    print(f"Found: {len(found_terms)}/{len(expected_terms)} terms")
    print(f"Missing: {missing_terms}")
    
    if missing_terms:
        print(f"\n=== FULL PARSED TEXT (first 1000 chars) ===")
        print(doc.parsed_text[:1000])
        print("...")
        print(f"\n=== FULL PARSED TEXT (last 500 chars) ===") 
        print(doc.parsed_text[-500:])
    
    # Tokenize and check tokens
    tokens = doc.tokenize()
    print(f"\n=== TOKENIZATION CHECK ===")
    print(f"Total tokens: {doc.get_total_tokens()}")
    print(f"Unique tokens: {doc.get_unique_token_count()}")
    
    # Check for specific important tokens
    important_tokens = ['artificial', 'intelligence', 'uci', 'machine', 'learning', 'amy', 'elsayed', 'jason', 'kahn', 'alexander', 'ihler']
    print(f"\nImportant token frequencies:")
    for token in important_tokens:
        freq = doc.tokens.get(token, 0)
        print(f"  {token}: {freq}")
    
    return len(missing_terms) == 0

if __name__ == "__main__":
    success = verify_parsing()
    if success:
        print("\n🎉 PARSING VERIFICATION PASSED!")
    else:
        print("\n⚠️  PARSING VERIFICATION FAILED - Some expected content missing")