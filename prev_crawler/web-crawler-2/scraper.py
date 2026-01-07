import re
from urllib.parse import urlparse, urljoin, urldefrag
from lxml import html
from nltk.tokenize import word_tokenize
# GLOBAL VAR for minimum words for a website to be useful
MIN_WORDS = 100

# Allowed domains for crawling - updated for current crawler target
ALLOWED_DOMAINS = [
    "aljazeera.com",
    "www.aljazeera.com"
]

# common stop words provided in write-up
stopwords = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd",
    "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
}

analytics = {
    # set of the unique pages found
    "unique_pages": set(),
    # the url to the page with most words
    "longest_page_url": None,
    # the count of words in the longest page
    "longest_page_word_count": 0,
    # dictionary for the words parsed and their count
    "word_frequencies": {},
    # dictionary for the subdomains and their count
    "subdomain_counts": {}
}



def finalize_report():
        """
        Writes the final statistics from the complete web crawl.
        1. Number of Unique URLs
        2. Longest page in terms of words
        3. 50 Most common words from entire set of crawled sites
        4. Subdomains of "*.uci.edu" with their corresponding count
        """
        try:
            with open("report.txt", "w") as f:
                # number of unique pages
                f.write("1. Number of unique pages found\n")
                f.write(f"{len(analytics['unique_pages'])}\n\n")

                # longest page (by number of words)
                f.write("2. Longest page (by number of words)\n")
                if analytics["longest_page_url"]:
                    f.write(f"URL: {analytics['longest_page_url']}\n")
                    f.write(f"Word count: {analytics['longest_page_word_count']}\n\n")
                else:
                    f.write("No pages processed.\n\n")

                # 50 most common words
                f.write("3. 50 most common words\n")

                # sorts the dictionary and then uses the reverse=True to retrieve the last 50 (highest count) words
                sorted_words = sorted(
                    analytics["word_frequencies"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:50]

                # writes the 50 top words to the file
                for word, freq in sorted_words:
                    f.write(f"{word}: {freq}\n")
                f.write("\n")

                # subdomains under *.uci.edu and their unique page counts
                f.write("4. Subdomains found under *.uci.edu\n")

                if analytics["subdomain_counts"]:
                    for subdomain in sorted(analytics["subdomain_counts"].keys()):
                        count = analytics["subdomain_counts"][subdomain]
                        f.write(f"{subdomain}, {count}\n")
                else:
                    # shouldn't run this tbh
                    f.write("No subdomains found.\n")

            print(
                f"[Analytics] Results written to report.txt\n"
            )

        except Exception as e:
            print(f"[Analytics ERROR] Failed to write output file: {e}")


def extract_text_from_tree(tree):
    """Helper function to extract clean text from lxml tree (replaces BeautifulSoup logic)"""
    # Remove script, style, and noscript elements (same as groupmate's logic)
    for element in tree.xpath('//script | //style | //noscript'):
        element.getparent().remove(element)
    
    # Get text content (equivalent to soup.get_text(separator=" ", strip=True))
    text = tree.text_content()
    # Clean up whitespace to match BeautifulSoup's separator=" ", strip=True behavior
    text = ' '.join(text.split())
    return text

def is_alnum(char: str) -> bool:
    """
    Helper function to check if a character is alphanumeric.
    Enhanced to handle web content better.
    """
    if len(char) != 1:
        return False
    
    # Check if it's a digit (0-9)
    if '0' <= char <= '9':
        return True
    
    # Check if it's a lowercase letter (a-z)
    if 'a' <= char <= 'z':
        return True
    
    # Check if it's an uppercase letter (A-Z)
    if 'A' <= char <= 'Z':
        return True
    
    return False

def tokenize_text(text):
    """
    Enhanced tokenization for web content (replaces groupmate's regex)
    Better handling of edge cases than simple regex approach.
    """
    if not text:
        return []
    
    tokens = []
    current_token = ""
    
    for char in text:
        if is_alnum(char):
            current_token += char.lower()
        else:
            if current_token:
                tokens.append(current_token)
                current_token = ""
    
    # Don't forget the last token
    if current_token:
        tokens.append(current_token)
    
    return tokens

def update_word_frequencies(words):
    """Helper function to update word frequency analytics"""
    for word in words:
        # excludes any stopwords from the set
        if word not in stopwords:
            analytics["word_frequencies"][word] = (analytics["word_frequencies"].get(word, 0) + 1)

def update_longest_page(clean_url, word_count):
    """Helper function to update longest page analytics"""
    # Will update the longest page analytics
    if word_count > analytics["longest_page_word_count"]:
        analytics["longest_page_url"] = clean_url
        analytics["longest_page_word_count"] = word_count

def update_subdomain_analytics(clean_url):
    """Helper function to implement subdomain tracking for report question 4"""
    try:
        parsed = urlparse(clean_url)
        netloc = parsed.netloc.lower()
        
        # Check if netloc exactly matches or is a subdomain of allowed domains
        is_valid_domain = False
        for domain in ALLOWED_DOMAINS:
            if netloc == domain or netloc.endswith('.' + domain):
                is_valid_domain = True
                break
        
        if is_valid_domain:
            # Count unique pages per subdomain
            if netloc not in analytics["subdomain_counts"]:
                analytics["subdomain_counts"][netloc] = 0
            analytics["subdomain_counts"][netloc] += 1
    except Exception as e:
        # Silently handle any URL parsing errors
        pass

def save_analytics_to_file():
    """Helper function to save analytics data for report generation"""
    import json
    
    # Convert set to list for JSON serialization
    analytics_copy = analytics.copy()
    analytics_copy["unique_pages"] = list(analytics["unique_pages"])
    
    with open("analytics_data.json", "w") as f:
        json.dump(analytics_copy, f, indent=2)
    
    print(f"Analytics saved: {len(analytics['unique_pages'])} unique pages crawled")

def process_page_analytics(clean_url, tree):
    """Helper function to process all analytics for a page"""
    try:
        # Extract text using lxml instead of BeautifulSoup
        text = extract_text_from_tree(tree)
        
        # Tokenize using imported tokenizer module
        words = word_tokenize(text)
        
        word_count = len(words)
        # will skip pages with minimal content (groupmate's logic)
        if word_count < MIN_WORDS: # REVIEW BC IDK IF ITS TOO LOW OR HIGH 
            return False  # Indicates page should be skipped
        
        # Add URL to unique pages set (this was missing!)
        analytics["unique_pages"].add(clean_url)
        
        # Update analytics using helper functions
        update_word_frequencies(words)
        update_longest_page(clean_url, word_count)
        update_subdomain_analytics(clean_url)
        
        # Save analytics periodically (every 100 pages)
        if len(analytics["unique_pages"]) % 100 == 0:
            save_analytics_to_file()
        
        return True  # Indicates page was processed successfully
        
    except Exception as e:
        print(f"Error processing analytics for {clean_url}: {e}")
        return False

def scraper(url, resp):
    links = extract_next_links(url, resp)
    # will be a list containing all the valid links after extraction
    valid_links = [link for link in links if is_valid(link)]
    # checks if the response is valid and if there is any valid content to parse
    if (resp.status == 200) and (resp.raw_response) and (resp.raw_response.content):
        # this will separate the url from the fragment(fragment not needed)
        # this is just a double check possibly redundent if URL is still clean from extraction
        clean_url, fragment = urldefrag(resp.url if resp.url else url)
        # checks if url is in set of unique pages, if not then add it
        if clean_url not in analytics["unique_pages"]:
            try:
                tree = html.fromstring(resp.raw_response.content)
                success = process_page_analytics(clean_url, tree)
                if not success:
                    print("[SCRAPER] skipped this page")
                    return valid_links  # Skip if page has minimal content
                analytics["unique_pages"].add(clean_url)
                
            except Exception as e:
                print(f"Error for {clean_url}: {e}")
    return valid_links

def extract_links_from_tree(tree, base_url):
    """Helper function to extract links using lxml (replaces BeautifulSoup logic)"""
    # Extract all href attributes from anchor tags (equivalent to soup.find_all("a", href=True))
    raw_links = tree.xpath('//a/@href')
    
    new_urls = []
    for link in raw_links:
        # Process all href values, including empty ones (which resolve to base URL)
        # Convert relative URLs to absolute URLs
        absolute_url = urljoin(base_url, link)
        
        # Remove fragment (everything after #) - proper way
        absolute_url, _ = urldefrag(absolute_url)
        
        if absolute_url:
            new_urls.append(absolute_url)
    
    return new_urls

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    new_urls = []

    if resp.status != 200:
        return new_urls

    if resp.raw_response is None or resp.raw_response.content is None:
        return new_urls
    
    try:
        # Parse HTML content with lxml instead of BeautifulSoup
        tree = html.fromstring(resp.raw_response.content)
        base_url = resp.url if resp.url else url
        
        # Extract links using helper function
        new_urls = extract_links_from_tree(tree, base_url)
    
    except Exception as e:
        print(f"Error parsing HTML for {url}: {e}")
        return []
    
    # Remove duplicates while preserving order (keeping groupmate's exact logic)
    seen = set()
    unique_links = []
    for url in new_urls:
        if url not in seen:
            seen.add(url)
            unique_links.append(url)

    return unique_links

def check_for_traps(url, parsed):
    """
    Returns False if the URL is considered a trap (calendar loops, 
    dynamic date/event queries, ...), True otherwise.
    """

    # blocks month/year URLs that often repeat
    if re.search(r"/\d{4}-\d{2}(/|$)", parsed.path):
        return False
    # seperate cases of events with different date formatting (didn't get covered by other case)
    if re.search(r"/events/(today|month|\d{4}-\d{2}(-\d{2})?)", parsed.path, re.IGNORECASE):
        return False
    
    # blocks any login pages from being added to frontier
    if re.search(r"login", url, re.IGNORECASE):
        return False
    
    
    # necessary for any pagination loops (page=70, page=71, page=72, ...)
    pagination_patterns = ('page=', 'start=', 'offset=')
    for p in pagination_patterns:
        m = re.search(rf'{p}(\d+)', parsed.query)
        if m and int(m.group(1)) > 5:
            return False
        
    # works on removing version traps like Wiki
    query_parts = parsed.query.split('&') if parsed.query else []
    if any(part.startswith(('version=', 'do=', 'rev=')) for part in query_parts):
        return False
    
    # blocks the wiki traps that take you down a spiral of pages that you can't even access
    if re.search(r"/wiki/.*/timeline", url, re.IGNORECASE) and "from=" in parsed.query:
        return False
    # Passed all traps
    return True
    
    
        
def is_valid(url):
    """
    Decide whether to crawl this url or not. 
    If you decide to crawl it, return True; otherwise return False.
    There are already some conditions that return False.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # Check if URL is in allowed UCI domains - CRITICAL REQUIREMENT
        netloc = parsed.netloc.lower()
        
        # Check if netloc exactly matches or is a subdomain of allowed domains
        is_valid_domain = False
        for domain in ALLOWED_DOMAINS:
            if netloc == domain or netloc.endswith('.' + domain):
                is_valid_domain = True
                break
        
        if not is_valid_domain:
            return False
        
        # checks if the URL is one of the traps (includes print testing)
        if not check_for_traps(url, parsed):
            print(f"[TRAP BLOCKED] {url}")
            return False
        
        # Check for unwanted file extensions
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|apk|war|txt|pps|ppsx|scm"
            + r"|thmx|mso|arff|rtf|jar|csv|img|c|cpp|h|py|java"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
        
        return True

    except TypeError:
        print ("TypeError for ", parsed)
        return False
