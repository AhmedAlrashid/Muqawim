import os
import json
import re
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Tuple, Set
from collections import Counter, defaultdict
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

"""
Plan:
Use a map to map each url to an id to be able to store the doc_id instead of full doc url

Loop through each word and tokenize them

create a dictionary that that will map each word with its assocciated weight (for m1 itll be just the frequency)

Each document will have its own dictionary, so there are no collisions between repeated words

Add up the weights for the full document also and save that in the index

Add_to_index function should take in the doc_id, dictionary associated with it and the total weight, then that should be added to the index

the index will be a defaultdict[list], so that each word will have a an associated weight with the document so

something like "jump":[(82773,3),(32213,5)] indicating the word jump is assocaited in docs with doc_id 82773 and has 3 weight or freq

and 32213 with 5 weight or frequency

We should add to inverted index in memory until we finish a document or reach a threshold (lets say 15000) to not run out of

space and then write it to a text file

Text files will partioned, this will help with searching, 100 or so partitions will do so, once the in memory reaches threshold 

we should map our has function to the correct partition and then write to the file
"""


class URLMapper:
    """Manages bidirectional mapping between URLs and document IDs"""
    
    def __init__(self):
        self.url_to_id = {}
        self.id_to_url = {}
    
    def get_id(self, url: str) -> int:
        """Get document ID for URL, creating new one if needed"""
        if url in self.url_to_id:
            return self.url_to_id[url]
        
        # Create new ID using simple hash
        new_id = self._simple_hash(url)
        
        # Handle hash collisions by incrementing
        while new_id in self.id_to_url:
            new_id += 1
        
        # Store bidirectional mapping
        self.url_to_id[url] = new_id
        self.id_to_url[new_id] = url
        
        return new_id
    
    def get_url(self, doc_id: int) -> str:
        """Reverse lookup: get URL from document ID"""
        return self.id_to_url.get(doc_id, None)
    
    def _simple_hash(self, url: str) -> int:
        """Simple hash function for creating document IDs"""
        hash_value = 0
        prime = 31
        mod = 2**31 - 1
        
        for char in url:
            hash_value = (hash_value * prime + ord(char)) % mod
        
        return abs(hash_value) + 1
    
    def __len__(self):
        return len(self.url_to_id)


