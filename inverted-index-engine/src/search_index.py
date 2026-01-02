from pathlib import Path
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from index_the_index import load_lexicon_into_memory
import time
from flask import Flask, request, jsonify
import flask

project_root = Path(__file__).parent.parent

import math

# Create Flask app
app = Flask(__name__)

# Global variables to store loaded data (initialized at startup)
lexicon = None
url_mapping = None

def load_search_data():
    """Load lexicon and URL mapping data once at startup for better performance"""
    global lexicon, url_mapping
    
    startup_start = time.time()
    print("Loading search index data...")
    
    lexicon = load_lexicon_into_memory(project_root / "index" / "lexicon.txt")
    url_mapping = load_url_mapping(project_root / "index" / "url_mapping.txt")
    
    startup_end = time.time()
    startup_time = (startup_end - startup_start) * 1000
    
    print(f"✓ Loaded {len(lexicon)} terms in lexicon")
    print(f"✓ Loaded {len(url_mapping)} URL mappings")
    print(f"✓ Startup loading time: {startup_time:.2f} ms")
    print("=" * 50)

class Query:
    def __init__(self):
        self.query = ""
        self.boolean_operator = ""
        self.stemmer = PorterStemmer()  # Initialize Porter stemmer for query processing
        project_root = Path(__file__).resolve().parent.parent
        self.index_file_path = project_root / "index" / "inverted_index.txt"
        self.url_mapping_file_path = project_root / "index" / "url_mapping.txt"
        self.results = ""
    
    def _should_preserve_token(self, token: str, original_token: str = None) -> bool:
        """
        Determine if a token should be preserved without stemming.
        Preserves: short acronyms (2-3 chars, all caps), very short tokens (< 3 chars)
        
        Args:
            token: Lowercase token to check
            original_token: Original token before lowercasing (for case checking)
            
        Returns:
            True if token should be preserved, False if should be stemmed
        """
        if original_token:
            # Preserve short acronyms (2-3 characters, all uppercase)
            if len(original_token) <= 3 and original_token.isupper() and original_token.isalpha():
                return True
        # Preserve very short tokens to avoid over-stemming
        if len(token) < 3:
            return True
        return False
    
    def _smart_stem(self, token: str, original_token: str = None) -> str:
        """
        Apply stemming with smart preservation of acronyms and short tokens.
        
        Args:
            token: Lowercase token to stem
            original_token: Original token before lowercasing
            
        Returns:
            Stemmed token, or original if should be preserved
        """
        if self._should_preserve_token(token, original_token):
            return token.lower()
        return self.stemmer.stem(token)
    
    def stem_query_term(self, query_term: str) -> str:
        """
        Stem a single query term using the same process as indexing.
        For single words, returns the stemmed word.
        For multi-word queries, returns the first stemmed word (used for display).
        
        Args:
            query_term: Raw query term from user
            
        Returns:
            Stemmed query term, or original if no valid tokens found
        """
        # Tokenize the query term (handles multi-word queries)
        # Get original tokens to preserve case info for acronyms
        original_tokens = word_tokenize(query_term)
        tokens = word_tokenize(query_term.lower())
        
        # Filter to alphanumeric tokens and stem them with smart preservation
        stemmed_tokens = []
        for orig_token, token in zip(original_tokens, tokens):
            if token.isalnum() and len(token) >= 1:
                stemmed = self._smart_stem(token, orig_token)
                stemmed_tokens.append(stemmed)
        
        # Return the first stemmed token, or original if no valid tokens
        return stemmed_tokens[0] if stemmed_tokens else query_term.lower()
    
    def is_multi_word_query(self, query: str) -> bool:
        """
        Check if a query contains multiple meaningful words.
        
        Args:
            query: Raw query from user
            
        Returns:
            True if query has multiple alphanumeric tokens
        """
        tokens = word_tokenize(query.lower())
        alphanumeric_tokens = [token for token in tokens if token.isalnum() and len(token) >= 1]
        return len(alphanumeric_tokens) > 1
    
    def process_multi_word_query(self, query: str, lexicon: dict, url_mapping: dict) -> list:
        """
        Process a multi-word query by finding documents that contain ALL terms.
        Also uses n-gram matching for better retrieval.
        
        Args:
            query: Raw multi-word query from user
            lexicon: Loaded lexicon dictionary for direct file access
            url_mapping: Loaded URL mapping dictionary for fast lookup
            
        Returns:
            List of URLs that contain all stemmed terms or matching n-grams
        """
        stemmed_terms = self.stem_all_query_terms(query)
        
        # First, try to find exact n-gram matches (2-gram or 3-gram)
        query_ngrams = self.generate_query_ngrams(query)
        
        # Check if any n-gram exists in the index
        ngram_results = []
        for ngram in query_ngrams:
            if ngram in lexicon:
                print(f"Found n-gram in index: {ngram}")
                ngram_urls = self.get_sorted_urls_by_tf_idf(ngram, lexicon, url_mapping)
                if ngram_urls:
                    ngram_results.extend(ngram_urls)
        
        # If we found n-gram matches, combine them with individual term matches
        if ngram_results:
            # Use n-gram results as primary, but also consider individual terms
            all_results = set(ngram_results)
            
            # Also get results for individual terms
            for term in stemmed_terms:
                term_urls = self.get_sorted_urls_by_tf_idf(term, lexicon, url_mapping)
                all_results.update(term_urls)
            
            # Score and rank all results
            return self._rank_combined_results(query, stemmed_terms, query_ngrams, all_results, lexicon, url_mapping)
        
        # Fall back to original multi-word query processing
        if len(stemmed_terms) < 2:
            return self.get_sorted_urls_by_tf_idf(query, lexicon, url_mapping)
        
        # Get results for each term
        all_term_results = []
        
        for term in stemmed_terms:
            # Get URLs for this specific term
            term_urls = self.get_sorted_urls_by_tf_idf(term, lexicon, url_mapping)
            
            if not term_urls:
                return []  # If any term has no results, no documents match all terms
            all_term_results.append(set(term_urls))
        
        # Find intersection (documents containing ALL terms)
        common_urls = set.intersection(*all_term_results)
        return list(common_urls)
    
    def _rank_combined_results(self, query: str, stemmed_terms: list, query_ngrams: list, 
                               candidate_urls: set, lexicon: dict, url_mapping: dict) -> list:
        """
        Rank results by combining scores from individual terms and n-grams.
        N-grams get higher weight since they represent exact phrase matches.
        
        Args:
            query: Original query
            stemmed_terms: List of stemmed individual terms
            query_ngrams: List of n-grams from the query
            candidate_urls: Set of candidate URLs to rank
            lexicon: Loaded lexicon dictionary
            url_mapping: Loaded URL mapping dictionary
            
        Returns:
            List of URLs sorted by combined TF-IDF score
        """
        url_scores = {}
        
        # Get scores for individual terms
        for term in stemmed_terms:
            doc_frequencies = self.get_documents_with_frequencies(term, lexicon)
            N = len(url_mapping)
            df = len(doc_frequencies)
            
            if df > 0:
                idf = math.log(N / df)
                for doc_id, tf in doc_frequencies.items():
                    if doc_id in url_mapping and url_mapping[doc_id] in candidate_urls:
                        url = url_mapping[doc_id]
                        score = tf * idf
                        url_scores[url] = url_scores.get(url, 0) + score
        
        # Get scores for n-grams (with higher weight - 1.5x multiplier)
        for ngram in query_ngrams:
            doc_frequencies = self.get_documents_with_frequencies(ngram, lexicon)
            N = len(url_mapping)
            df = len(doc_frequencies)
            
            if df > 0:
                idf = math.log(N / df)
                for doc_id, tf in doc_frequencies.items():
                    if doc_id in url_mapping and url_mapping[doc_id] in candidate_urls:
                        url = url_mapping[doc_id]
                        # N-grams get 1.5x weight for exact phrase matching
                        score = tf * idf * 1.5
                        url_scores[url] = url_scores.get(url, 0) + score
        
        # Sort by score in descending order
        sorted_urls = sorted(url_scores.keys(), key=lambda x: url_scores[x], reverse=True)
        return sorted_urls
    
    def stem_all_query_terms(self, query: str) -> list:
        """
        Stem all words in a query and return them as a list.
        This is used for multi-word query processing.
        
        Args:
            query: Raw query from user
            
        Returns:
            List of stemmed terms
        """
        # Tokenize the entire query
        # Get original tokens to preserve case info for acronyms
        original_tokens = word_tokenize(query)
        tokens = word_tokenize(query.lower())
        
        # Filter to alphanumeric tokens and stem them with smart preservation
        stemmed_tokens = []
        for orig_token, token in zip(original_tokens, tokens):
            if token.isalnum() and len(token) >= 1:
                stemmed = self._smart_stem(token, orig_token)
                stemmed_tokens.append(stemmed)
        
        return stemmed_tokens
    
    def generate_query_ngrams(self, query: str) -> list:
        """
        Generate 2-grams and 3-grams from a query using the same process as indexing.
        
        Args:
            query: Raw query from user
            
        Returns:
            List of n-gram strings (bigrams and trigrams) in format "word1_word2" or "word1_word2_word3"
        """
        stemmed_tokens = self.stem_all_query_terms(query)
        ngrams = []
        
        # Generate 2-grams (bigrams)
        for i in range(len(stemmed_tokens) - 1):
            bigram = f"{stemmed_tokens[i]}_{stemmed_tokens[i+1]}"
            ngrams.append(bigram)
        
        # Generate 3-grams (trigrams)
        for i in range(len(stemmed_tokens) - 2):
            trigram = f"{stemmed_tokens[i]}_{stemmed_tokens[i+1]}_{stemmed_tokens[i+2]}"
            ngrams.append(trigram)
        
        return ngrams
    
    def get_total_document_count(self) -> int:
        """
        Get the total number of documents in the collection by counting unique document IDs
        from the URL mapping file.
        
        Returns:
            Total number of documents indexed
        """
        doc_count = 0
        try:
            with open(self.url_mapping_file_path, 'r', encoding='utf-8') as url_mapping_doc:
                for line in url_mapping_doc:
                    line = line.strip()
                    if line and ':' in line:
                        doc_count += 1
        except FileNotFoundError:
            print(f"URL mapping file not found: {self.url_mapping_file_path}")
            return 0
        except Exception as e:
            print(f"Error reading URL mapping: {e}")
            return 0
        
        return doc_count
    
    def get_documents_with_frequencies(self, query, lexicon):
        """
        Get document IDs and their frequencies for a given query term.
        Automatically stems the query term to match the stemmed index.
        Uses lexicon for direct file access instead of scanning entire file.
        
        Args:
            query: Raw query term
            lexicon: Loaded lexicon dictionary for direct file access
        
        Returns:
        - A dictionary mapping document IDs to their term frequencies
        """
        # Stem the query term to match the index
        stemmed_query = self.stem_query_term(query)
        
        doc_frequencies = {}
        
        # Check if the stemmed term exists in the lexicon
        if stemmed_query not in lexicon:
            return {}  # Term not found in index
        
        # Get the term's location information from lexicon
        term_info = lexicon[stemmed_query]
        offset = term_info['offset']
        length = term_info['length']
        
        try:
            with open(self.index_file_path, 'rb') as inverted_index_doc:
                # Seek directly to the term's location
                inverted_index_doc.seek(offset)
                
                # Read exactly the number of bytes for this term's line
                line_bytes = inverted_index_doc.read(length)
                line = line_bytes.decode('utf-8').strip()
                
                if not line:
                    return {}
                
                parts = line.split(":")
                if len(parts) < 2:
                    return {}
                
                term = parts[0]
                if term == stemmed_query:
                    # Parse format: word:doc_id1:freq1,doc_id2:freq2,...
                    doc_data = ':'.join(parts[1:])
                    
                    # Split by comma to get individual document entries
                    for entry in doc_data.split(','):
                        if ':' in entry:
                            doc_id, freq = entry.split(':', 1)
                            doc_frequencies[doc_id.strip()] = int(freq.strip())
                            
        except FileNotFoundError:
            print(f"Index file not found: {self.index_file_path}")
            return {}
        except Exception as e:
            print(f"Error reading index: {e}")
            return {}
        
        return doc_frequencies
    
    def get_sorted_urls_by_frequency(self, query, lexicon, url_mapping):
        """
        Get URLs sorted by their term frequency in descending order
        
        Args:
            query: Query term to search for
            lexicon: Loaded lexicon dictionary for direct file access
            url_mapping: Loaded URL mapping dictionary for fast lookup
        
        Returns:
        - A list of URLs sorted by term frequency (highest to lowest)
        """
        # Get document IDs and their frequencies
        doc_frequencies = self.get_documents_with_frequencies(query, lexicon)
        
        print(f"Found {len(doc_frequencies)} documents containing the term")
        
        # Sort document IDs by frequency in descending order
        sorted_doc_ids = sorted(doc_frequencies.keys(), 
                                key=lambda x: doc_frequencies[x], 
                                reverse=True)
        
        # Map document IDs to URLs using in-memory mapping
        url_frequency_map = {}
        
        for doc_id in sorted_doc_ids:
            if doc_id in url_mapping:
                url = url_mapping[doc_id]
                url_frequency_map[url] = doc_frequencies[doc_id]
        
            # Sort URLs by their term frequency in descending order
            sorted_urls = sorted(url_frequency_map.keys(), 
                                 key=lambda x: url_frequency_map[x], 
                                 reverse=True)
            
            return sorted_urls
        
    def get_sorted_urls_by_tf_idf(self, query, lexicon, url_mapping):
        """
        Get URLs sorted by their TF-IDF score in descending order
        
        Args:
            query: Query term to search for
            lexicon: Loaded lexicon dictionary for direct file access
            url_mapping: Loaded URL mapping dictionary for fast lookup
        
        Returns:
        - A list of URLs sorted by TF-IDF (highest to lowest)
        """
        # Get document IDs and their frequencies
        doc_frequencies = self.get_documents_with_frequencies(query, lexicon)
        
        print(f"Found {len(doc_frequencies)} documents containing the term")
        
        ### TF-IDF ###

        N = len(url_mapping)  # Use pre-loaded URL mapping count
        df = len(doc_frequencies)

        if df == 0:
            return []
        
        idf = math.log(N/df)

        # compute TF-IDF scores for each doc
        doc_scores = {doc_id: (tf*idf) for doc_id, tf in doc_frequencies.items()}

        ##############

        # Sort document IDs by TF-IDF in descending order
        sorted_doc_ids = sorted(doc_scores.keys(), 
                                key=lambda x: doc_scores[x], 
                                reverse=True)
        
        # Map document IDs to URLs using in-memory mapping
        url_frequency_map = {}
        
        for doc_id in sorted_doc_ids:
            if doc_id in url_mapping:
                url = url_mapping[doc_id]
                url_frequency_map[url] = doc_scores[doc_id]
        
        # Sort URLs by their TF-IDF in descending order
        sorted_urls = sorted(url_frequency_map.keys(), 
                             key=lambda x: url_frequency_map[x], 
                             reverse=True)
        
        return sorted_urls
    
    def boolean_AND_operator(self, query, lexicon, url_mapping):
        """Process boolean AND queries with stemmed terms"""
        terms = [term.strip() for term in query.split('AND')]
        
        # If only one term, return standard search results
        if len(terms) < 2:
            return self.get_sorted_urls_by_tf_idf(query, lexicon, url_mapping)
        
        # Store results for each term
        all_term_results = []
        
        # Search for each term (stemming will be applied in get_sorted_urls_by_tf_idf)
        for term in terms:
            # Get URLs for this specific term
            term_urls = self.get_sorted_urls_by_tf_idf(term, lexicon, url_mapping)
            
            if not term_urls:
                return []
            all_term_results.append(set(term_urls))
        common_urls = set.intersection(*all_term_results)

        return list(common_urls)


