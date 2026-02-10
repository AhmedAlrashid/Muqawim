from search_index import load_lexicon_into_memory,load_url_mapping,Query,time,project_root,trigger_search
def main():
    # Test the 4 requested queries + some we know exist
    queries = [
        "Gaza",
        "saudi", 
        "trump"
    ]
    
    for query in queries:
        trigger_search(query)

if __name__ == "__main__":
    main()