class Document:
    """Represents a single document in the corpus"""
    
    def __init__(self, url: str, content: str, encoding: str = "utf-8", stemmer: Optional[PorterStemmer] = None):
        self.url = self._clean_url(url)
        self.raw_content = content
        self.encoding = encoding
        self.stemmer = stemmer or PorterStemmer()
        self.parsed_text, self.important_text = self._parse_content()
        self.tokens = {}  # Maps stemmed token -> (normal_count, important_count)
        self.doc_id = None  # Will be set by the index when needed
    
    def _clean_url(self, url: str) -> str:
        """Remove fragment part from URL as specified in requirements"""
        return url.split('#')[0]
    
    def _parse_content(self) -> Tuple[str, str]:
        """Parse HTML content and extract clean text, handling broken HTML.
        Returns tuple of (normal_text, important_text) where important_text
        contains words from bold, headings (h1-h3), and title tags."""
        if not self.raw_content or not self.raw_content.strip():
            return "", ""
        
        try:
            # BeautifulSoup can handle broken/malformed HTML gracefully
            soup = BeautifulSoup(self.raw_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract important text (bold, headings, title)
            important_parts = []
            
            # Get title
            title_tag = soup.find('title')
            if title_tag:
                important_parts.append(title_tag.get_text())
            
            # Get headings h1, h2, h3
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                important_parts.append(heading.get_text())
            
            # Get bold text
            for bold in soup.find_all(['b', 'strong']):
                important_parts.append(bold.get_text())
            
            # Combine important text
            important_text = ' '.join(important_parts)
            
            # Get all text content for normal text
            text = soup.get_text()
            
            # Clean up whitespace
            def clean_text(text_str):
                lines = (line.strip() for line in text_str.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                return ' '.join(chunk for chunk in chunks if chunk)
            
            clean_normal = clean_text(text)
            clean_important = clean_text(important_text)
            
            return clean_normal, clean_important
        except Exception as e:
            print(f"Error parsing HTML for {self.url}: {e}")
            return "", ""
    
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
    
    def tokenize(self) -> Dict[str, Tuple[int, int]]:
        """
        Tokenize the document text using NLTK word tokenizer and Porter stemming.
        Important words (bold, headings, titles) are tracked separately.
        
        According to requirements:
        - Tokens: alphanumeric sequences extracted using NLTK word tokenizer
        - No stop words (use all words)
        - Porter stemming using NLTK implementation (with smart preservation)
        
        Returns:
            Dictionary mapping stemmed_token -> (normal_count, important_count)
        """
        self.tokens = {}
        
        # Tokenize normal text
        if self.parsed_text:
            # Get original tokens before lowercasing to preserve case info
            original_tokens = word_tokenize(self.parsed_text)
            normal_tokens = word_tokenize(self.parsed_text.lower())
            for orig_token, token in zip(original_tokens, normal_tokens):
                # Keep only alphanumeric tokens (filter out punctuation)
                if token.isalnum() and len(token) >= 1:
                    stemmed = self._smart_stem(token, orig_token)  # Smart stemming with preservation
                    if stemmed not in self.tokens:
                        self.tokens[stemmed] = (0, 0)
                    normal_count, important_count = self.tokens[stemmed]
                    self.tokens[stemmed] = (normal_count + 1, important_count)
        
        # Tokenize important text (with higher weight)
        if self.important_text:
            original_important_tokens = word_tokenize(self.important_text)
            important_tokens = word_tokenize(self.important_text.lower())
            for orig_token, token in zip(original_important_tokens, important_tokens):
                # Keep only alphanumeric tokens (filter out punctuation)
                if token.isalnum() and len(token) >= 1:
                    stemmed = self._smart_stem(token, orig_token)  # Smart stemming with preservation
                    if stemmed not in self.tokens:
                        self.tokens[stemmed] = (0, 0)
                    normal_count, important_count = self.tokens[stemmed]
                    # Important words get 2x weight
                    self.tokens[stemmed] = (normal_count, important_count + 2)
        
        # Generate 2-grams and 3-grams from normal text
        if self.parsed_text:
            original_normal_tokens = word_tokenize(self.parsed_text)
            normal_tokens_lower = word_tokenize(self.parsed_text.lower())
            normal_tokens = [self._smart_stem(t, orig) for orig, t in zip(original_normal_tokens, normal_tokens_lower) if t.isalnum() and len(t) >= 1]
            
            # Generate 2-grams (bigrams) from normal text
            for i in range(len(normal_tokens) - 1):
                bigram = f"{normal_tokens[i]}_{normal_tokens[i+1]}"
                if bigram not in self.tokens:
                    self.tokens[bigram] = (0, 0)
                normal_count, important_count = self.tokens[bigram]
                self.tokens[bigram] = (normal_count + 1, important_count)
            
            # Generate 3-grams (trigrams) from normal text
            for i in range(len(normal_tokens) - 2):
                trigram = f"{normal_tokens[i]}_{normal_tokens[i+1]}_{normal_tokens[i+2]}"
                if trigram not in self.tokens:
                    self.tokens[trigram] = (0, 0)
                normal_count, important_count = self.tokens[trigram]
                self.tokens[trigram] = (normal_count + 1, important_count)
        
        # Generate 2-grams and 3-grams from important text (with higher weight)
        if self.important_text:
            original_important_tokens = word_tokenize(self.important_text)
            important_tokens_lower = word_tokenize(self.important_text.lower())
            important_tokens = [self._smart_stem(t, orig) for orig, t in zip(original_important_tokens, important_tokens_lower) if t.isalnum() and len(t) >= 1]
            
            # Generate 2-grams (bigrams) from important text
            for i in range(len(important_tokens) - 1):
                bigram = f"{important_tokens[i]}_{important_tokens[i+1]}"
                if bigram not in self.tokens:
                    self.tokens[bigram] = (0, 0)
                normal_count, important_count = self.tokens[bigram]
                # Important n-grams get 2x weight
                self.tokens[bigram] = (normal_count, important_count + 2)
            
            # Generate 3-grams (trigrams) from important text
            for i in range(len(important_tokens) - 2):
                trigram = f"{important_tokens[i]}_{important_tokens[i+1]}_{important_tokens[i+2]}"
                if trigram not in self.tokens:
                    self.tokens[trigram] = (0, 0)
                normal_count, important_count = self.tokens[trigram]
                # Important n-grams get 2x weight
                self.tokens[trigram] = (normal_count, important_count + 2)
        
        return self.tokens
    
    def get_unique_tokens(self) -> List[str]:
        """Get list of unique tokens in this document"""
        return list(self.tokens.keys())
    
    def get_total_tokens(self) -> int:
        """Get total number of tokens in this document (including weights)"""
        return sum(normal + important for normal, important in self.tokens.values())
    
    def get_unique_token_count(self) -> int:
        """Get number of unique tokens in this document"""
        return len(self.tokens)
    
    def get_token_frequency(self, token: str) -> int:
        """Get total frequency of a token (normal + important weights)"""
        if token in self.tokens:
            normal, important = self.tokens[token]
            return normal + important
        return 0
    
    def set_doc_id(self, url_mapper: URLMapper) -> int:
        """
        Set or get document ID for this document's URL using URLMapper.
        
        Args:
            url_mapper: URLMapper instance for bidirectional URL-ID mapping
            
        Returns:
            int: The document ID for this URL
        """
        self.doc_id = url_mapper.get_id(self.url)
        return self.doc_id
    
    def _simple_hash(self, url: str) -> int:
        """
        Simple hash function that creates a numeric ID from URL.
        This is reversible through the id_to_url_map.
        
        Args:
            url: URL to hash
            
        Returns:
            int: Hash value as positive integer
        """
        # Simple polynomial rolling hash
        hash_value = 0
        prime = 31
        mod = 2**31 - 1  # Large prime to avoid overflow
        
        for char in url:
            hash_value = (hash_value * prime + ord(char)) % mod
        
        # Ensure positive integer and avoid 0
        return abs(hash_value) + 1
    
    def __str__(self) -> str:
        return f"Document(url='{self.url}', tokens={self.get_total_tokens()}, unique={self.get_unique_token_count()})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def compute_simhash(self, hash_bits: int = 64) -> int:
        """
        Compute SimHash fingerprint for near-duplicate detection.
        
        Args:
            hash_bits: Number of bits in the hash (default 64)
            
        Returns:
            int: SimHash fingerprint as an integer
        """
        if not self.tokens:
            self.tokenize()
        
        if not self.tokens:
            return 0
        
        # Initialize feature vector
        feature_vector = [0] * hash_bits
        

        for token, (normal_count, important_count) in self.tokens.items():
            weight = normal_count + important_count
            # hash token to hash_bits-bit integer
            token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            
            for i in range(hash_bits):
                if token_hash & (1 << i):
                    feature_vector[i] += weight
                else:
                    feature_vector[i] -= weight
        
        fingerprint = 0
        for i in range(hash_bits):
            if feature_vector[i] > 0:
                fingerprint |= (1 << i)
        
        return fingerprint
    
    def get_fingerprint(self) -> int:
        """Get SimHash fingerprint for this document (cached)"""
        if not hasattr(self, '_fingerprint'):
            self._fingerprint = self.compute_simhash()
        return self._fingerprint

class Posting:
    """Represents a posting in the index"""
    def __init__(self, doc_id: int, freq: int):
        self.doc_id = doc_id
        self.freq = freq
    
    def __repr__(self) -> str:
        return f"Posting(doc_id={self.doc_id}, freq={self.freq})"
    
    def tuple(self) -> tuple:
        return (self.doc_id, self.freq)

class NearDuplicateDetector:
    """
    Detects near-duplicate documents using SimHash fingerprinting.
    
    Uses Hamming distance between fingerprints to identify near-duplicates.
    Documents with Hamming distance <= threshold are considered near-duplicates.
    """
    
    def __init__(self, similarity_threshold: int = 3, hash_bits: int = 64):
        """
        Initialize near-duplicate detector.
        
        Args:
            similarity_threshold: Maximum Hamming distance for near-duplicates (default 3)
                                 Lower values = stricter matching
            hash_bits: Number of bits in SimHash (default 64)
        """
        self.similarity_threshold = similarity_threshold
        self.hash_bits = hash_bits
        # Map fingerprint -> set of doc_ids with this fingerprint
        self.fingerprint_to_docs: Dict[int, Set[int]] = defaultdict(set)
        # Map doc_id -> fingerprint
        self.doc_to_fingerprint: Dict[int, int] = {}
    
    def add_document(self, doc_id: int, fingerprint: int):
        self.fingerprint_to_docs[fingerprint].add(doc_id)
        self.doc_to_fingerprint[doc_id] = fingerprint
    
    def find_near_duplicates(self, fingerprint: int) -> List[int]:
        """
        Find all documents that are near-duplicates of the given fingerprint.
        
        Uses Hamming distance to find similar fingerprints.
        
        Args:
            fingerprint: SimHash fingerprint to check
            
        Returns:
            List of doc_ids that are near-duplicates
        """
        near_duplicates = []
        
        # Check all stored fingerprints
        for stored_fp, doc_ids in self.fingerprint_to_docs.items():
            hamming_distance = self._hamming_distance(fingerprint, stored_fp)
            if hamming_distance <= self.similarity_threshold:
                near_duplicates.extend(doc_ids)
        
        return near_duplicates
    
    def is_near_duplicate(self, doc_id: int, fingerprint: int) -> Tuple[bool, List[int]]:
        """
        Check if a document is a near-duplicate of any existing document.
        
        Args:
            doc_id: Document ID to check
            fingerprint: SimHash fingerprint of the document
            
        Returns:
            Tuple of (is_duplicate, list_of_duplicate_doc_ids)
        """
        duplicates = self.find_near_duplicates(fingerprint)
        duplicates = [d for d in duplicates if d != doc_id]
        
        return len(duplicates) > 0, duplicates
    
    def _hamming_distance(self, fp1: int, fp2: int) -> int:
        """
        Calculate Hamming distance between two fingerprints.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            Hamming distance (0 to hash_bits)
        """
        xor_result = fp1 ^ fp2
        # Count number of set bits (popcount)
        distance = bin(xor_result).count('1')
        return distance
    
    def save_fingerprints(self, file_path: Path):
        with open(file_path, 'w', encoding='utf-8') as f:
            for doc_id, fingerprint in sorted(self.doc_to_fingerprint.items()):
                f.write(f"{doc_id}:{fingerprint}\n")
    
    def load_fingerprints(self, file_path: Path):
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                try:
                    doc_id_str, fingerprint_str = line.split(':', 1)
                    doc_id = int(doc_id_str)
                    fingerprint = int(fingerprint_str)
                    
                    self.fingerprint_to_docs[fingerprint].add(doc_id)
                    self.doc_to_fingerprint[doc_id] = fingerprint
                except ValueError:
                    continue
    
    def get_statistics(self) -> Dict:
        total_docs = len(self.doc_to_fingerprint)
        unique_fingerprints = len(self.fingerprint_to_docs)
        
        exact_duplicates = sum(1 for doc_set in self.fingerprint_to_docs.values() if len(doc_set) > 1)
        
        return {
            'total_documents': total_docs,
            'unique_fingerprints': unique_fingerprints,
            'exact_duplicate_groups': exact_duplicates,
            'collision_rate': (total_docs - unique_fingerprints) / total_docs if total_docs > 0 else 0
        }


class InvertedIndex:
    """Manages inverted index with disk offloading and merging"""
    
    def __init__(self, url_mapper: URLMapper, offload_threshold: int = 15000, index_dir: Path = None, 
                 enable_near_duplicate_detection: bool = True, similarity_threshold: int = 3):
        self.url_mapper = url_mapper
        self.offload_threshold = offload_threshold
        self.index_dir = index_dir or Path(__file__).parent.parent / "index"
        self.index_dir.mkdir(exist_ok=True)
        
        # In-memory index: token -> list of (doc_id, term_frequency)
        self.in_memory_index = defaultdict(list)
        self.doc_count = 0
        self.partial_index_files = []
        
        self.enable_near_duplicate_detection = enable_near_duplicate_detection
        if enable_near_duplicate_detection:
            self.duplicate_detector = NearDuplicateDetector(similarity_threshold=similarity_threshold)
            self.duplicates_skipped = 0
            self.duplicates_found = 0
        else:
            self.duplicate_detector = None
    
    def add_document(self, doc: Document, skip_duplicates: bool = False):
        """
        Add a document to the index.
        
        Args:
            doc: Document to add
            skip_duplicates: If True, skip documents that are near-duplicates (default False)
            
        Returns:
            bool: True if document was added, False if skipped as duplicate
        """
        doc_id = doc.set_doc_id(self.url_mapper)
        
        if self.enable_near_duplicate_detection and self.duplicate_detector:
            fingerprint = doc.get_fingerprint()
            is_duplicate, duplicate_doc_ids = self.duplicate_detector.is_near_duplicate(doc_id, fingerprint)
            
            if is_duplicate:
                self.duplicates_found += 1
                if skip_duplicates:
                    self.duplicates_skipped += 1
                    return False

            self.duplicate_detector.add_document(doc_id, fingerprint)
        
        self.doc_count += 1
        
        # Add tokens to in-memory index
        for token, (normal_count, important_count) in doc.tokens.items():
            term_frequency = normal_count + important_count
            self.in_memory_index[token].append((doc_id, term_frequency))
        
        # Offload to disk if threshold reached
        if self.doc_count % self.offload_threshold == 0:
            self._offload_to_disk()
        
        return True
    
    def _offload_to_disk(self):
        """Write current in-memory index to a partial index file"""
        if not self.in_memory_index:
            return
        
        partial_file = self.index_dir / f"partial_index_{len(self.partial_index_files)}.txt"
        self.partial_index_files.append(partial_file)
        
        # Write index to file (token -> list of postings)
        with open(partial_file, 'w', encoding='utf-8') as f:
            for token in sorted(self.in_memory_index.keys()):
                postings = self.in_memory_index[token]
                # Format: token:doc_id1:tf1,doc_id2:tf2,...
                postings_str = ','.join(f"{doc_id}:{tf}" for doc_id, tf in postings)
                f.write(f"{token}:{postings_str}\n")
        
        # Clear in-memory index
        self.in_memory_index.clear()
        print(f"Offloaded index to {partial_file.name} (total partial files: {len(self.partial_index_files)})")
    
    def finalize(self):
        """Offload remaining in-memory index and merge all partial indexes"""
        # Offload any remaining in-memory data
        if self.in_memory_index:
            self._offload_to_disk()
        
        # Merge all partial indexes
        if self.partial_index_files:
            print(f"Merging {len(self.partial_index_files)} partial index files...")
            self._merge_partial_indexes()
        else:
            # No partial files, write in-memory index directly
            self._write_final_index()
    
    def _merge_partial_indexes(self):
        """Merge all partial index files into final index"""
        # Read all partial indexes
        merged_index = defaultdict(list)
        
        for partial_file in self.partial_index_files:
            with open(partial_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    
                    parts = line.split(':', 1)
                    if len(parts) != 2:
                        continue
                    
                    token = parts[0]
                    postings_str = parts[1]
                    
                    # Parse postings: doc_id1:tf1,doc_id2:tf2,...
                    for posting in postings_str.split(','):
                        if ':' in posting:
                            doc_id_str, tf_str = posting.split(':', 1)
                            try:
                                doc_id = int(doc_id_str)
                                tf = int(tf_str)
                                merged_index[token].append((doc_id, tf))
                            except ValueError:
                                continue
        
        # Write merged index to final file
        final_index_file = self.index_dir / "inverted_index.txt"
        with open(final_index_file, 'w', encoding='utf-8') as f:
            for token in sorted(merged_index.keys()):
                postings = merged_index[token]
                # Combine postings for same doc_id (sum term frequencies)
                doc_tf_map = {}
                for doc_id, tf in postings:
                    if doc_id in doc_tf_map:
                        doc_tf_map[doc_id] += tf
                    else:
                        doc_tf_map[doc_id] = tf
                
                # Write combined postings
                postings_str = ','.join(f"{doc_id}:{tf}" for doc_id, tf in sorted(doc_tf_map.items()))
                f.write(f"{token}:{postings_str}\n")
        
        print(f"Merged index written to {final_index_file}")
        
        # Clean up partial files (optional - keep them for debugging)
        # for partial_file in self.partial_index_files:
        #     partial_file.unlink()
    
    def _write_final_index(self):
        """Write in-memory index directly to final file (if no partial files)"""
        final_index_file = self.index_dir / "inverted_index.txt"
        with open(final_index_file, 'w', encoding='utf-8') as f:
            for token in sorted(self.in_memory_index.keys()):
                postings = self.in_memory_index[token]
                postings_str = ','.join(f"{doc_id}:{tf}" for doc_id, tf in postings)
                f.write(f"{token}:{postings_str}\n")
        
        print(f"Index written to {final_index_file}")
    
    def save_url_mapping(self):
        """Save URL to ID mapping to disk"""
        mapping_file = self.index_dir / "url_mapping.txt"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            for url, doc_id in sorted(self.url_mapper.url_to_id.items(), key=lambda x: x[1]):
                f.write(f"{doc_id}:{url}\n")
        print(f"URL mapping saved to {mapping_file}")
    
    def save_fingerprints(self):
        """Save document fingerprints to disk"""
        if self.enable_near_duplicate_detection and self.duplicate_detector:
            fingerprint_file = self.index_dir / "fingerprints.txt"
            self.duplicate_detector.save_fingerprints(fingerprint_file)
            print(f"Fingerprints saved to {fingerprint_file}")
    
    def get_index_size_kb(self) -> float:
        """Calculate total size of index files in KB"""
        total_size = 0
        for file_path in self.index_dir.glob("*.txt"):
            total_size += file_path.stat().st_size
        return total_size / 1024.0
    
    def get_unique_tokens_count(self) -> int:
        """Get count of unique tokens in the final index"""
        final_index_file = self.index_dir / "inverted_index.txt"
        if not final_index_file.exists():
            return len(self.in_memory_index)
        
        count = 0
        with open(final_index_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and ':' in line:
                    count += 1
        return count

   
def parse_html_content(html_content):
    """
    Parse HTML content and extract text, handling broken HTML gracefully.
    Returns clean text content from the HTML.
    """
    if not html_content or not html_content.strip():
        return ""
    
    try:
        # BeautifulSoup can handle broken/malformed HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)
        
        return clean_text
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return ""


def iter_docs(root, stemmer: Optional[PorterStemmer] = None):
    """Iterate through all JSON files and create Document objects"""
    if stemmer is None:
        stemmer = PorterStemmer()
    
    for domain in Path(root).iterdir():
        if domain.is_dir():  # Filter to specific domain
            for page in domain.iterdir():
                if page.suffix == ".json":
                    try:
                        data = json.loads(page.read_text(encoding="utf-8", errors="ignore"))
                        
                        # Create Document object
                        document = Document(
                            url=data["url"],
                            content=data["content"],
                            encoding=data.get("encoding", "utf-8"),
                            stemmer=stemmer
                        )
                        
                        yield document
                        
                    except Exception as e:
                        print(f"Error reading file {page}: {e}")
                        continue

def get_num_docs(root: Path) -> int:
    """
    Get the number of documents in the dataset
    Args:
        root: The root directory of the dataset
    """
    count = 0
    for doc in iter_docs(root):
        count += 1
    return count


def find_near_duplicates_for_doc(doc: Document, duplicate_detector: NearDuplicateDetector, 
                                   url_mapper: URLMapper) -> List[Tuple[int, str, int]]:
    """
    Find near-duplicate documents for a given document.
    
    Args:
        doc: Document to find duplicates for
        duplicate_detector: NearDuplicateDetector instance
        url_mapper: URLMapper to get URLs from doc_ids
        
    Returns:
        List of tuples: (doc_id, url, hamming_distance)
    """
    fingerprint = doc.get_fingerprint()
    doc_id = doc.set_doc_id(url_mapper)
    
    duplicates = []
    for stored_fp, doc_ids in duplicate_detector.fingerprint_to_docs.items():
        hamming_distance = duplicate_detector._hamming_distance(fingerprint, stored_fp)
        if hamming_distance <= duplicate_detector.similarity_threshold:
            for dup_doc_id in doc_ids:
                if dup_doc_id != doc_id:
                    url = url_mapper.get_url(dup_doc_id)
                    duplicates.append((dup_doc_id, url, hamming_distance))
    
    # Sort by Hamming distance (closest first)
    duplicates.sort(key=lambda x: x[2])
    return duplicates


def load_duplicate_detector(index_dir: Path, similarity_threshold: int = 3) -> Optional[NearDuplicateDetector]:
    """
    Load a NearDuplicateDetector from saved fingerprints.
    
    Args:
        index_dir: Directory containing the fingerprints.txt file
        similarity_threshold: Threshold for near-duplicate detection
        
    Returns:
        NearDuplicateDetector instance or None if fingerprints file doesn't exist
    """
    fingerprint_file = index_dir / "fingerprints.txt"
    if not fingerprint_file.exists():
        return None
    
    detector = NearDuplicateDetector(similarity_threshold=similarity_threshold)
    detector.load_fingerprints(fingerprint_file)
    return detector



def main():
    """Build inverted index from the dataset"""
    # Default to DEV folder relative to project root, or use absolute path if provided
    data_root = Path(__file__).parent.parent / "data" / "DEV"
    print(f"Building inverted index from dataset at: {data_root}")
    
    # Check if the directory exists
    if not data_root.exists():
        print(f"Error: Directory {data_root} does not exist!")
        return
    
    # Initialize components
    stemmer = PorterStemmer()  # NLTK Porter stemmer for tokenization
    url_mapper = URLMapper()
    index = InvertedIndex(url_mapper, offload_threshold=15000)
    
    count = 0
    empty_content = 0
    total_tokens = 0
    total_unique_tokens = 0
    
    # Process documents and build index
    for doc in iter_docs(data_root, stemmer):
        count += 1
        
        # Tokenize the document (with stemming and important words)
        doc.tokenize()
        
        # Add document to index (skip_duplicates=False means we index all documents, even duplicates)
        # Set skip_duplicates=True if you want to skip near-duplicate documents
        index.add_document(doc, skip_duplicates=False)
        
        total_tokens += doc.get_total_tokens()
        total_unique_tokens += doc.get_unique_token_count()
        
        if not doc.raw_content:
            empty_content += 1
        
        # Show progress every 1000 documents
        if count % 1000 == 0:
            print(f"Processed {count} documents...")
            
        # Show details for the first few documents
        if count <= 3:
            print(f"\n--- Sample Document {count} ---")
            print(f"URL: {doc.url}")
            print(f"Encoding: {doc.encoding}")
            print(f"Raw content length: {len(doc.raw_content)} chars")
            print(f"Parsed text length: {len(doc.parsed_text)} chars")
            print(f"Total tokens: {doc.get_total_tokens()}")
            print(f"Unique tokens: {doc.get_unique_token_count()}")
            print(f"Parsed text preview: {doc.parsed_text[:200]}...")
            print(f"First 10 tokens: {list(doc.tokens.keys())[:10]}")
            # Show top 5 most frequent tokens
            sorted_tokens = sorted(doc.tokens.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)
            print(f"Top 5 frequent tokens: {[(t, n+i) for t, (n, i) in sorted_tokens[:5]]}")
            print(f"Document object: {doc}")
    
    # Finalize index (offload remaining and merge)
    print(f"\nFinalizing index...")
    index.finalize()
    index.save_url_mapping()
    index.save_fingerprints()
    
    # Calculate statistics
    index_size_kb = index.get_index_size_kb()
    unique_tokens_in_index = index.get_unique_tokens_count()
    
    print(f"\n=== INDEX BUILDING RESULTS ===")
    print(f"Total documents processed: {count}")
    print(f"Documents with empty content: {empty_content}")
    print(f"Total tokens across all documents: {total_tokens:,}")
    print(f"Total unique tokens across all documents: {total_unique_tokens:,}")
    if count > 0:
        print(f"Average tokens per document: {total_tokens / count:.1f}")
        print(f"Average unique tokens per document: {total_unique_tokens / count:.1f}")
    
    print(f"\n=== INDEX STATISTICS ===")
    print(f"Number of indexed documents: {count}")
    print(f"Number of unique tokens: {unique_tokens_in_index:,}")
    print(f"Total size of index on disk: {index_size_kb:.2f} KB")
    
    # Near-duplicate detection statistics
    if index.enable_near_duplicate_detection and index.duplicate_detector:
        print(f"\n=== NEAR-DUPLICATE DETECTION STATISTICS ===")
        stats = index.duplicate_detector.get_statistics()
        print(f"Total documents: {stats['total_documents']}")
        print(f"Unique fingerprints: {stats['unique_fingerprints']}")
        print(f"Exact duplicate groups: {stats['exact_duplicate_groups']}")
        print(f"Near-duplicates found: {index.duplicates_found}")
        print(f"Near-duplicates skipped: {index.duplicates_skipped}")
        print(f"Collision rate: {stats['collision_rate']:.2%}")

if __name__ == "__main__":
    main()
