def indexing_our_index(file_path):
    print("Indexing our index...")

    lexicon = {}

    # Open in **binary mode** so offsets are in raw bytes
    with open(file_path, "rb") as f:
        while True:
            offset = f.tell()              
            # byte position BEFORE reading line
            line = f.readline()            
            # read bytes of the line

            if not line:                   
                # end of file
                break

            if not line.strip():           
                # skip empty lines
                continue

            # decode to parse the word
            text = line.decode("utf-8").strip()
            
            # Parse format: term:doc_id1:freq1,doc_id2:freq2,...
            if ':' not in text:
                continue
                
            parts = text.split(':', 1)
            term = parts[0]
            
            # Count document frequency (number of documents containing this term)
            postings = parts[1]
            df = len(postings.split(',')) if postings else 0
            
            length = len(line)

            lexicon[term] = {
                "offset": offset,          
                "length": length,          
                "df": df                   
            }

    return lexicon

def write_lexicon_into_file(file_path, lexicon_path):
    lexicon = indexing_our_index(file_path)
    with open(lexicon_path, "w", encoding="utf-8") as lexicon_file:
        for term, info in lexicon.items():
            lexicon_file.write(f"{term} {info['offset']} {info['length']} {info['df']}\n")


def load_lexicon_into_memory(file_path):
    """Load lexicon from file into memory as a dictionary"""
    lexicon = {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 4:
                term = parts[0]
                offset = int(parts[1])
                length = int(parts[2])
                df = int(parts[3])
                
                lexicon[term] = {
                    "offset": offset,
                    "length": length,
                    "df": df
                }
    
    return lexicon
if __name__ == "__main__":
    from pathlib import Path
    
    # Define paths
    project_root = Path(__file__).parent.parent
    index_file = project_root / "index" / "inverted_index.txt"
    lexicon_file = project_root / "index" / "lexicon.txt"
    
    print(f"Creating lexicon from: {index_file}")
    print(f"Saving lexicon to: {lexicon_file}")
    
    write_lexicon_into_file(str(index_file), str(lexicon_file))
    print("Lexicon created successfully!")
    # Load the lexicon into memory
    lexicon = load_lexicon_into_memory(project_root / "index" / "lexicon.txt")
    print("Lexicon loaded into memory successfully!")
    print(f"Loaded {len(lexicon)} terms.")