def load_url_mapping(url_mapping_path):
    """Load URL mapping into memory as a dictionary for fast lookup"""
    url_mapping = {}
    
    try:
        with open(url_mapping_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    doc_id, url = line.split(':', 1)
                    url_mapping[doc_id.strip()] = url.strip()
    except FileNotFoundError:
        print(f"URL mapping file not found: {url_mapping_path}")
    except Exception as e:
        print(f"Error loading URL mapping: {e}")
    
    return url_mapping


def search_query_logic(query_text):
    """
    Core search logic function - extracted from test_search_local.py
    This function contains the clean search logic that can be used by both Flask API and local testing
    
    Args:
        query_text: The search query string
        
    Returns:
        Dictionary with search results in API format
    """
    global lexicon, url_mapping
    
    try:
        # Use pre-loaded data instead of loading on every request
        if lexicon is None or url_mapping is None:
            # Fallback: load data if not already loaded (shouldn't happen in normal operation)
            lexicon = load_lexicon_into_memory(project_root / "index" / "lexicon.txt")
            url_mapping = load_url_mapping(project_root / "index" / "url_mapping.txt")
        
        query_processor = Query()
        
        # Start timing ONLY the search algorithm
        start_time = time.time()
        
        # Determine query type and process accordingly
        if query_processor.is_multi_word_query(query_text) or 'AND' in query_text.upper():
            stemmed_terms = query_processor.stem_all_query_terms(query_text)
            query_info = f"Multi-word query - Stemmed terms: {' '.join(stemmed_terms)}"
        else:
            stemmed_query = query_processor.stem_query_term(query_text)
            query_info = f"Single word - Stemmed query: '{query_text}' -> '{stemmed_query}'"
        
        # Use TF-IDF scoring for all queries
        sorted_urls = query_processor.get_sorted_urls_by_tf_idf(query_text, lexicon, url_mapping)
        
        # End timing - this now measures ONLY the search algorithm
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Prepare response data (same format as Flask API)
        result_data = {
            'query': query_text,
            'query_info': query_info,
            'total_documents': len(url_mapping),
            'results_count': len(sorted_urls),
            'search_time_ms': round(duration_ms, 2),
            'results': sorted_urls[:20]  # Top 20 results like Flask API
        }
        
        return result_data
        
    except Exception as e:
        return {
            'error': f'Search failed: {str(e)}',
            'query': query_text,
            'results_count': 0,
            'results': []
        }


@app.route('/search', methods=['GET'])
def search_endpoint():
    """Flask endpoint for searching the inverted index"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    # Use the improved search logic function
    result_data = search_query_logic(query)
    
    # Check if there was an error
    if 'error' in result_data:
        return jsonify(result_data), 500
    
    return jsonify(result_data)


def trigger_search(query):
    """Legacy function for command-line usage"""
    lexicon = load_lexicon_into_memory(project_root / "index" / "lexicon.txt")
    url_mapping = load_url_mapping(project_root / "index" / "url_mapping.txt")
    print(f"Loaded {len(url_mapping)} URL mappings")
    
    query_processor = Query()
    
    # Get total document count (cached from URL mapping)
    total_docs = len(url_mapping)
    print(f"Total documents in collection: {total_docs}")
    print("=" * 50)
    
    # Start timing the search
    start_time = time.time()
    
    # Use TF-IDF for all queries (single word, multi-word, or AND queries)
    # Stem the query for display purposes
    if query_processor.is_multi_word_query(query) or 'AND' in query.upper():
        stemmed_terms = query_processor.stem_all_query_terms(query)
        print(f"Query - Stemmed terms: {' '.join(stemmed_terms)}")
    else:
        stemmed_query = query_processor.stem_query_term(query)
        print(f"Single word - Stemmed query: '{query}' -> '{stemmed_query}'")
    
    # Use TF-IDF scoring for all queries
    sorted_urls = query_processor.get_sorted_urls_by_tf_idf(query, lexicon, url_mapping)
    
    # End timing and calculate duration
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000  
    # Convert to milliseconds
    print(f"Search completed in {duration_ms:.2f} ms")
    print(f"Results: {len(sorted_urls)} out of {total_docs} documents")
    print("URLs:")
    if sorted_urls:
        for i, url in enumerate(sorted_urls[:5], 1):  # Show top 5 results
            print(f"  {i}. {url}")
        if len(sorted_urls) > 5:
            print(f"  ... and {len(sorted_urls) - 5} more results")
    else:
        print("  No results found")


if __name__ == "__main__":
    # Load data at startup
    load_search_data()
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)