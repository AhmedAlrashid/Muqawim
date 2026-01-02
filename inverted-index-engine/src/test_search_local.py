from search_index import load_lexicon_into_memory,load_url_mapping,Query,time,project_root
def main():
    lexicon = load_lexicon_into_memory(project_root / "index" / "lexicon.txt")
    url_mapping = load_url_mapping(project_root / "index" / "url_mapping.txt")
    print(f"Loaded {len(url_mapping)} URL mappings")
    
    query_processor = Query()
    
    # Get total document count (cached from URL mapping)
    total_docs = len(url_mapping)
    print(f"Total documents in collection: {total_docs}")
    print("=" * 50)
    
    # Test the 4 requested queries + some we know exist
    queries = [
        "cristina lopes",
        "machine learning", 
        "ACM",
        "master of software engineering"
    ]
    
    for query in queries:
        print(f"Searching for: \"{query}\"")
        
        # Start timing the search
        start_time = time.time()
        
        # Use TF-IDF for all queries (single word, multi-word, or AND queries)
        # Stem the query for display purposes
        if query_processor.is_multi_word_query(query) or 'AND' in query.upper():
            stemmed_terms = query_processor.stem_all_query_terms(query)
            query_ngrams = query_processor.generate_query_ngrams(query)
            print(f"Query - Stemmed terms: {' '.join(stemmed_terms)}")
            if query_ngrams:
                print(f"Query - Generated n-grams: {', '.join(query_ngrams)}")
        else:
            stemmed_query = query_processor.stem_query_term(query)
            print(f"Single word - Stemmed query: '{query}' -> '{stemmed_query}'")
        
        # Use n-gram enhanced search for multi-word queries, standard TF-IDF for single words
        if query_processor.is_multi_word_query(query) or 'AND' in query.upper():
            sorted_urls = query_processor.process_multi_word_query(query, lexicon, url_mapping)
        else:
            sorted_urls = query_processor.get_sorted_urls_by_tf_idf(query, lexicon, url_mapping)
        
        # End timing and calculate duration
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        
        print(f"Search completed in {duration_ms:.2f} ms")
        print(f"Results: {len(sorted_urls)} out of {total_docs} documents")
        print("URLs:")
        if sorted_urls:
            for i, url in enumerate(sorted_urls[:5], 1):  # Show top 5 results
                print(f"  {i}. {url}")
            if len(sorted_urls) > 5:
                print(f"  ... and {len(sorted_urls) - 5} more results")
        else:
            print("No results found")

if __name__ == "__main__":
    main()