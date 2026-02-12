import re
from urllib.parse import urlparse, urljoin, urldefrag
from lxml import html
from nltk.tokenize import word_tokenize
import sys
import signal
import json
import os
import hashlib

# GLOBAL VAR for minimum words for a website to be useful
MIN_WORDS = 100

# Allowed domains for crawling - updated for current crawler target
ALLOWED_DOMAINS = [
    "www.aljazeera.com",
    "aljazeera.com"
]

# Base directory for storing downloaded pages
DATA_STORAGE_DIR = "data/downloaded_pages"

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


def get_subdomain_from_url(url):
    """Extract subdomain from URL for folder organization"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Replace dots with underscores for folder names
        return domain.replace(".", "_")
    except:
        return "unknown"


def generate_filename_hash(url):
    """Generate a hash-based filename for the page"""
    return hashlib.sha256(url.encode()).hexdigest()


def get_slug(url):
    path = urlparse(url).path  # "/en/pressing-for-protection/"
    parts = [p for p in path.split("/") if p]  # ["en", "pressing-for-protection"]
    if len(parts) >= 2 and parts[0] == "en":
        slug=parts[1]
        return slug.replace("-", " ").title()
    return None

def extract_article_text(soup):
    """
    Extracts the main article text by locating the container
    that actually holds readable paragraph content.
    """

    candidate_containers = [
        ".rich-text",                 # CMS rich text blocks
        ".article-content",           # common article wrapper
        "[data-content-type='article-body']",
        "article"                     # semantic fallback
    ]

    for selector in candidate_containers:
        container = soup.select_one(selector)
        if not container:
            continue

        # Collect visible, non-empty paragraphs
        paragraphs = []
        for p in container.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

        # If we found real content, stop searching
        if paragraphs:
            return "\n\n".join(paragraphs)

    # Nothing matched
    return None

def save_page_to_json(url, content):
    """Save page content to JSON file organized by subdomain"""
    try:
        subdomain = get_subdomain_from_url(url)
        directory = os.path.join(DATA_STORAGE_DIR, subdomain)
        
        # Create directory structure if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Generate filename based on URL hash
        filename = generate_filename_hash(url) + ".json"
        filepath = os.path.join(directory, filename)

        # Prepare defaults
        headline = None
        article = None

        # If we have HTML content as a string, create a BeautifulSoup for extraction
        soup = None
        if isinstance(content, str):
            try:
                from bs4 import BeautifulSoup as _BS
                soup = _BS(content, "html.parser")
            except Exception:
                soup = None

        # Use substring check (Python strings don't have `includes`)
        if "liberties" in url:
            image = None

            if soup:
                h1 = soup.find('h1')
                if h1 and h1.get_text(strip=True):
                    headline = h1.get_text(strip=True)
                else:
                    headline = get_slug(url)

                article = extract_article_text(soup)

                # Extract image
                og_image = soup.find("meta", property="og:image")
                if og_image and og_image.get("content"):
                    image = og_image["content"]

                if not image:
                    article_img = soup.find("img")
                    if article_img and article_img.get("src"):
                        image = article_img["src"]
            else:
                headline = get_slug(url)
                article = None
                image = None

        # Create JSON object with URL and content
        page_data = {
            "url": url,
            "headline": headline,
            # "date":date,
            "article": article,
            "content": content,
            "image" : image, 
            "encoding": "utf-8"
        }
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False)
        print (image)
        print(article)
        print(headline)
        print(f"[STORAGE] Saved page: {url}")
        return True
        
    except Exception as e:
        print(f"[STORAGE ERROR] Failed to save page {url}: {e}")
        return False



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

def sigint_handler(signum,frame):
    if signum==2:
        print("You have pressed ctrl+c")
        sys.exit(0)

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
                
                # Save page content to JSON file
                try:
                    content = resp.raw_response.content.decode('utf-8', errors='ignore')
                    save_page_to_json(clean_url, content)
                except Exception as e:
                    print(f"[SCRAPER] Failed to save page content: {e}")
                
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
    
    # Remove duplicates while preserving order 
    seen = set()
    unique_links = []
    for url in new_urls:
        if url not in seen:
            seen.add(url)
            unique_links.append(url)
            print(unique_links)
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


save_page_to_json("https://liberties.aljazeera.com/en/pressing-for-protection/", "<!DOCTYPE html>\n<html lang=\"en-US\">\n\t<head>\n\t\t<meta charset=\"UTF-8\">\n\t\t<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\t\t<meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">\n\t\t<link rel=\"profile\" href=\"//gmpg.org/xfn/11\">\n\n\t\t<!--  Essential META Tags -->\n\n\t\t<meta property=\"og:title\" content=\"Pressing for protection\">\n\t\t<meta property=\"og:description\" content=\"\">\n\t\t<meta property=\"og:image\" content=\"https://liberties.aljazeera.com/resources/uploads/2025/08/1756212916.webp\">\n\t\t<meta property=\"og:url\" content=\"https://liberties.aljazeera.com/en/pressing-for-protection/\">\n\t\t<meta name=\"twitter:card\" content=\"summary_large_image\">\n\n\n\t\t<!--  Non-Essential, But Recommended -->\n\n\t\t<meta property=\"og:site_name\" content=\"Human Rights &amp; Public Liberties\">\n\t\t<meta name=\"twitter:image:alt\" content=\"Pressing for protection\">\n\n\n\n\t\t<title>Pressing for protection &#8211; Human Rights &amp; Public Liberties</title>\n<meta name='robots' content='max-image-preview:large' />\n\t<style>img:is([sizes=\"auto\" i], [sizes^=\"auto,\" i]) { contain-intrinsic-size: 3000px 1500px }</style>\n\t<link rel=\"alternate\" hreflang=\"en\" href=\"https://liberties.aljazeera.com/en/pressing-for-protection/\" />\n<link rel='stylesheet' id='wp-block-library-css' href='https://liberties.aljazeera.com/site-includes/css/dist/block-library/style.min.css' type='text/css' media='all' />\n<style id='classic-theme-styles-inline-css' type='text/css'>\n/*! This file is auto-generated */\n.wp-block-button__link{color:#fff;background-color:#32373c;border-radius:9999px;box-shadow:none;text-decoration:none;padding:calc(.667em + 2px) calc(1.333em + 2px);font-size:1.125em}.wp-block-file__button{background:#32373c;color:#fff;text-decoration:none}\n</style>\n<style id='global-styles-inline-css' type='text/css'>\n:root{--wp--preset--aspect-ratio--square: 1;--wp--preset--aspect-ratio--4-3: 4/3;--wp--preset--aspect-ratio--3-4: 3/4;--wp--preset--aspect-ratio--3-2: 3/2;--wp--preset--aspect-ratio--2-3: 2/3;--wp--preset--aspect-ratio--16-9: 16/9;--wp--preset--aspect-ratio--9-16: 9/16;--wp--preset--color--black: #000000;--wp--preset--color--cyan-bluish-gray: #abb8c3;--wp--preset--color--white: #ffffff;--wp--preset--color--pale-pink: #f78da7;--wp--preset--color--vivid-red: #cf2e2e;--wp--preset--color--luminous-vivid-orange: #ff6900;--wp--preset--color--luminous-vivid-amber: #fcb900;--wp--preset--color--light-green-cyan: #7bdcb5;--wp--preset--color--vivid-green-cyan: #00d084;--wp--preset--color--pale-cyan-blue: #8ed1fc;--wp--preset--color--vivid-cyan-blue: #0693e3;--wp--preset--color--vivid-purple: #9b51e0;--wp--preset--gradient--vivid-cyan-blue-to-vivid-purple: linear-gradient(135deg,rgba(6,147,227,1) 0%,rgb(155,81,224) 100%);--wp--preset--gradient--light-green-cyan-to-vivid-green-cyan: linear-gradient(135deg,rgb(122,220,180) 0%,rgb(0,208,130) 100%);--wp--preset--gradient--luminous-vivid-amber-to-luminous-vivid-orange: linear-gradient(135deg,rgba(252,185,0,1) 0%,rgba(255,105,0,1) 100%);--wp--preset--gradient--luminous-vivid-orange-to-vivid-red: linear-gradient(135deg,rgba(255,105,0,1) 0%,rgb(207,46,46) 100%);--wp--preset--gradient--very-light-gray-to-cyan-bluish-gray: linear-gradient(135deg,rgb(238,238,238) 0%,rgb(169,184,195) 100%);--wp--preset--gradient--cool-to-warm-spectrum: linear-gradient(135deg,rgb(74,234,220) 0%,rgb(151,120,209) 20%,rgb(207,42,186) 40%,rgb(238,44,130) 60%,rgb(251,105,98) 80%,rgb(254,248,76) 100%);--wp--preset--gradient--blush-light-purple: linear-gradient(135deg,rgb(255,206,236) 0%,rgb(152,150,240) 100%);--wp--preset--gradient--blush-bordeaux: linear-gradient(135deg,rgb(254,205,165) 0%,rgb(254,45,45) 50%,rgb(107,0,62) 100%);--wp--preset--gradient--luminous-dusk: linear-gradient(135deg,rgb(255,203,112) 0%,rgb(199,81,192) 50%,rgb(65,88,208) 100%);--wp--preset--gradient--pale-ocean: linear-gradient(135deg,rgb(255,245,203) 0%,rgb(182,227,212) 50%,rgb(51,167,181) 100%);--wp--preset--gradient--electric-grass: linear-gradient(135deg,rgb(202,248,128) 0%,rgb(113,206,126) 100%);--wp--preset--gradient--midnight: linear-gradient(135deg,rgb(2,3,129) 0%,rgb(40,116,252) 100%);--wp--preset--font-size--small: 13px;--wp--preset--font-size--medium: 20px;--wp--preset--font-size--large: 36px;--wp--preset--font-size--x-large: 42px;--wp--preset--spacing--20: 0.44rem;--wp--preset--spacing--30: 0.67rem;--wp--preset--spacing--40: 1rem;--wp--preset--spacing--50: 1.5rem;--wp--preset--spacing--60: 2.25rem;--wp--preset--spacing--70: 3.38rem;--wp--preset--spacing--80: 5.06rem;--wp--preset--shadow--natural: 6px 6px 9px rgba(0, 0, 0, 0.2);--wp--preset--shadow--deep: 12px 12px 50px rgba(0, 0, 0, 0.4);--wp--preset--shadow--sharp: 6px 6px 0px rgba(0, 0, 0, 0.2);--wp--preset--shadow--outlined: 6px 6px 0px -3px rgba(255, 255, 255, 1), 6px 6px rgba(0, 0, 0, 1);--wp--preset--shadow--crisp: 6px 6px 0px rgba(0, 0, 0, 1);}:where(.is-layout-flex){gap: 0.5em;}:where(.is-layout-grid){gap: 0.5em;}body .is-layout-flex{display: flex;}.is-layout-flex{flex-wrap: wrap;align-items: center;}.is-layout-flex > :is(*, div){margin: 0;}body .is-layout-grid{display: grid;}.is-layout-grid > :is(*, div){margin: 0;}:where(.wp-block-columns.is-layout-flex){gap: 2em;}:where(.wp-block-columns.is-layout-grid){gap: 2em;}:where(.wp-block-post-template.is-layout-flex){gap: 1.25em;}:where(.wp-block-post-template.is-layout-grid){gap: 1.25em;}.has-black-color{color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-color{color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-color{color: var(--wp--preset--color--white) !important;}.has-pale-pink-color{color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-color{color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-color{color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-color{color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-color{color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-color{color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-color{color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-color{color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-color{color: var(--wp--preset--color--vivid-purple) !important;}.has-black-background-color{background-color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-background-color{background-color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-background-color{background-color: var(--wp--preset--color--white) !important;}.has-pale-pink-background-color{background-color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-background-color{background-color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-background-color{background-color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-background-color{background-color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-background-color{background-color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-background-color{background-color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-background-color{background-color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-background-color{background-color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-background-color{background-color: var(--wp--preset--color--vivid-purple) !important;}.has-black-border-color{border-color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-border-color{border-color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-border-color{border-color: var(--wp--preset--color--white) !important;}.has-pale-pink-border-color{border-color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-border-color{border-color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-border-color{border-color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-border-color{border-color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-border-color{border-color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-border-color{border-color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-border-color{border-color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-border-color{border-color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-border-color{border-color: var(--wp--preset--color--vivid-purple) !important;}.has-vivid-cyan-blue-to-vivid-purple-gradient-background{background: var(--wp--preset--gradient--vivid-cyan-blue-to-vivid-purple) !important;}.has-light-green-cyan-to-vivid-green-cyan-gradient-background{background: var(--wp--preset--gradient--light-green-cyan-to-vivid-green-cyan) !important;}.has-luminous-vivid-amber-to-luminous-vivid-orange-gradient-background{background: var(--wp--preset--gradient--luminous-vivid-amber-to-luminous-vivid-orange) !important;}.has-luminous-vivid-orange-to-vivid-red-gradient-background{background: var(--wp--preset--gradient--luminous-vivid-orange-to-vivid-red) !important;}.has-very-light-gray-to-cyan-bluish-gray-gradient-background{background: var(--wp--preset--gradient--very-light-gray-to-cyan-bluish-gray) !important;}.has-cool-to-warm-spectrum-gradient-background{background: var(--wp--preset--gradient--cool-to-warm-spectrum) !important;}.has-blush-light-purple-gradient-background{background: var(--wp--preset--gradient--blush-light-purple) !important;}.has-blush-bordeaux-gradient-background{background: var(--wp--preset--gradient--blush-bordeaux) !important;}.has-luminous-dusk-gradient-background{background: var(--wp--preset--gradient--luminous-dusk) !important;}.has-pale-ocean-gradient-background{background: var(--wp--preset--gradient--pale-ocean) !important;}.has-electric-grass-gradient-background{background: var(--wp--preset--gradient--electric-grass) !important;}.has-midnight-gradient-background{background: var(--wp--preset--gradient--midnight) !important;}.has-small-font-size{font-size: var(--wp--preset--font-size--small) !important;}.has-medium-font-size{font-size: var(--wp--preset--font-size--medium) !important;}.has-large-font-size{font-size: var(--wp--preset--font-size--large) !important;}.has-x-large-font-size{font-size: var(--wp--preset--font-size--x-large) !important;}\n:where(.wp-block-post-template.is-layout-flex){gap: 1.25em;}:where(.wp-block-post-template.is-layout-grid){gap: 1.25em;}\n:where(.wp-block-columns.is-layout-flex){gap: 2em;}:where(.wp-block-columns.is-layout-grid){gap: 2em;}\n:root :where(.wp-block-pullquote){font-size: 1.5em;line-height: 1.6;}\n</style>\n<link rel='stylesheet' id='fontawesome-pro-css' href='https://liberties.aljazeera.com/resources/plugins/ajwa-fw-loader/7.0.0/css/all.min.css' type='text/css' media='all' />\n<link rel='stylesheet' id='wpml-legacy-horizontal-list-0-css' href='https://liberties.aljazeera.com/resources/plugins/sitepress-multilingual-cms/templates/language-switchers/legacy-list-horizontal/style.min.css' type='text/css' media='all' />\n<link rel='stylesheet' id='bootstrap-styles-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/bootstrap/css/bootstrap.min.css' type='text/css' media='all' />\n<link rel='stylesheet' id='main-style-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/assets/css/style.css' type='text/css' media='all' />\n<link rel='stylesheet' id='rtl-style-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/assets/css/style-rtl.css' type='text/css' media='all' />\n<link rel='stylesheet' id='resp-style-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/assets/css/style-responsive.css' type='text/css' media='all' />\n<link rel='stylesheet' id='slick-styles-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/slick/slick.css' type='text/css' media='all' />\n<link rel='stylesheet' id='slick-theme-styles-css' href='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/slick/slick-theme.css' type='text/css' media='all' />\n<script type=\"text/javascript\" src=\"https://liberties.aljazeera.com/site-includes/js/jquery/jquery.min.js\" id=\"jquery-core-js\"></script>\n<script type=\"text/javascript\" src=\"https://liberties.aljazeera.com/site-includes/js/jquery/jquery-migrate.min.js\" id=\"jquery-migrate-js\"></script>\n<link rel=\"alternate\" title=\"oEmbed (JSON)\" type=\"application/json+oembed\" href=\"https://liberties.aljazeera.com/en/wp-json/oembed/1.0/embed?url=https%3A%2F%2Fliberties.aljazeera.com%2Fen%2Fpressing-for-protection%2F\" />\n<link rel=\"alternate\" title=\"oEmbed (XML)\" type=\"text/xml+oembed\" href=\"https://liberties.aljazeera.com/en/wp-json/oembed/1.0/embed?url=https%3A%2F%2Fliberties.aljazeera.com%2Fen%2Fpressing-for-protection%2F&#038;format=xml\" />\n<meta name=\"generator\" content=\"WPML ver:4.8.4 stt:5,1;\" />\n\t\t<style type=\"text/css\" id=\"wp-custom-css\">\n\t\t\t.fa-google-plus:before {\n    content: \"\";\n    display: inline-block;\n    width: 1.3em;\n    height: 1.3em;\n    background: url(\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCA2NDAgNjQwJz48cGF0aCBmaWxsPSdjdXJyZW50Q29sb3InIGQ9J00zODYuMyAyOTIuNUMzODguMSAzMDIuMiAzODkuNCAzMTEuOSAzODkuNCAzMjQuNUMzODkuNCA0MzQuMyAzMTUuOCA1MTIgMjA1IDUxMkM5OC45IDUxMiAxMyA0MjYuMSAxMyAzMjBDMTMgMjEzLjkgOTguOSAxMjggMjA1IDEyOEMyNTYuOSAxMjggMzAwLjEgMTQ2LjkgMzMzLjYgMTc4LjNMMjgxLjUgMjI4LjNDMjY3LjQgMjE0LjcgMjQyLjUgMTk4LjcgMjA1IDE5OC43QzEzOS41IDE5OC43IDg2LjEgMjUyLjkgODYuMSAzMjBDODYuMSAzODcuMSAxMzkuNSA0NDEuMyAyMDUgNDQxLjNDMjgxIDQ0MS4zIDMwOS41IDM4Ni42IDMxNCAzNTguNUwyMDUgMzU4LjVMMjA1IDI5Mi41TDM4Ni4zIDI5Mi41TDM4Ni4zIDI5Mi41ek01NzEuNyAyOTguOUw1NzEuNyAyNDMuMkw1MTUuNyAyNDMuMkw1MTUuNyAyOTguOUw0NjAgMjk4LjlMNDYwIDM1NC45TDUxNS43IDM1NC45TDUxNS43IDQxMC42TDU3MS43IDQxMC42TDU3MS43IDM1NC45TDYyNy40IDM1NC45TDYyNy40IDI5OC45TDU3MS43IDI5OC45eicvPjwvc3ZnPg==\") no-repeat center / contain;\n}\n\n.fa-facebook:before {\n    content: \"\";\n    display: inline-block;\n    width: 1.3em;\n    height: 1.3em;\n    background: url(\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCA2NDAgNjQwJz48cGF0aCBmaWxsPSdjdXJyZW50Q29sb3InIGQ9J00yNDAgMzYzLjNMMjQwIDU3NkwzNTYgNTc2TDM1NiAzNjMuM0w0NDIuNSAzNjMuM0w0NjAuNSAyNjUuNUwzNTYgMjY1LjVMMzU2IDIzMC45QzM1NiAxNzkuMiAzNzYuMyAxNTkuNCA0MjguNyAxNTkuNEM0NDUgMTU5LjQgNDU4LjEgMTU5LjggNDY1LjcgMTYwLjZMNDY1LjcgNzEuOUM0NTEuNCA2OCA0MTYuNCA2NCAzOTYuMiA2NEMyODkuMyA2NCAyNDAgMTE0LjUgMjQwIDIyMy40TDI0MCAyNjUuNUwxNzQgMjY1LjVMMTc0IDM2My4zTDI0MCAzNjMuM3onLz48L3N2Zz4=\") no-repeat center / contain;\n}\n\n.fa-twitter:before {\n    content: \"\";\n    display: inline-block;\n    width: 1.3em;\n    height: 1.3em;\n    background: url(\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCA2NDAgNjQwJz48cGF0aCBmaWxsPSdjdXJyZW50Q29sb3InIGQ9J000NTMuMiAxMTJMNTIzLjggMTEyTDM2OS42IDI4OC4yTDU1MSA1MjhMNDA5IDUyOEwyOTcuNyAzODIuNkwxNzAuNSA1MjhMOTkuOCA1MjhMMjY0LjcgMzM5LjVMOTAuOCAxMTJMMjM2LjQgMTEyTDMzNi45IDI0NC45TDQ1My4yIDExMnpNNDI4LjQgNDg1LjhMNDY3LjUgNDg1LjhMMjE1LjEgMTUyTDE3My4xIDE1Mkw0MjguNCA0ODUuOHonLz48L3N2Zz4=\") no-repeat center / contain;\n}\n\n\n#ajmnfooter .wrap.footer-wrap {\n    background: #191a1c;\n}\n.top-header {\n    z-index: 3;\n}\n.page-content.post > .page-title-figure > .figure-body {\n\tposition: initial !important;\n}\n\n.website-ads a{\n\tdisplay: inline-block;\n\tmargin-bottom: 10px !important;\n}\n\n_ul.terms-block li a {\n    opacity: 1;\n    color: #000 !important;\n    background-color: #fff !important;\n    border: 0 !important;\n}\n_ul.terms-block li a:hover {\n    opacity: 1;\n    color: #fff !important;\n    background-color: #000 !important;\n    border: 0 !important;\n}\n.cat-on-top ul.terms-block {\n    z-index: 2 !important;\n}\n.block-5 > .row {\n\theight: 100%;\n}\t\t</style>\n\t\t\n<!-- ************************************************* -->\n<!-- Google tag (gtag.js) -->\r\n<script async src=\"https://www.googletagmanager.com/gtag/js?id=G-H9RSCDDE0L\"></script>\r\n<script> \r\nwindow.dataLayer = window.dataLayer || []; \r\nfunction gtag(){dataLayer.push(arguments);} \r\ngtag('js', new Date()); \r\ngtag('config', 'G-H9RSCDDE0L'); \r\n</script>\r\n<!-- End Google tag (gtag.js) -->\n<!-- ************************************************* -->\n\t</head>\n\n\t<body class=\"en_US\">\n\t\t<style>\n\t\t\t@media only screen and (max-width: 720px) {\n\t\t\t\t#wpadminbar {display: none;}\t\n\t\t\t}\n\t\t</style>\n\t\t<!-- start wrapper -->\n\t\t<div class=\"wrapper\">\n\t\t\t<h1 id=\"mobile-logo\">\n\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/\">\n\t\t\t\t\t<img src='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/Public-Liberties-and-Human-Rights-Center-Logo-en.svg?id=1763636830' alt=\"Human Rights &amp; Public Liberties\">\n\t\t\t\t</a>\n\t\t\t\t<ul class=\"social-list\">\n\n\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\t</a> </li>\n\t\t\t\t</ul>\n\t\t\t</h1>\n\t\t\t<div id=\"menu-button\">\n\t\t\t\t<div class=\"cursor\"> \n\t\t\t\t\t<!--Menu-->\n\t\t\t\t\t<div id=\"nav-button\"> <span class=\"nav-bar\"></span> <span class=\"nav-bar\"></span> <span class=\"nav-bar\"></span> </div>\n\t\t\t\t</div>\n\t\t\t</div>\n\n\t\t\t<!-- Top Header -->\n\n\t\t\t<header>\n\t\t\t\t<h1 id=\"logo\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/\">\n\t\t\t\t\t\t<img src='https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/Public-Liberties-and-Human-Rights-Center-Logo-en.svg?id=1763636830' alt=\"Human Rights &amp; Public Liberties\">\n\t\t\t\t\t</a>\n\n\t\t\t\t</h1>\n\n\t\t\t\t<div class=\"language\">\n\t\t\t\t\t\n<div class=\"lang_sel_list_horizontal wpml-ls-statics-shortcode_actions wpml-ls wpml-ls-legacy-list-horizontal\" id=\"lang_sel_list\">\n\t<ul role=\"menu\"><li class=\"icl-ar wpml-ls-slot-shortcode_actions wpml-ls-item wpml-ls-item-ar wpml-ls-first-item wpml-ls-last-item wpml-ls-item-legacy-list-horizontal\" role=\"none\">\n\t\t\t\t<a href=\"https://liberties.aljazeera.com/\" class=\"wpml-ls-link\" role=\"menuitem\"  aria-label=\"Switch to العربية\" title=\"Switch to العربية\" >\n                    <span class=\"wpml-ls-native icl_lang_sel_native\" lang=\"ar\">العربية</span></a>\n\t\t\t</li></ul>\n</div>\n\t\t\t\t</div>\n\n\n\t\t\t\t<!-- start main nav -->\n\t\t\t\t<nav id=\"main-nav\">\n\n\t\t\t\t\t<ul id=\"menu-main-menu-en\" class=\"option-set clearfix\"><li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/news/\">News</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/armed-conflict/\">Armed Conflict</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/courts-and-justice/\">Courts and Justice</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/interviews/\">Interviews</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/long-read/\">Long Read</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/climate-environment/\">Climate &amp; Environment</a></li>\n<li class=\"menu-item menu-item-type-taxonomy menu-item-object-category\"><a href=\"https://liberties.aljazeera.com/en/category/op-ed/\">Op-ed</a></li>\n<li class=\"menu-item menu-item-type-custom menu-item-object-custom\"><a href=\"/en/publications/\">Publications</a></li>\n<li class=\"menu-item menu-item-type-post_type menu-item-object-page\"><a href=\"https://liberties.aljazeera.com/en/media-library/\">Media Library</a></li>\n</ul> \n\t\t\t\t</nav>\n\t\t\t\t<div class=\"news-letter\">\n\t\t\t\t\t<h5>\n\t\t\t\t\t\tNewsletter\t\t\t\t\t</h5>\n\t\t\t\t\t<div class=\"inputs-group\">\n\t\t\t\t\t\t<input autocomplete=\"off\" type=\"text\" class=\"newsletter-term\"  placeholder=\"Email Address\">\n\t\t\t\t\t\t<button type=\"submit\" class=\"newsletter-button\">\n\t\t\t\t\t\t\t<i class=\"fa fa-long-arrow-left\"></i>\n\t\t\t\t\t\t</button>\n\t\t\t\t\t</div>\n\n\t\t\t\t</div>\n\t\t\t\t<div class=\"latest-publication\">\n\t\t\t\t\t\n<div class='publications-banner'>\n\t\t<figure class=\"figure sidemenu-fig __block\">\n\t\t<a class=\"figure-link\"><img src=\"https://liberties.aljazeera.com/resources/uploads/2021/01/1610568299.jpg\"></a>\n\t\t<!-- 13403 : 350 : 380 -->\n\t\t<figcaption class=\"figure-caption\">\n\t\t\t<div class=\"figure-body\">\n\t\t\t\t<ul class=\"terms-block \">\n\t\t\t\t\t<li>\n\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/publications/\" class=\"taxonomy-block\" style=\"border: 2px solid transparent; background-color:#2d999d\">Publications</a>\n\t\t\t\t\t</li>\n\t\t\t\t</ul>\n\t\t\t\t\n\t\t\t\t<h5 class=\"figure-link\" href=\"https://liberties.aljazeera.com/en/publications/prisoner-345/\">\n\t\t\t\t\tPrisoner 345\t\t\t\t</h5>\n\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t13 Jan, 2021\t</small>\n</div>\n\t\t\t\t\t\t\t\t<form method=\"post\" action=\"https://liberties.aljazeera.com/administration/admin-post.php\">\n\t\t\t\t\t<input type=\"hidden\" name=\"action\" value=\"pdf_download\" />\n\t\t\t\t\t<input name='file_id' value='K3OkBP1bSJsmODg46ASGQcZhDP5Y3TBLiUQe5wYYQVqX/UlXXk7IdgzKtsPIlL7Z7nnsY0ivh6DcnAfYIQqZra/L40EepInQKTY9SQ4xX4/UcRnjyyVqbvmbxLfmgCpz' type='hidden'>\n\t\t\t\t\t<button\n\t\t\t\t\t\t\ttype=\"submit\"\n\t\t\t\t\t\t\tclass=\"theme_button btn-sm\"\n\t\t\t\t\t\t\t><i class=\"fa fa-download\" aria-hidden=\"true\"></i>  Download</button>\n\t\t\t\t</form>\n\t\t\t\t\n\t\t\t</div>\n\t\t</figcaption>\n\t</figure>\n\t</div>\n\n\t\t\t\t</div>\n\t\t\t\t<div class=\"website-ads\">\n\t\t\t\t\t<div class=\"row\"> \n\t\t<div class=\"col-md-12 col-sm-12\">\n\t\t<div class=\"banner-container\">\n\t\t\t<a href=\"https://liberties.aljazeera.com/en/sign-the-petition/\" target=\"_self\">\n\t\t\t\t<img src=\"https://liberties.aljazeera.com/resources/uploads/2025/07/1752671928.png\" />\n\t\t\t</a>\n\t\t</div>\n\t</div>\n\n\t\n</div>\n\t\t\t\t</div>\n\t\t\t\t<!-- end main nav -->\n\t\t\t</header>\n\t\t\t<div class=\"top-header\">\n\t\t\t\t<form action=\"/\">\n\t\t\t\t\t<div class=\"search\">\n\n\t\t\t\t\t\t<input required autocomplete=\"off\" type=\"text\" class=\"search-term\" name=\"s\" placeholder=\"Search for?\" value=''>\n\t\t\t\t\t\t<button type=\"submit\" class=\"search-button\">\n\t\t\t\t\t\t\t<i class=\"fa fa-search\"></i>\n\t\t\t\t\t\t</button>\n\t\t\t\t\t</div>\n\t\t\t\t</form>\n\t\t\t\t<ul class=\"social-list clearfix\">\n\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\t</a> </li>\n\t\t\t\t</ul>\n\t\t\t</div>\n<div id=\"content\" class=\"page-content post\">\n\t\t\t<figure class=\"figure page-title-figure\">\n\t\t\t\t\t\t<div class=\"figure-body position-reset\">\n\t\t\t\t<figcaption class=\"figure-caption\" style=\"position: initial!important;\">\n\t\t\t\t\t<ul class=\"terms-block \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-block\"\n\t\t   style=\"border: 2px solid transparent; background-color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t<h1>Pressing for protection</h1>\n\t\t\t\t</figcaption>\n\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t26 August, 2025\t</small>\n</div>\n\t\t\t\t\t\t\t</div>\n\t\t</figure>\n\t\t\t<div class=\"wrap\">\n\t\t<article id=\"post-25150\" class=\"post-25150 post type-post status-publish format-standard has-post-thumbnail hentry category-press-freedom\">\n\t<style>\n\t.share li {\n\t\tfloat: left;\n\t\t-webkit-transition: all 0.14s ease-in-out;\n\t\t-moz-transition: all 0.14s ease-in-out;\n\t\t-o-transition: all 0.14s ease-in-out;\n\t\ttransition: all 0.14s ease-in-out;\n\t\topacity: 0.5;\n\t}\n\t.share li:hover {\n\t\topacity: 1;\n\t}\n\n\t.sharer li.link a {\n\t\tfont-size: 20px;\n\t}\n\t.sharer li .like_button {\n\t\tpadding: 6px 0 0 0;\n\t}\n\t.sharer li .reblog-icon {\n\t\tpadding: 6px 0 0 7px;\n\t}\n\t.sharer {\n\t\tposition: relative;\n\t}\n\t.sharer .sharer-wrap {\n\t\tposition: absolute;\n\t\ttext-align: center;\n\t\tbottom: 100%;\n\t\twidth: 150px;\n\t\tleft: 50%;\n\t\t-webkit-transform: translate(-50%, 0);\n\t\t-moz-transform: translate(-50%, 0);\n\t\t-o-transform: translate(-50%, 0);\n\t\t-ms-transform: translate(-50%, 0);\n\t\ttransform: translate(-50%, 0);\n\t\tvisibility: hidden;\n\t\topacity: 0;\n\t\t-webkit-transition: all 0.14s ease-in-out;\n\t\t-moz-transition: all 0.14s ease-in-out;\n\t\t-o-transition: all 0.14s ease-in-out;\n\t\ttransition: all 0.14s ease-in-out;\n\t}\n\t.sharer:hover .sharer-wrap {\n\t\tvisibility: visible;\n\t\topacity: 1;\n\t}\n\t.sharer:hover .sharer-wrap ul {\n\t\t-webkit-transform: translate(0, -8px);\n\t\t-moz-transform: translate(0, -8px);\n\t\t-o-transform: translate(0, -8px);\n\t\t-ms-transform: translate(0, -8px);\n\t\ttransform: translate(0, -8px);\n\t}\n\t.sharer ul {\n\t\tposition: relative;\n\t\tdisplay: inline-block;\n\t\tmargin: 0;\n\t\tpadding: 5px 5px;\n\t\tlist-style: none;\n\t\tz-index: 10;\n\t\tbackground: #ffffff;\n\t\tborder: 1px solid #cacbcc;\n\t\tborder-radius: 5px;\n\t\t-webkit-transition: all 0.14s ease-in-out;\n\t\t-moz-transition: all 0.14s ease-in-out;\n\t\t-o-transition: all 0.14s ease-in-out;\n\t\ttransition: all 0.14s ease-in-out;\n\t}\n\t.post-tools .sharer-wrap li {\n\t\tpadding: 0 !important;\n\t}\n\t.post-tools .sharer-wrap li a:hover {\n\t\topacity: 1;\n\t\tcolor: #dba200;\n\t}\n\t.post-tools .sharer-wrap li a {\n\t\topacity: .7;\n\t\tpadding: 5px;\n\t\twidth: 100%;\n\t\tdisplay: block;\n\t\ttext-align: center;\n\t}\n\t.sharer ul:after,\n\t.sharer ul:before {\n\t\ttop: 100%;\n\t\tleft: 50%;\n\t\tborder: solid transparent;\n\t\tcontent: \" \";\n\t\theight: 0;\n\t\twidth: 0;\n\t\tposition: absolute;\n\t\tpointer-events: none;\n\t}\n\t.sharer ul:after {\n\t\tborder-color: rgba(255, 255, 255, 0);\n\t\tborder-top-color: #ffffff;\n\t\tborder-width: 9px;\n\t\tmargin-left: -9px;\n\t}\n\t.sharer ul:before {\n\t\tborder-color: rgba(240, 244, 245, 0);\n\t\tborder-top-color: #cacbcc;\n\t\tborder-width: 11px;\n\t\tmargin-left: -11px;\n\t}\n\t.sharer ul li a {\n\t\twidth: 32px;\n\t\theight: 35px;\n\t\tpadding-top: 9px;\n\t}\n\t.sharer ul li a.social-link {\n\n\t\tline-height: normal;\n\t}\n\n\t.post-tools ul li i.fa {\n\t\tfont-size: 12px;\n\t}\n</style>\n<div class=\"post-tools\">\n\t<ul>\n\t\t\n\t\t\n\n\n\t\t<li><a href=\"mailto:?subject=Please see this article&amp;body=Check out this site https%3Ahttps://liberties.aljazeera.com/en/pressing-for-protection/\" class=\"send-to-email\"><i class=\"fa fa-envelope\" aria-hidden=\"true\"></i></a></li>\n\t\t<li><a href=\"javascript:void(0)\" class=\"print-page\"><i class=\"fa fa-print\" aria-hidden=\"true\"></i></a></li>\n\t\t<!-- <li><i class=\"fa fa-ellipsis-v\" aria-hidden=\"true\"></i></li> -->\n\t\t<li><a href=\"javascript:void(0)\" class=\"increase-page-font-size\"><i class=\"fa fa-font _plus\"></i></a></li>\n\t\t<li><a href=\"javascript:void(0)\" class=\"decrease-page-font-size\"><i class=\"fa fa-font _minus\"></i></a></li>\n\t\t<li>\n\t\t\t<div class=\"sharer\">\n\t\t\t\t<a class=\"social-export\"><i class=\"fa fa-share\" aria-hidden=\"true\"></i></a>\n\t\t\t\t<div class=\"sharer-wrap\">\n\t\t\t\t\t<ul>\n\t\t\t\t\t\t<li class=\"twitter\">\n\t\t\t\t\t\t\t<a href=\"https://twitter.com/intent/tweet?url=https%3A%2F%2Fliberties.aljazeera.com%2Fen%2Fpressing-for-protection%2F\"\n\t\t\t\t\t\t\t   title=\"Share on Twitter\"\n\t\t\t\t\t\t\t   class=\"social-link\"\n\t\t\t\t\t\t\t   target=\"_blank\"><i class=\"fa fa-twitter\"></i>\n\t\t\t\t\t\t\t</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t<li class=\"facebook\">\n\t\t\t\t\t\t\t<a href=\"https://www.facebook.com/sharer.php?u=https%3A%2F%2Fliberties.aljazeera.com%2Fen%2Fpressing-for-protection%2F\"\n\t\t\t\t\t\t\t   title=\"Share on Facebook\"\n\t\t\t\t\t\t\t   class=\"social-link\"\n\t\t\t\t\t\t\t   target=\"_blank\"><i class=\"fa fa-facebook\"></i>\n\t\t\t\t\t\t\t</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t\t<li class=\"gplus\">\n\t\t\t\t\t\t\t<a href=\"https://plus.google.com/share?url=https%3A%2F%2Fliberties.aljazeera.com%2Fen%2Fpressing-for-protection%2F\"\n\t\t\t\t\t\t\t   title=\"Share on Google +\"\n\t\t\t\t\t\t\t   class=\"social-link\"\n\t\t\t\t\t\t\t   target=\"_blank\"><i class=\"fa fa-google-plus\"></i>\n\t\t\t\t\t\t\t</a>\n\t\t\t\t\t\t</li>\n\t\t\t\t\t</ul>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t</li>\n\t</ul>\n</div>\n<style>\n\t@media print {\n\t\t.related-posts-sidebar, .post-tools \n\t\t{\n\t\t\tdisplay: none;\n\t\t}\n\t\t.fa-font._minus::before {\n\t\t\tfont-size: .7em;\n\t\t}\n\t}\n</style>\n\n<script>\n\twindow.onload = function() {\n\t\tif (window.jQuery) { \n\t\t\tjQuery('ready').ready(function($){\n\n\t\t\t\t$('.increase-page-font-size').click(function(){\n\n\t\t\t\t\t$('article .article-content').find('p,h1,h2,h3,h4,h5,h6').each(function () {\n\t\t\t\t\t\tvar fontSize = parseInt($(this).css(\"font-size\"));\n\n\t\t\t\t\t\tfontSize = fontSize + 1 + 'px';\n\t\t\t\t\t\t$(this).css({'font-size':fontSize});\n\t\t\t\t\t});\n\n\t\t\t\t});\n\n\t\t\t\t$('.decrease-page-font-size').click(function(){\n\n\t\t\t\t\t$('article .article-content').find('p,h1,h2,h3,h4,h5,h6').each(function () {\n\t\t\t\t\t\tvar fontSize = parseInt($(this).css(\"font-size\"));\n\n\t\t\t\t\t\tfontSize = fontSize - 1 + 'px';\n\t\t\t\t\t\t$(this).css({'font-size':fontSize});\n\t\t\t\t\t});\n\n\t\t\t\t});\n\n\t\t\t\t$('.print-page').click(function(){\n\n\t\t\t\t\tvar mywindow = window.open(\" \", 'PRINT', 'height=400,width=600');\n\t\t\t\t\tmywindow.document.open();\n\t\t\t\t\tmywindow.document.write('<html><head><title>' + document.title  + '</title></head>');\n\t\t\t\t\tmywindow.document.write('<h1>' + document.title  + '</h1>');\n\t\t\t\t\tmywindow.document.write( $('article.hentry .article-content').html());\n\t\t\t\t\tmywindow.document.write('</html>');\n\t\t\t\t\tmywindow.document.close();\n\t\t\t\t\tmywindow.focus();\n\t\t\t\t\tmywindow.print();\n\t\t\t\t\tmywindow.close();\n\n\t\t\t\t});\n\n\n\t\t\t});\n\t\t}\n\t}\n\n</script>\n<div class=\"article-content\">\n\t<div class=\"main-image\">\n\t<img src=\"https://liberties.aljazeera.com/resources/uploads/2025/08/1756212916.webp\" alt=\"\" />\n\t</div>\n<section>\n\t<div class=\"row\">\n\t\t<div class=\"col-sm-12\">\n\t\t\t<p><p data-start=\"94\" data-end=\"521\">This week, the International Federation of Journalists, in coordination with Britain’s National Union of Journalists (NUJ), launched a 48-hour campaign of solidarity with Palestinian journalists in Gaza.</p>\n<p data-start=\"94\" data-end=\"521\">The initiative, which began on Monday, seeks to draw attention to the growing toll of media workers killed in the enclave and to call for stronger protections for journalists in conflict zones.</p>\n<p data-start=\"523\" data-end=\"980\" data-is-last-node=\"\" data-is-only-node=\"\">The campaign includes demands to end impunity for those targeting reporters and to guarantee safe access for journalists operating in war-torn areas. On Wednesday, a vigil will be held outside Downing Street, organised by the NUJ, with speeches from union leaders and foreign correspondents.</p>\n<p data-start=\"523\" data-end=\"980\" data-is-last-node=\"\" data-is-only-node=\"\">Among them is Wael Al-Dahdouh, Al Jazeera’s bureau chief in Gaza, who has become a prominent voice amid the conflict. The broadcaster is expected to cover the event.</p>\n</p>\n\t\t</div>\n\t</div>\n</section>\n</div>\t\t<div class=\"related-posts-sidebar\">\n\t\t\t<h4>Related News</h4>\n\t\t\t<ul>\n\t\t\t\t\t\t\t\t<li>\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/al-jazeera-forum-navigating-the-complexities-of-human-rights-accountability-international-law/\">\n\t\t\t\t\t\t<date>8 February, 2026</date>\n\t\t\t\t\t\t<h5>Al Jazeera Forum: Navigating the Complexities of Human Rights, Accountability &amp; International Law</h5>\n\t\t\t\t\t</a>\n\t\t\t\t</li>\n\t\t\t\t\t\t\t\t<li>\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/israel-media-and-the-curtailment-of-press-freedoms/\">\n\t\t\t\t\t\t<date>28 January, 2026</date>\n\t\t\t\t\t\t<h5>Israel, Media, and the Curtailment of Press Freedoms</h5>\n\t\t\t\t\t</a>\n\t\t\t\t</li>\n\t\t\t\t\t\t\t\t<li>\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/occupied-west-bank-press-freedom-under-law-al-jazeera-at-risk/\">\n\t\t\t\t\t\t<date>27 January, 2026</date>\n\t\t\t\t\t\t<h5>Occupied West Bank, Press Freedom Under Law, Al Jazeera at Risk</h5>\n\t\t\t\t\t</a>\n\t\t\t\t</li>\n\t\t\t\t\t\t\t</ul>\n\t\t</div>\n</article><div class=\"related-posts-blocks\">\n\t<div class=\"row no-gutters\">\n\t\t\t\t<div class=\"col-md-3\">\n\t\t\t<a href=\"https://liberties.aljazeera.com/en/al-jazeera-on-ending-impunity-for-crimes-against-journalists/\">\n\t\t\t\t<div class=\"card\">      \n\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/11/1762186816.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/al-jazeera-on-ending-impunity-for-crimes-against-journalists/\"><h5 class=\"card-title\">Al Jazeera on Ending Impunity for Crimes Against Journalists</h5></a>\n\t\t\t\t\t\t<p>Gaza illustrates the danger with grim clarity. Since 2023, at least 252 journalists have been killed there, a toll that makes it, by far, the most lethal place on earth for the press. Yet the...</p>\n\t\t\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t3 November, 2025\t</small>\n</div>\n\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</a>\n\t\t</div>\n\t\t\t\t<div class=\"col-md-3\">\n\t\t\t<a href=\"https://liberties.aljazeera.com/en/why-murdering-journalists-still-goes-unpunished/\">\n\t\t\t\t<div class=\"card\">      \n\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2022/06/1654759633.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/why-murdering-journalists-still-goes-unpunished/\"><h5 class=\"card-title\">Why Murdering Journalists Still Goes Unpunished?</h5></a>\n\t\t\t\t\t\t<p>To track these grim statistics, UNESCO maintains its Observatory of Killed Journalists, a public database documenting every known case since 1993. It records not only names and dates,...</p>\n\t\t\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t2 November, 2025\t</small>\n</div>\n\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</a>\n\t\t</div>\n\t\t\t\t<div class=\"col-md-3\">\n\t\t\t<a href=\"https://liberties.aljazeera.com/en/ajmn-ipi-call-for-a-renewed-fight-for-free-media/\">\n\t\t\t\t<div class=\"card\">      \n\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/10/1761819610.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/ajmn-ipi-call-for-a-renewed-fight-for-free-media/\"><h5 class=\"card-title\">AJMN &amp; IPI Call for a Renewed Fight for Free Media</h5></a>\n\t\t\t\t\t\t<p>Before closing the Congress, Al Jazeera Media Network Delegation presented a commemorative shield to the International Press Institute, represented by its Executive Director, Scott Griffen, in...</p>\n\t\t\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t30 October, 2025\t</small>\n</div>\n\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</a>\n\t\t</div>\n\t\t\t\t<div class=\"col-md-3\">\n\t\t\t<a href=\"https://liberties.aljazeera.com/en/bearing-witness-in-gaza/\">\n\t\t\t\t<div class=\"card\">      \n\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2018/11/GettyImages-949558570.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/bearing-witness-in-gaza/\"><h5 class=\"card-title\">Bearing Witness in Gaza</h5></a>\n\t\t\t\t\t\t<p>By the end of the session, one message had crystallized. In Gaza, the truth itself is under siege, and those who strive to tell it are fighting not only for their profession, but for the...</p>\n\t\t\t\t\t\t<div class=\"published-note \">\n\t<small>\n\t\t\t\t\t\t28 October, 2025\t</small>\n</div>\n\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</a>\n\t\t</div>\n\t\t\t</div>\n</div>\n<script>\n\tjQuery(document).ready(function ($) {\n\t\t$(\"#ad-posts-tabs\").on(\"click\", \"li\", function () {\n\t\t\tvar $this = $(this);\n\t\t\tif($this.hasClass('currenttab')) {return}\n\t\t\t$(\"#ad-posts-tabs\").find(\"li\").filter(\".currenttab\").removeClass(\"currenttab\");\n\t\t\t$this.addClass(\"currenttab\");\n\t\t\tvar tab_num = $this.attr(\"data-tab-num\");\n\t\t\tshow_tab(tab_num);\n\t\t});\n\t\tfunction show_tab(tab_num) {\n\t\t\tvar tabcontents = $(\".ptc\");\n\t\t\tvar count = 0;\n\t\t\ttabcontents.fadeOut(300, function () {\n\t\t\t\tif (++count === tabcontents.length) {\n\t\t\t\t\t$(\"#ptc\" + tab_num).fadeIn(300).addClass('opened').removeClass('closed');\n\t\t\t\t}\n\t\t\t}).addClass('closed').removeClass('opened');\n\t\t}\n\t});\n</script>\n<div class=\"most-populat-posts-blocks\">\n\n\t<div class=\"ad-posts-tabs\">\n\t\t<ul id=\"ad-posts-tabs\">\n\t\t\t<li id=\"tab0\"  data-tab-num=\"0\" class=\"currenttab\"><span>Most Viewed</span></li>\n\t\t\t<li id=\"tab1\"  data-tab-num=\"1\"><span>Most Popular</span></li>\n\n\t\t</ul>\n\t</div>\n\n\t<div class=\"ad-posts-tabs-contents\">\n\t\t<div id=\"ptc0\" class=\"ptc active\">\n\t\t\t\t\t\t<div class=\"row no-gutters\">\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/i-was-taken-to-an-open-field-police-brutality-in-south-africa/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2021/03/1617086861.jpeg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/long-read/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3aa581\"\n\t\t   >Long Read\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/i-was-taken-to-an-open-field-police-brutality-in-south-africa/\"><h5 class=\"card-title\">&#8216;I was taken to an open field&#8217;: Police brutality in South Africa</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/will-covid-19-vaccines-divide-rich-and-poor-nations/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2021/05/1621860349.png\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/videograph/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#ff6363\"\n\t\t   >Videograph\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/will-covid-19-vaccines-divide-rich-and-poor-nations/\"><h5 class=\"card-title\">Will COVID-19 vaccines divide rich and poor nations?</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/world-hunger/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2020/12/1607526862.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/videograph/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#ff6363\"\n\t\t   >Videograph\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/world-hunger/\"><h5 class=\"card-title\">World Hunger</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/why-has-spain-released-catalan-separatist-leaders-from-jail/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2021/06/1624521954.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/courts-and-justice/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#d1b440\"\n\t\t   >Courts and Justice\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/videograph/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#ff6363\"\n\t\t   >Videograph\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/why-has-spain-released-catalan-separatist-leaders-from-jail/\"><h5 class=\"card-title\">Why has Spain released Catalan separatist leaders from jail?</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/is-it-too-late-to-save-our-planet/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/climate-environment/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#1e73be\"\n\t\t   >Climate &amp; Environment\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/videograph/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#ff6363\"\n\t\t   >Videograph\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/is-it-too-late-to-save-our-planet/\"><h5 class=\"card-title\">Is it too late to save our planet?</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/a-un-report-set-out-a-four-point-plan-of-action-to-tackle-systemic-racism/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2021/05/1620045222-scaled.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/video-reports/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#b08e6a\"\n\t\t   >Reports\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/videograph/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#ff6363\"\n\t\t   >Videograph\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/a-un-report-set-out-a-four-point-plan-of-action-to-tackle-systemic-racism/\"><h5 class=\"card-title\">A UN report set out a four-point plan of action to tackle systemic racism</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/arab-naksa/\">\n\t\t\t\t\t\t<div class=\"card mv\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2023/04/1681116267.webp\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/armed-conflict/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#d8b91e\"\n\t\t   >Armed Conflict\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/arab-naksa/\"><h5 class=\"card-title\">Arab “Naksa”</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>\n\t\t<div id=\"ptc1\" class=\"ptc\"> \n\t\t\t\t\t\t<div class=\"row no-gutters\">\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/doha-international-conference-concludes-with-declaration-on-journalist-protection/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/10/1760023156.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/events/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3980bf\"\n\t\t   >Events\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/doha-international-conference-concludes-with-declaration-on-journalist-protection/\"><h5 class=\"card-title\">Doha International Conference Concludes with Declaration on Journalist Protection</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/doha-hosts-the-international-conference-on-protecting-journalists-in-armed-conflicts/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/10/1759932907.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/events/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3980bf\"\n\t\t   >Events\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/doha-hosts-the-international-conference-on-protecting-journalists-in-armed-conflicts/\"><h5 class=\"card-title\">Doha Hosts the International Conference on Protecting Journalists in Armed Conflicts</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/russias-repression-deepens-dissent-torture-and-legal-abuse/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/09/1758632037.webp\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/russias-repression-deepens-dissent-torture-and-legal-abuse/\"><h5 class=\"card-title\">Russia’s Repression Deepens</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/israel-murders-journalists/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/09/1758452960.png\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/israel-murders-journalists/\"><h5 class=\"card-title\">Israel Murders Journalists</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/spying-on-reporters/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2025/09/1758189933.png\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/spying-on-reporters/\"><h5 class=\"card-title\">Spying On Reporters</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t\t<div class=\"col-md-2\">\n\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/netanyahus-regret-and-the-rally-for-captive/\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<img class=\"card-img-top\" src=\"https://liberties.aljazeera.com/resources/uploads/2022/06/1654759633.jpg\" alt=\"Card image cap\">\n\t\t\t\t\t\t\t<div class=\"card-body\">\n\t\t\t\t\t\t\t\t<ul class=\"terms-plain \">\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/armed-conflict/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#d8b91e\"\n\t\t   >Armed Conflict\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/humanitarian-crisis/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#c63163\"\n\t\t   >Humanitarian Crisis\t\t</a>\n\t</li>\n\t\t<li>\n\t\t<a href=\"https://liberties.aljazeera.com/en/category/press-freedom/\"\n\t\t   class=\"taxonomy-plain\"\n\t\t   style=\"border: 2px solid transparent; color:#3392a5\"\n\t\t   >Press Freedom\t\t</a>\n\t</li>\n\t</ul>\n\t\t\t\t\t\t\t\t<a href=\"https://liberties.aljazeera.com/en/netanyahus-regret-and-the-rally-for-captive/\"><h5 class=\"card-title\">Netanyahu’s Regret and the Rally for Captive</h5></a>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>\n\t</div>\n</div>\n\t</div>\n\t<div id=\"ajmnfooter\">\n\t\t\t<div class=\"wrap footer-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t\t\t\t<h3>Who We Are</h3>\n\t\t\t\t\t\t\t\t\t<div class=\"list\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://terms.aljazeera.net/\">Terms and Conditions</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://privacy.aljazeera.net/\">Privacy Policy</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://privacy.aljazeera.net/cookie/\">Cookies Policy</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://careers.aljazeera.net/\">Work for us</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t\t\t\t<h3>Our Network</h3>\n\t\t\t\t\t\t\t\t\t<div class=\"list\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://studies.aljazeera.net/en/\">Al Jazeera Center for Studies</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://forum.aljazeera.net/en/\">Al Jazeera Forum</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://institute.aljazeera.net/en/\">Al Jazeera Media Institute</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://learning.aljazeera.net/en\">Learn Arabic</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://hotels.aljazeera.net/\">Al Jazeera Hotel Partners</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t\t\t\t<h3>Our Channels</h3>\n\t\t\t\t\t\t\t\t\t<div class=\"list\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.aljazeera.net/\">Al Jazeera Arabic</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.aljazeera.com/\">Al Jazeera English</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://balkans.aljazeera.net/\">Al Jazeera Balkans</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://mubasher.aljazeera.net/\">Al Jazeera Mubasher</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://doc.aljazeera.net/\">Al Jazeera Documentary</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t\t\t\t<h3>&nbsp;</h3>\n\t\t\t\t\t\t\t\t\t<div class=\"list\">\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.ajplus.net/english/\">AJ+</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.ajplus.net/arabi/\">AJ+ Arabi</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.ajplus.net/espanol/\">AJ+ Español</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div><a target=\"_blank\" href=\"https://www.ajplus.net/francais/\">AJ+ French</a></div>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t<div class=\"column identity\">\n\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t<div class=\"ajmn-footer-logo\">\n\t\t\t\t\t\t\t\t<a href=\"//network.aljazeera.net/\" target=\"_blank\"><img src='data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDIzLjAuMSwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAxNjQgOTUiIHN0eWxlPSJlbmFibGUtYmFja2dyb3VuZDpuZXcgMCAwIDE2NCA5NTsiIHhtbDpzcGFjZT0icHJlc2VydmUiPgo8c3R5bGUgdHlwZT0idGV4dC9jc3MiPgoJLnN0MHtmaWxsOiNGRkZGRkY7fQo8L3N0eWxlPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMzMuMyw4Ni4yM3YtMi4wNWgtNS40OXYxLjc2aDIuODJsLTIuOTEsNC4yMXYyLjA1aDUuNjR2LTEuNzdIMzAuNEwzMy4zLDg2LjIzeiBNNTIuNjMsODcuMgoJYy0wLjEyLDAuMTQtMC4yOCwwLjIxLTAuNjcsMC4yNWgtMC43OXYtMS41MWgwLjYxYzAuMDUsMCwwLjEsMC4wMSwwLjE0LDAuMDFjMC4zMSwwLjAxLDAuNDQsMC4wNSwwLjU4LDAuMTMKCUM1Mi44NSw4Ni4yOSw1Mi45Myw4Ni44NCw1Mi42Myw4Ny4yIE01NC4zNCw4OS4zYy0wLjMtMC43MS0wLjQxLTAuODYtMC42OS0wLjk5YzAuMDUtMC4wMSwwLjA5LTAuMDMsMC4xNC0wLjA2CgljMC44OS0wLjQxLDEuMzItMS40NSwwLjk4LTIuNmMtMC4yNy0wLjk1LTEtMS40Ny0yLjM3LTEuNDdoLTMuMjJ2OC4wMmgyLjA0di0zaDAuNDdjMC4zMywwLDAuNTMsMC4xNSwwLjcsMC41N2wwLjExLDAuMjVsMC4wNiwwLjE0CglsMC43NywyLjAzaDIuMTJsLTAuOTktMi42M0M1NC40MSw4OS40OCw1NC4zOSw4OS4zOSw1NC4zNCw4OS4zIE01OS4xMSw4OC45MWwwLjc1LTIuNTVsMC43NiwyLjU1SDU5LjExeiBNNjEsODQuMThoLTIuMjYKCWwtMi43Miw4LjAyaDIuMDVsMC40Ni0xLjQ3aDIuNjJsMC40NCwxLjQ3aDIuMTdMNjEsODQuMTh6IE0yMS43Niw4OC45MWwwLjc1LTIuNTVsMC43NiwyLjU1SDIxLjc2eiBNMjEuMzksODQuMThsLTIuNzEsOC4wMmgyLjA1CglsMC40Ni0xLjQ3aDIuNjJsMC40NSwxLjQ3aDIuMTdsLTIuNzctOC4wMkgyMS4zOXogTTMuMDgsODguOTFsMC43NS0yLjU1bDAuNzUsMi41NUgzLjA4eiBNMi43MSw4NC4xOEwwLDkyLjIxaDIuMDVsMC40Ni0xLjQ3aDIuNjIKCWwwLjQ0LDEuNDdoMi4xN2wtMi43Ny04LjAySDIuNzF6IE00NC4xOCw4OS4xMmgyLjY2Vjg3LjRoLTIuNjZ2LTEuNDZoMy4xdi0xLjc2aC01LjEzdjguMDJoNS40MVY5MC41aC0zLjM3Vjg5LjEyeiBNMzcuMTMsODkuMTIKCWgyLjY3Vjg3LjRoLTIuNjd2LTEuNDZoMy4xdi0xLjc2SDM1LjF2OC4wMmg1LjRWOTAuNWgtMy4zN1Y4OS4xMnogTTE1LjQyLDkxLjdjMCwxLjIzLTAuNDQsMS42Ny0xLjQyLDEuMzkKCWMtMC4wNi0wLjAxLTAuMTEtMC4wMy0wLjE2LTAuMDZsLTAuNDgsMS43NGMwLjExLDAuMDUsMC4yMiwwLjEsMC4zMywwLjE0YzIuMjgsMC44NiwzLjc4LTAuNDIsMy43OC0yLjY1di04LjA5aC0yLjA0VjkxLjd6CgkgTTEzLjYsOTAuNDJIMTEuMXYtNi4yM0g5LjA0djguMDJoNC41NlY5MC40MnoiLz4KPHBvbHlnb24gY2xhc3M9InN0MCIgcG9pbnRzPSI2OS45OSw4NC4xOCA3MS44NSw4OS43IDcxLjg3LDg5LjcgNzMuNjMsODQuMTggNzYuMDksODQuMTggNzYuMDksOTIuMjEgNzQuNDYsOTIuMjEgNzQuNDYsODYuNTIgCgk3NC40Myw4Ni41MiA3Mi40OCw5Mi4yMSA3MS4xMyw5Mi4yMSA2OS4xOCw4Ni41OCA2OS4xNiw4Ni41OCA2OS4xNiw5Mi4yMSA2Ny41Miw5Mi4yMSA2Ny41Miw4NC4xOCAiLz4KPHBvbHlnb24gY2xhc3M9InN0MCIgcG9pbnRzPSI4My41OCw4NC4xOCA4My41OCw4NS42NyA3OS4zOCw4NS42NyA3OS4zOCw4Ny4zOSA4My4yNCw4Ny4zOSA4My4yNCw4OC43NiA3OS4zOCw4OC43NiA3OS4zOCw5MC43MiAKCTgzLjY3LDkwLjcyIDgzLjY3LDkyLjIxIDc3LjYzLDkyLjIxIDc3LjYzLDg0LjE4ICIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNODguMTYsOTAuNzJjMC4yNSwwLDAuNS0wLjA0LDAuNzQtMC4xMmMwLjI0LTAuMDgsMC40NS0wLjIyLDAuNjMtMC40MWMwLjE5LTAuMTksMC4zMy0wLjQ0LDAuNDUtMC43NQoJYzAuMTEtMC4zMSwwLjE3LTAuNjgsMC4xNy0xLjEyYzAtMC40LTAuMDQtMC43Ny0wLjEyLTEuMDljLTAuMDgtMC4zMy0wLjIxLTAuNi0wLjM4LTAuODRjLTAuMTgtMC4yMy0wLjQxLTAuNDEtMC43MS0wLjUzCgljLTAuMjktMC4xMi0wLjY2LTAuMTktMS4wOS0wLjE5SDg2LjZ2NS4wNUg4OC4xNnogTTg4LjI5LDg0LjE4YzAuNTEsMCwwLjk5LDAuMDgsMS40MywwLjI1YzAuNDQsMC4xNywwLjgzLDAuNDEsMS4xNSwwLjc0CgljMC4zMiwwLjMzLDAuNTgsMC43NCwwLjc2LDEuMjRjMC4xOCwwLjQ5LDAuMjcsMS4wNywwLjI3LDEuNzRjMCwwLjU4LTAuMDcsMS4xMi0wLjIyLDEuNjJjLTAuMTUsMC40OS0wLjM3LDAuOTItMC42NywxLjI4CgljLTAuMywwLjM2LTAuNjgsMC42NC0xLjEzLDAuODVjLTAuNDUsMC4yMS0wLjk4LDAuMzEtMS41OSwwLjMxaC0zLjQzdi04LjAySDg4LjI5eiIvPgo8cmVjdCB4PSI5My4xMSIgeT0iODQuMTkiIGNsYXNzPSJzdDAiIHdpZHRoPSIxLjc1IiBoZWlnaHQ9IjguMDIiLz4KPHBhdGggY2xhc3M9InN0MCIgZD0iTTEwMC40Nyw4OS4xMWwtMS0yLjk0aC0wLjAybC0xLjA0LDIuOTRIMTAwLjQ3eiBNMTAwLjM3LDg0LjE4bDIuOTgsOC4wMmgtMS44MmwtMC42LTEuNzloLTIuOThsLTAuNjIsMS43OQoJaC0xLjc2bDMuMDEtOC4wMkgxMDAuMzd6Ii8+Cjxwb2x5Z29uIGNsYXNzPSJzdDAiIHBvaW50cz0iMTA4Ljg3LDg0LjE4IDExMi4xOSw4OS41NyAxMTIuMjEsODkuNTcgMTEyLjIxLDg0LjE4IDExMy44NSw4NC4xOCAxMTMuODUsOTIuMjEgMTEyLjEsOTIuMjEgCgkxMDguNzksODYuODQgMTA4Ljc3LDg2Ljg0IDEwOC43Nyw5Mi4yMSAxMDcuMTMsOTIuMjEgMTA3LjEzLDg0LjE4ICIvPgo8cG9seWdvbiBjbGFzcz0ic3QwIiBwb2ludHM9IjEyMS4zNCw4NC4xOCAxMjEuMzQsODUuNjcgMTE3LjE0LDg1LjY3IDExNy4xNCw4Ny4zOSAxMjAuOTksODcuMzkgMTIwLjk5LDg4Ljc2IDExNy4xNCw4OC43NiAKCTExNy4xNCw5MC43MiAxMjEuNDMsOTAuNzIgMTIxLjQzLDkyLjIxIDExNS4zOSw5Mi4yMSAxMTUuMzksODQuMTggIi8+Cjxwb2x5Z29uIGNsYXNzPSJzdDAiIHBvaW50cz0iMTIxLjk5LDg1LjY3IDEyMS45OSw4NC4xOCAxMjguNTEsODQuMTggMTI4LjUxLDg1LjY3IDEyNi4xMiw4NS42NyAxMjYuMTIsOTIuMjEgMTI0LjM3LDkyLjIxIAoJMTI0LjM3LDg1LjY3ICIvPgo8cG9seWdvbiBjbGFzcz0ic3QwIiBwb2ludHM9IjEzNS4yNiw5Mi4yMSAxMzMuOTEsODYuNzUgMTMzLjg5LDg2Ljc1IDEzMi41Niw5Mi4yMSAxMzAuNzksOTIuMjEgMTI4LjY4LDg0LjE4IDEzMC40Myw4NC4xOCAKCTEzMS42OSw4OS42NCAxMzEuNzEsODkuNjQgMTMzLjEsODQuMTggMTM0LjczLDg0LjE4IDEzNi4wOSw4OS43MSAxMzYuMTIsODkuNzEgMTM3LjQyLDg0LjE4IDEzOS4xNCw4NC4xOCAxMzcsOTIuMjEgIi8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik0xNDEuNDYsODkuMjFjMC4wOCwwLjMyLDAuMiwwLjYsMC4zNywwLjg2YzAuMTcsMC4yNSwwLjM5LDAuNDYsMC42NywwLjYxYzAuMjgsMC4xNSwwLjYxLDAuMjMsMSwwLjIzCgljMC4zOSwwLDAuNzMtMC4wOCwxLTAuMjNjMC4yNy0wLjE1LDAuNS0wLjM2LDAuNjctMC42MWMwLjE3LTAuMjUsMC4zLTAuNTQsMC4zNy0wLjg2YzAuMDgtMC4zMiwwLjEyLTAuNjUsMC4xMi0wLjk4CgljMC0wLjM1LTAuMDQtMC42OS0wLjEyLTEuMDJjLTAuMDgtMC4zMy0wLjItMC42Mi0wLjM3LTAuODhjLTAuMTctMC4yNi0wLjM5LTAuNDYtMC42Ny0wLjYyYy0wLjI3LTAuMTUtMC42MS0wLjIzLTEtMC4yMwoJYy0wLjM5LDAtMC43MywwLjA4LTEsMC4yM2MtMC4yNywwLjE1LTAuNSwwLjM2LTAuNjcsMC42MmMtMC4xNywwLjI2LTAuMjksMC41NS0wLjM3LDAuODhjLTAuMDgsMC4zMy0wLjEyLDAuNjctMC4xMiwxLjAyCglDMTQxLjM0LDg4LjU3LDE0MS4zOCw4OC44OSwxNDEuNDYsODkuMjEgTTEzOS44Niw4Ni41NmMwLjE4LTAuNTEsMC40My0wLjk2LDAuNzctMS4zNGMwLjMzLTAuMzgsMC43NC0wLjY4LDEuMjMtMC45CgljMC40OS0wLjIyLDEuMDMtMC4zMywxLjY0LTAuMzNjMC42MiwwLDEuMTcsMC4xMSwxLjY1LDAuMzNjMC40OCwwLjIyLDAuODksMC41MiwxLjIzLDAuOWMwLjMzLDAuMzgsMC41OSwwLjgzLDAuNzcsMS4zNAoJYzAuMTgsMC41MSwwLjI3LDEuMDcsMC4yNywxLjY3YzAsMC41OC0wLjA5LDEuMTMtMC4yNywxLjYzYy0wLjE4LDAuNTEtMC40NCwwLjk1LTAuNzcsMS4zMmMtMC4zMywwLjM3LTAuNzQsMC42Ny0xLjIzLDAuODgKCWMtMC40OCwwLjIxLTEuMDMsMC4zMi0xLjY1LDAuMzJjLTAuNjEsMC0xLjE2LTAuMTEtMS42NC0wLjMyYy0wLjQ5LTAuMjEtMC45LTAuNTEtMS4yMy0wLjg4Yy0wLjMzLTAuMzctMC41OS0wLjgxLTAuNzctMS4zMgoJYy0wLjE4LTAuNTEtMC4yNy0xLjA1LTAuMjctMS42M0MxMzkuNTksODcuNjMsMTM5LjY4LDg3LjA3LDEzOS44Niw4Ni41NiIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMTUyLjI4LDg3LjgxYzAuNCwwLDAuNy0wLjA5LDAuOS0wLjI3YzAuMi0wLjE4LDAuMy0wLjQ3LDAuMy0wLjg4YzAtMC4zOS0wLjEtMC42Ny0wLjMtMC44NQoJYy0wLjItMC4xOC0wLjUtMC4yNi0wLjktMC4yNmgtMS45MnYyLjI2SDE1Mi4yOHogTTE1Mi45LDg0LjE4YzAuMzYsMCwwLjY4LDAuMDYsMC45NiwwLjE3YzAuMjksMC4xMiwwLjUzLDAuMjgsMC43NCwwLjQ4CgljMC4yLDAuMiwwLjM2LDAuNDQsMC40NywwLjdjMC4xMSwwLjI3LDAuMTYsMC41NSwwLjE2LDAuODZjMCwwLjQ3LTAuMSwwLjg4LTAuMywxLjIyYy0wLjIsMC4zNS0wLjUyLDAuNjEtMC45NiwwLjc5djAuMDIKCWMwLjIyLDAuMDYsMC4zOSwwLjE1LDAuNTMsMC4yN2MwLjE0LDAuMTIsMC4yNiwwLjI3LDAuMzUsMC40NGMwLjA5LDAuMTcsMC4xNSwwLjM1LDAuMiwwLjU2YzAuMDQsMC4yLDAuMDcsMC40LDAuMDgsMC42MQoJYzAuMDEsMC4xMywwLjAyLDAuMjgsMC4wMiwwLjQ1YzAuMDEsMC4xNywwLjAyLDAuMzUsMC4wNCwwLjUzYzAuMDIsMC4xOCwwLjA1LDAuMzUsMC4wOSwwLjUxYzAuMDQsMC4xNiwwLjEsMC4zLDAuMTgsMC40MWgtMS43NQoJYy0wLjEtMC4yNS0wLjE2LTAuNTYtMC4xOC0wLjkxYy0wLjAyLTAuMzUtMC4wNi0wLjY5LTAuMS0xLjAxYy0wLjA2LTAuNDItMC4xOS0wLjczLTAuMzgtMC45MmMtMC4xOS0wLjE5LTAuNTEtMC4yOS0wLjk1LTAuMjkKCWgtMS43NXYzLjEzaC0xLjc1di04LjAySDE1Mi45eiIvPgo8cG9seWdvbiBjbGFzcz0ic3QwIiBwb2ludHM9IjE1OC40MSw4NC4xOCAxNTguNDEsODcuNTEgMTYxLjUxLDg0LjE4IDE2My43LDg0LjE4IDE2MC41OSw4Ny4zNSAxNjQsOTIuMjEgMTYxLjgsOTIuMjEgMTU5LjQxLDg4LjYgCgkxNTguNDEsODkuNjIgMTU4LjQxLDkyLjIxIDE1Ni42Niw5Mi4yMSAxNTYuNjYsODQuMTggIi8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik0yNC4xNyw3MS41NmMwLTAuMjUsMC4wOS0wLjQ2LDAuMjYtMC42NGMwLjE3LTAuMTgsMC4zOS0wLjI2LDAuNjMtMC4yNmMwLjI0LDAsMC40NCwwLjA5LDAuNjEsMC4yNgoJYzAuMTcsMC4xOCwwLjI1LDAuMzksMC4yNSwwLjY0YzAsMC4yNC0wLjA4LDAuNDUtMC4yNSwwLjYyYy0wLjE3LDAuMTctMC4zNywwLjI1LTAuNjEsMC4yNWMtMC4yNSwwLTAuNDYtMC4wOC0wLjYzLTAuMjUKCUMyNC4yNSw3Mi4wMSwyNC4xNyw3MS44LDI0LjE3LDcxLjU2IE0yMi4zMSw3NS44NnYwLjM3YzAsMC4yMywwLjA3LDAuNCwwLjIsMC41MmMwLjEzLDAuMTIsMC4zNSwwLjE4LDAuNjQsMC4xOGgxLjM0Vjc0LjYKCWMtMC4zMywwLjA2LTAuNjIsMC4xNC0wLjg5LDAuMjNjLTAuMjcsMC4wOS0wLjQ5LDAuMi0wLjY4LDAuM2MtMC4xOSwwLjExLTAuMzMsMC4yMy0wLjQ0LDAuMzVDMjIuMzcsNzUuNjEsMjIuMzEsNzUuNzQsMjIuMzEsNzUuODYKCSBNMjEuODYsNzEuNTZjMC0wLjI1LDAuMDktMC40NiwwLjI2LTAuNjRjMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjZjMC4yNCwwLDAuNDQsMC4wOSwwLjYxLDAuMjZjMC4xNywwLjE4LDAuMjUsMC4zOSwwLjI1LDAuNjQKCWMwLDAuMjQtMC4wOCwwLjQ1LTAuMjUsMC42MmMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjVjLTAuMjUsMC0wLjQ2LTAuMDgtMC42My0wLjI1QzIxLjk1LDcyLjAxLDIxLjg2LDcxLjgsMjEuODYsNzEuNTYKCSBNMjAuOSw3Ni4wN2MwLTAuMzMsMC4wOS0wLjY1LDAuMjgtMC45NmMwLjE5LTAuMzEsMC40OS0wLjU5LDAuODktMC44NGMwLjQtMC4yNSwwLjkyLTAuNDcsMS41NS0wLjY0YzAuNjMtMC4xOCwxLjM4LTAuMywyLjI2LTAuMzYKCXYzLjY3aDEuNjd2MS4yOGgtMi42Yy0wLjA5LTAuMDUtMC4xNi0wLjEzLTAuMjItMC4yMWMtMC4wNi0wLjA5LTAuMTEtMC4xNy0wLjE1LTAuMjZjLTAuMDQtMC4wOS0wLjA3LTAuMTktMC4wOS0wLjI5CgljLTAuMDQsMC4xNS0wLjEyLDAuMjgtMC4yMywwLjM5Yy0wLjEsMC4wOS0wLjI1LDAuMTgtMC40NCwwLjI2Yy0wLjE5LDAuMDgtMC40NSwwLjEyLTAuNzcsMC4xMmMtMC43OSwwLTEuMzUtMC4xOS0xLjY3LTAuNTcKCUMyMS4wNiw3Ny4yNiwyMC45LDc2Ljc0LDIwLjksNzYuMDciLz4KPHJlY3QgeD0iMjcuMjciIHk9Ijc2LjkzIiBjbGFzcz0ic3QwIiB3aWR0aD0iNC4yMSIgaGVpZ2h0PSIxLjI4Ii8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik0zNC4zNCw4MC4xMmMwLTAuMjUsMC4wOS0wLjQ2LDAuMjYtMC42NGMwLjE3LTAuMTgsMC4zOS0wLjI2LDAuNjMtMC4yNmMwLjI0LDAsMC40NCwwLjA5LDAuNjEsMC4yNgoJYzAuMTcsMC4xOCwwLjI1LDAuMzksMC4yNSwwLjY0YzAsMC4yNC0wLjA4LDAuNDUtMC4yNSwwLjYxYy0wLjE3LDAuMTctMC4zNywwLjI1LTAuNjEsMC4yNWMtMC4yNSwwLTAuNDYtMC4wOC0wLjYzLTAuMjUKCUMzNC40Myw4MC41NiwzNC4zNCw4MC4zNiwzNC4zNCw4MC4xMiBNMzIuMDQsODAuMTJjMC0wLjI1LDAuMDktMC40NiwwLjI2LTAuNjRjMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjYKCWMwLjI0LDAsMC40NCwwLjA5LDAuNjEsMC4yNmMwLjE3LDAuMTgsMC4yNSwwLjM5LDAuMjUsMC42NGMwLDAuMjQtMC4wOCwwLjQ1LTAuMjUsMC42MWMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjUKCWMtMC4yNSwwLTAuNDYtMC4wOC0wLjYzLTAuMjVDMzIuMTIsODAuNTYsMzIuMDQsODAuMzYsMzIuMDQsODAuMTIgTTMxLjE5LDc2LjkzaDIuMTl2LTMuNDNsMS40OC0wLjQydjMuODZoMS44N3YxLjI4aC01LjUzVjc2LjkzeiIKCS8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik00MC44LDc3LjM5Yy0wLjA5LTAuNy0wLjIyLTEuMjctMC4zNy0xLjcxYy0wLjE1LTAuNDMtMC4zNC0wLjY1LTAuNTYtMC42NWMtMC4wOCwwLTAuMjEsMC4wOS0wLjQxLDAuMjcKCWMtMC4xMiwwLjEyLTAuMjQsMC4yOC0wLjM3LDAuNDljLTAuMTMsMC4yMS0wLjI0LDAuMzktMC4zMiwwLjU2YzAuMzMsMC4yNSwwLjY2LDAuNDYsMS4wMSwwLjY0QzQwLjE0LDc3LjE2LDQwLjQ4LDc3LjI5LDQwLjgsNzcuMzkKCSBNNDIuMSw3Ny4xOWMtMC4wMiwwLjItMC4xLDAuNDYtMC4yNywwLjc3Yy0wLjMxLDAuNjQtMC42LDAuOTYtMC44OCwwLjk2Yy0wLjEsMC0wLjIxLTAuMDMtMC4zMy0wLjA4CgljLTAuMjMtMC4wOS0wLjU1LTAuMjQtMC45NS0wLjQzYy0wLjQtMC4yLTAuODgtMC40NC0xLjQ1LTAuNzNjLTAuMTMsMC4yMy0wLjI4LDAuMzktMC40NSwwLjQ2Yy0wLjEzLDAuMDUtMC4zNSwwLjA3LTAuNjUsMC4wNwoJaC0wLjc2di0xLjI4aDAuODZjMC4yMy0wLjU0LDAuNDgtMS4wMywwLjczLTEuNDdjMC4yNi0wLjQ0LDAuNTEtMC44MiwwLjc2LTEuMTNjMC4yNS0wLjMxLDAuNS0wLjU1LDAuNzMtMC43MgoJYzAuMjQtMC4xNywwLjQ2LTAuMjYsMC42Ni0wLjI2YzAuNTEsMCwwLjk0LDAuMzcsMS4yOCwxLjFjMC4xLDAuMjIsMC4yLDAuNDksMC4zLDAuODNjMC4xLDAuMzMsMC4yMSwwLjczLDAuMzMsMS4yCglDNDIuMDksNzYuOCw0Mi4xMiw3Ny4wNCw0Mi4xLDc3LjE5Ii8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik00My43Nyw3Mi4yNWMwLjA2LTAuMDQsMC4xNi0wLjA5LDAuMy0wLjE0YzAuMTQtMC4wNSwwLjI3LTAuMTEsMC40MS0wLjE4YzAuMTYtMC4wNywwLjM0LTAuMTQsMC41Mi0wLjIxCgljMC4yMywwLjMsMC40NiwwLjY5LDAuNjgsMS4xN2MwLjIyLDAuNDcsMC40MiwwLjk2LDAuNiwxLjQ2YzAuMTgsMC41LDAuMzQsMC45OSwwLjQ4LDEuNDVjMC4xNCwwLjQ2LDAuMjUsMC44MywwLjMzLDEuMTEKCWMwLjE3LTAuMDIsMC4zMS0wLjA3LDAuNDEtMC4xNWMwLjEtMC4wOCwwLjE5LTAuMTcsMC4yNC0wLjI4YzAuMDYtMC4xMSwwLjEtMC4yMiwwLjEyLTAuMzVjMC4wMi0wLjEzLDAuMDMtMC4yNSwwLjAzLTAuMzh2LTUuMDYKCWwxLjQ5LTAuNDV2NS41OHYwLjM5YzAsMC4yNSwwLjA2LDAuNDMsMC4xOSwwLjU0YzAuMTMsMC4xMSwwLjMsMC4xNiwwLjUxLDAuMTZoMC45M3YxLjI4aC0wLjUyYy0wLjM3LDAtMC42OS0wLjA3LTAuOTUtMC4yMQoJYy0wLjI2LTAuMTQtMC40Ni0wLjMzLTAuNTktMC41NmMtMC4xOCwwLjIzLTAuNDMsMC40MS0wLjc1LDAuNTZjLTAuMzIsMC4xNC0wLjc1LDAuMjItMS4zLDAuMjJoLTQuMDhsMC40MS0xLjI4aDIuNDMKCWMtMC4wNi0wLjI3LTAuMTQtMC41OS0wLjI0LTAuOTVjLTAuMS0wLjM2LTAuMjMtMC43NS0wLjM4LTEuMTZjLTAuMTUtMC40MS0wLjMzLTAuODMtMC41NC0xLjI3QzQ0LjI4LDczLjEsNDQuMDQsNzIuNjcsNDMuNzcsNzIuMjUKCSIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNNTAuNjYsNzYuOTNoMS44NmMtMC4xNi0wLjItMC4yNi0wLjQ1LTAuMzEtMC43NGMtMC4wNS0wLjI5LTAuMDgtMC42LTAuMDgtMC45M2MwLTAuNjMsMC4yNS0xLjEzLDAuNzYtMS41MQoJYzAuNTEtMC4zNywxLjIxLTAuNTcsMi4xLTAuNTljMC4zMy0wLjAyLDAuNjksMCwxLjEsMC4wNmMwLjQxLDAuMDUsMC44LDAuMTIsMS4xNywwLjE5djEuMzFjLTAuMTItMC4wMy0wLjI2LTAuMDctMC40NC0wLjExCgljLTAuMTctMC4wNC0wLjM2LTAuMDctMC41Ny0wLjExYy0wLjIxLTAuMDMtMC40Mi0wLjA2LTAuNjQtMC4wOGMtMC4yMi0wLjAyLTAuNDQtMC4wMy0wLjY1LTAuMDNjLTAuMTcsMC0wLjMzLDAuMDEtMC40OCwwLjA0CgljLTAuMTUsMC4wMi0wLjI4LDAuMDctMC4zOSwwLjE0Yy0wLjExLDAuMDctMC4yLDAuMTctMC4yNiwwLjI5Yy0wLjA2LDAuMTMtMC4wOSwwLjI4LTAuMDksMC40OGMwLDAuNDIsMC4wNCwwLjc2LDAuMTIsMQoJYzAuMDgsMC4yNSwwLjE5LDAuNDQsMC4zMiwwLjU4aDMuMTJ2MS4yOGgtNi42NlY3Ni45M3oiLz4KPHBhdGggY2xhc3M9InN0MCIgZD0iTTYyLjMyLDc2LjkzYy0wLjAyLTAuMDktMC4wNi0wLjItMC4xLTAuMzNjLTAuMDQtMC4xMy0wLjA5LTAuMjctMC4xNi0wLjQxYy0wLjA2LTAuMTQtMC4xMy0wLjI5LTAuMjEtMC40NQoJYy0wLjA4LTAuMTUtMC4xNi0wLjI5LTAuMjYtMC40M2MtMC4xNiwwLjE2LTAuMzIsMC4zMS0wLjQ2LDAuNDVjLTAuMTUsMC4xNC0wLjMsMC4yNy0wLjQ2LDAuNGMtMC4xNiwwLjEzLTAuMzMsMC4yNS0wLjUxLDAuMzgKCWMtMC4xOCwwLjEyLTAuMzksMC4yNS0wLjYxLDAuMzlINjIuMzJ6IE02Mi4wOSw4MS41OGwtMi43OSwwLjgzdi0wLjc0bDAuNzctMC4yM2MtMC4wOS0wLjAyLTAuMTYtMC4wNS0wLjIzLTAuMTEKCWMtMC4wNy0wLjA2LTAuMTItMC4xMy0wLjE3LTAuMjFjLTAuMDUtMC4wOC0wLjA4LTAuMTctMC4xMS0wLjI2Yy0wLjAzLTAuMDktMC4wNC0wLjE4LTAuMDQtMC4yNWMwLTAuMjQsMC4wNS0wLjQ2LDAuMTYtMC42NQoJYzAuMTEtMC4xOSwwLjI1LTAuMzYsMC40MS0wLjQ5czAuMzUtMC4yNCwwLjU0LTAuMzFjMC4xOS0wLjA3LDAuMzgtMC4xMSwwLjU1LTAuMTFjMC4xOCwwLDAuMzUsMC4wMywwLjUxLDAuMDkKCWMwLjE2LDAuMDYsMC4zMiwwLjE5LDAuNDgsMC4zOWMtMC4wOCwwLjA2LTAuMTcsMC4xNC0wLjI4LDAuMjNjLTAuMTEsMC4wOS0wLjI1LDAuMjEtMC40LDAuMzRjLTAuMTQtMC4xNS0wLjMxLTAuMjItMC41Mi0wLjIyCgljLTAuMiwwLTAuMzUsMC4wNS0wLjQzLDAuMTZjLTAuMDksMC4xMS0wLjEzLDAuMjItMC4xMywwLjMzYzAsMC4xLDAuMDMsMC4yLDAuMDksMC4yOGMwLjA2LDAuMDksMC4xMywwLjE2LDAuMjEsMC4yMgoJYzAuMDksMC4wNiwwLjE3LDAuMTEsMC4yNywwLjE0YzAuMDksMC4wMywwLjE3LDAuMDYsMC4yNCwwLjA2bDAuODctMC4yNlY4MS41OHogTTU4LjU4LDcwLjM3YzAuMTksMC4xOCwwLjQyLDAuMzcsMC42OSwwLjU4CgljMC4yNywwLjIxLDAuNTQsMC40MywwLjgzLDAuNjdjMC4yOCwwLjI0LDAuNTcsMC40OSwwLjg1LDAuNzZjMC4yOCwwLjI3LDAuNTQsMC41NiwwLjc3LDAuODZjMC4wNS0wLjA2LDAuMDgtMC4yOSwwLjA4LTAuNjl2LTEuODYKCWwxLjQzLTAuNDd2Mi4zN2MwLDAuNjMtMC4yMywxLjIxLTAuNywxLjc1YzAuNjQsMSwwLjk2LDEuODksMC45NiwyLjY3djEuMjFoLTUuMjh2LTEuNThjMC4yOS0wLjE5LDAuNTYtMC4zOCwwLjgzLTAuNTkKCWMwLjI3LTAuMjEsMC41Mi0wLjQxLDAuNzUtMC42MWMwLjIzLTAuMiwwLjQ0LTAuMzksMC42My0wLjU3YzAuMTktMC4xOCwwLjM1LTAuMzQsMC40OC0wLjQ3Yy0wLjIyLTAuMy0wLjQ2LTAuNTktMC43Mi0wLjg0CgljLTAuMjYtMC4yNi0wLjUzLTAuNS0wLjgtMC43MWMtMC4yNy0wLjIyLTAuNTQtMC40Mi0wLjgtMC42MWMtMC4yNi0wLjE5LTAuNDktMC4zNi0wLjY5LTAuNTNMNTguNTgsNzAuMzd6Ii8+Cjxwb2x5Z29uIGNsYXNzPSJzdDAiIHBvaW50cz0iNjYuMTYsNzAuMjYgNjYuMTYsNzguMjEgNjQuNjgsNzguMjEgNjQuNjgsNzAuNjggIi8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik03Mi43NSw3MS41MWMwLTAuMjgsMC4xLTAuNTIsMC4zLTAuNzJjMC4yLTAuMiwwLjQ0LTAuMywwLjcyLTAuM2MwLjE0LDAsMC4yNywwLjAzLDAuMzksMC4wOAoJYzAuMTIsMC4wNSwwLjIyLDAuMTMsMC4zMSwwLjIyYzAuMDksMC4wOSwwLjE2LDAuMiwwLjIxLDAuMzJjMC4wNSwwLjEzLDAuMDgsMC4yNiwwLjA4LDAuNGMwLDAuMjctMC4xLDAuNTEtMC4yOSwwLjcKCWMtMC4xOSwwLjItMC40MywwLjI5LTAuNywwLjI5Yy0wLjE0LDAtMC4yNy0wLjAzLTAuNC0wLjA4Yy0wLjEyLTAuMDUtMC4yMy0wLjEyLTAuMzItMC4yMWMtMC4wOS0wLjA5LTAuMTYtMC4xOS0wLjIyLTAuMzIKCUM3Mi43OCw3MS43OSw3Mi43NSw3MS42NSw3Mi43NSw3MS41MSBNNzMuODYsNzYuMjdjMC0wLjA5LTAuMDItMC4yMy0wLjA1LTAuNDFjLTAuMDMtMC4xOC0wLjA5LTAuMzYtMC4xNy0wLjU2CgljLTAuMDktMC4xOS0wLjItMC4zNy0wLjM0LTAuNTNjLTAuMTQtMC4xNi0wLjMzLTAuMjgtMC41NS0wLjM1Yy0wLjE0LDAuMDgtMC4yNywwLjE5LTAuMzgsMC4zM2MtMC4xMiwwLjE0LTAuMjIsMC4zLTAuMywwLjQ1CgljLTAuMDksMC4xNi0wLjE1LDAuMzEtMC4yLDAuNDdjLTAuMDUsMC4xNi0wLjA4LDAuMjktMC4wOCwwLjM5YzAsMC4xNiwwLjAzLDAuMjksMC4wOCwwLjRjMC4wNSwwLjExLDAuMTIsMC4yLDAuMiwwLjI3CgljMC4wOCwwLjA3LDAuMTcsMC4xMiwwLjI4LDAuMTVjMC4xLDAuMDMsMC4yMSwwLjA1LDAuMzIsMC4wNWMwLjM0LDAsMC42My0wLjA1LDAuODUtMC4xNkM3My43NCw3Ni42Nyw3My44Niw3Ni41LDczLjg2LDc2LjI3CgkgTTcwLjM4LDcxLjUxYzAtMC4yOCwwLjEtMC41MiwwLjMtMC43MmMwLjItMC4yLDAuNDQtMC4zLDAuNzItMC4zYzAuMTQsMCwwLjI3LDAuMDMsMC4zOSwwLjA4YzAuMTIsMC4wNSwwLjIyLDAuMTMsMC4zMSwwLjIyCgljMC4wOSwwLjA5LDAuMTYsMC4yLDAuMjEsMC4zMmMwLjA1LDAuMTMsMC4wOCwwLjI2LDAuMDgsMC40YzAsMC4yNy0wLjEsMC41MS0wLjI5LDAuN2MtMC4xOSwwLjItMC40MywwLjI5LTAuNywwLjI5CgljLTAuMTQsMC0wLjI3LTAuMDMtMC40LTAuMDhjLTAuMTItMC4wNS0wLjIzLTAuMTItMC4zMi0wLjIxYy0wLjA5LTAuMDktMC4xNi0wLjE5LTAuMjEtMC4zMkM3MC40MSw3MS43OSw3MC4zOCw3MS42NSw3MC4zOCw3MS41MQoJIE03NS40Nyw3Ni4zMWMwLDAuMzctMC4wNywwLjY4LTAuMjEsMC45M2MtMC4xNCwwLjI1LTAuMzMsMC40Ni0wLjU4LDAuNjNjLTAuMjUsMC4xNi0wLjU0LDAuMjgtMC44OSwwLjM2CgljLTAuMzUsMC4wNy0wLjcyLDAuMTEtMS4xMywwLjExYy0wLjI3LDAtMC41NS0wLjAyLTAuODQtMC4wN2MtMC4yOS0wLjA1LTAuNTUtMC4xMy0wLjc5LTAuMjZjLTAuMjQtMC4xMy0wLjQzLTAuMjktMC41OS0wLjUKCWMtMC4xNi0wLjIxLTAuMjMtMC40OC0wLjIzLTAuODFjMC0wLjYxLDAuMTMtMS4xNiwwLjM4LTEuNjVjMC4yNS0wLjQ5LDAuNjEtMC45MSwxLjA5LTEuMjZsLTAuNDEtMC4xOGwwLjU3LTAuOTMKCWMwLjU2LDAuMTIsMS4wNiwwLjI5LDEuNTEsMC41MWMwLjQ1LDAuMjIsMC44MywwLjQ5LDEuMTUsMC44YzAuMzEsMC4zMSwwLjU2LDAuNjYsMC43MywxLjA1Qzc1LjM5LDc1LjQzLDc1LjQ3LDc1Ljg1LDc1LjQ3LDc2LjMxIgoJLz4KPHBhdGggY2xhc3M9InN0MCIgZD0iTTc4LjQ1LDczYzAuMTIsMC42MywwLjIsMS4yNywwLjI2LDEuOWMwLjA1LDAuNjMsMC4wOSwxLjIyLDAuMTIsMS43N2gxLjI5djEuNTRoLTEuMjgKCWMtMC4wMSwwLjEzLTAuMDMsMC4yOS0wLjA2LDAuNDhjLTAuMDMsMC4xOS0wLjA5LDAuMzgtMC4xOCwwLjU3Yy0wLjA5LDAuMi0wLjIsMC4zOS0wLjM2LDAuNTljLTAuMTYsMC4xOS0wLjM2LDAuMzctMC42MSwwLjUzCgljLTAuMjUsMC4xNi0wLjU2LDAuMjgtMC45MiwwLjM4Yy0wLjM2LDAuMDktMC44LDAuMTQtMS4zMSwwLjE0bC0wLjI3LTAuOTZjMC40LTAuMDEsMC43Ni0wLjA4LDEuMDctMC4yMgoJYzAuMTMtMC4wNiwwLjI2LTAuMTQsMC4zOS0wLjIzYzAuMTMtMC4wOSwwLjI0LTAuMjEsMC4zNC0wLjM1YzAuMS0wLjE0LDAuMTgtMC4zMSwwLjI0LTAuNWMwLjA2LTAuMiwwLjA5LTAuNDIsMC4wOS0wLjY4CgljMC0wLjcxLTAuMDItMS40NC0wLjA1LTIuMTlzLTAuMTUtMS40OS0wLjM0LTIuMjJMNzguNDUsNzN6Ii8+CjxyZWN0IHg9Ijc5LjgyIiB5PSI3Ni42NyIgY2xhc3M9InN0MCIgd2lkdGg9IjQuMjEiIGhlaWdodD0iMS41NCIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNODYuMzUsODAuMjNjMC0wLjI4LDAuMS0wLjUyLDAuMy0wLjcyYzAuMi0wLjIsMC40NC0wLjMsMC43MS0wLjNjMC4xNCwwLDAuMjcsMC4wMywwLjM5LDAuMDgKCWMwLjEyLDAuMDUsMC4yMiwwLjEzLDAuMzEsMC4yMmMwLjA5LDAuMDksMC4xNiwwLjIsMC4yMSwwLjMyYzAuMDUsMC4xMiwwLjA4LDAuMjYsMC4wOCwwLjRjMCwwLjI3LTAuMSwwLjUxLTAuMjksMC43CgljLTAuMTksMC4yLTAuNDMsMC4yOS0wLjcsMC4yOWMtMC4xNCwwLTAuMjctMC4wMy0wLjQtMC4wOGMtMC4xMi0wLjA1LTAuMjMtMC4xMi0wLjMyLTAuMjFjLTAuMDktMC4wOS0wLjE2LTAuMi0wLjIyLTAuMzIKCUM4Ni4zOCw4MC41LDg2LjM1LDgwLjM3LDg2LjM1LDgwLjIzIE04My45OCw4MC4yM2MwLTAuMjgsMC4xLTAuNTIsMC4zLTAuNzJjMC4yLTAuMiwwLjQ0LTAuMywwLjcxLTAuM2MwLjE0LDAsMC4yNywwLjAzLDAuMzksMC4wOAoJYzAuMTIsMC4wNSwwLjIyLDAuMTMsMC4zMSwwLjIyYzAuMDksMC4wOSwwLjE2LDAuMiwwLjIxLDAuMzJjMC4wNSwwLjEyLDAuMDgsMC4yNiwwLjA4LDAuNGMwLDAuMjctMC4xLDAuNTEtMC4yOSwwLjcKCWMtMC4xOSwwLjItMC40MywwLjI5LTAuNywwLjI5Yy0wLjE0LDAtMC4yNy0wLjAzLTAuMzktMC4wOGMtMC4xMi0wLjA1LTAuMjMtMC4xMi0wLjMyLTAuMjFjLTAuMDktMC4wOS0wLjE2LTAuMi0wLjIyLTAuMzIKCUM4NC4wMSw4MC41LDgzLjk4LDgwLjM3LDgzLjk4LDgwLjIzIE04OC4xNSw3Mi45OHY1LjIzaC00LjQydi0xLjUzaDIuNjNWNzMuNUw4OC4xNSw3Mi45OHoiLz4KPHBhdGggY2xhc3M9InN0MCIgZD0iTTg5LjU1LDcxLjUzYzAtMC4yOCwwLjEtMC41MiwwLjMtMC43MmMwLjItMC4yLDAuNDQtMC4zLDAuNzEtMC4zYzAuMTQsMCwwLjI3LDAuMDMsMC4zOSwwLjA4CgljMC4xMiwwLjA1LDAuMjIsMC4xMywwLjMxLDAuMjJjMC4wOSwwLjA5LDAuMTYsMC4yLDAuMjEsMC4zMmMwLjA1LDAuMTMsMC4wOCwwLjI2LDAuMDgsMC40YzAsMC4yNy0wLjEsMC41MS0wLjI5LDAuNwoJYy0wLjE5LDAuMi0wLjQzLDAuMjktMC43LDAuMjljLTAuMTQsMC0wLjI3LTAuMDMtMC4zOS0wLjA4Yy0wLjEyLTAuMDUtMC4yMy0wLjEyLTAuMzItMC4yMWMtMC4wOS0wLjA5LTAuMTYtMC4yLTAuMjItMC4zMgoJQzg5LjU4LDcxLjgsODkuNTUsNzEuNjcsODkuNTUsNzEuNTMgTTkxLjU3LDczYzAuMTIsMC42MywwLjIsMS4yNywwLjI2LDEuOWMwLjA1LDAuNjMsMC4wOSwxLjIyLDAuMTIsMS43N2gxLjI5djEuNTRoLTEuMjgKCWMtMC4wMSwwLjEzLTAuMDMsMC4yOS0wLjA2LDAuNDhjLTAuMDMsMC4xOS0wLjA5LDAuMzgtMC4xOCwwLjU3Yy0wLjA5LDAuMi0wLjIsMC4zOS0wLjM2LDAuNTljLTAuMTYsMC4xOS0wLjM2LDAuMzctMC42MSwwLjUzCgljLTAuMjUsMC4xNi0wLjU2LDAuMjgtMC45MiwwLjM4Yy0wLjM2LDAuMDktMC44LDAuMTQtMS4zMSwwLjE0bC0wLjI3LTAuOTZjMC40LTAuMDEsMC43Ni0wLjA4LDEuMDctMC4yMgoJYzAuMTMtMC4wNiwwLjI2LTAuMTQsMC4zOS0wLjIzYzAuMTMtMC4wOSwwLjI0LTAuMjEsMC4zNC0wLjM1YzAuMS0wLjE0LDAuMTgtMC4zMSwwLjI0LTAuNWMwLjA2LTAuMiwwLjA5LTAuNDIsMC4wOS0wLjY4CgljMC0wLjcxLTAuMDItMS40NC0wLjA1LTIuMTlzLTAuMTUtMS40OS0wLjM0LTIuMjJMOTEuNTcsNzN6Ii8+CjxwYXRoIGNsYXNzPSJzdDAiIGQ9Ik05NS43OCw4MC4xN2MwLTAuMjgsMC4xLTAuNTIsMC4zLTAuNzJjMC4yLTAuMiwwLjQ0LTAuMywwLjcxLTAuM2MwLjE0LDAsMC4yNywwLjAzLDAuMzksMC4wOAoJYzAuMTIsMC4wNSwwLjIyLDAuMTMsMC4zMSwwLjIyYzAuMDksMC4wOSwwLjE2LDAuMiwwLjIxLDAuMzJjMC4wNSwwLjEzLDAuMDgsMC4yNiwwLjA4LDAuNGMwLDAuMjctMC4xLDAuNTEtMC4yOSwwLjcKCWMtMC4xOSwwLjItMC40MywwLjI5LTAuNywwLjI5Yy0wLjE0LDAtMC4yNy0wLjAzLTAuMzktMC4wOGMtMC4xMi0wLjA1LTAuMjMtMC4xMi0wLjMyLTAuMjFjLTAuMDktMC4wOS0wLjE2LTAuMi0wLjIyLTAuMzIKCUM5NS44MSw4MC40NSw5NS43OCw4MC4zMiw5NS43OCw4MC4xNyBNMTAwLjg1LDc4LjIxaC03Ljk2di0xLjU0aDQuOThjLTAuMi0wLjQxLTAuMzctMC43NS0wLjUyLTEuMDIKCWMtMC4xNC0wLjI3LTAuMjctMC40OS0wLjM5LTAuNjVjLTAuMTItMC4xNi0wLjIzLTAuMjctMC4zNC0wLjM0Yy0wLjExLTAuMDctMC4yMy0wLjEtMC4zNy0wLjFjLTAuMiwwLTAuMzgsMC4wNS0wLjUyLDAuMTUKCWMtMC4xNSwwLjEtMC4zMiwwLjI3LTAuNTEsMC41MmwtMS4wMS0wLjljMC4xMi0wLjE5LDAuMjgtMC4zNiwwLjQ1LTAuNTNjMC4xOC0wLjE2LDAuMzctMC4zMSwwLjU5LTAuNDMKCWMwLjIxLTAuMTIsMC40My0wLjIyLDAuNjYtMC4yOWMwLjIzLTAuMDcsMC40Ni0wLjExLDAuNjktMC4xMWMwLjI2LDAsMC40OSwwLjA2LDAuNzEsMC4xN2MwLjIyLDAuMTEsMC40MywwLjMsMC42NSwwLjU1CgljMC4yMiwwLjI1LDAuNDUsMC41OCwwLjcsMC45OGMwLjI1LDAuNCwwLjU0LDAuODksMC44NywxLjQ2YzAuMTEsMC4xOSwwLjI0LDAuMzIsMC4zOCwwLjQxYzAuMTUsMC4wOSwwLjMxLDAuMTMsMC40OCwwLjEzaDAuNDcKCVY3OC4yMXoiLz4KPHBvbHlnb24gY2xhc3M9InN0MCIgcG9pbnRzPSIxMDMuODQsNzAuMTcgMTAzLjg0LDc4LjIxIDEwMC41MSw3OC4yMSAxMDAuNTEsNzYuNjcgMTAyLjA1LDc2LjY3IDEwMi4wNSw3MC42OCAiLz4KPHBvbHlnb24gY2xhc3M9InN0MCIgcG9pbnRzPSIxMDYuOTksNzAuMTcgMTA2Ljk5LDc4LjIxIDEwNS4yLDc4LjIxIDEwNS4yLDcwLjY4ICIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMTE0LjkxLDcxLjU2YzAtMC4yNSwwLjA5LTAuNDYsMC4yNi0wLjY0YzAuMTctMC4xOCwwLjM5LTAuMjYsMC42My0wLjI2YzAuMjQsMCwwLjQ0LDAuMDksMC42MSwwLjI2CgljMC4xNywwLjE4LDAuMjUsMC4zOSwwLjI1LDAuNjRjMCwwLjI0LTAuMDgsMC40NS0wLjI1LDAuNjJjLTAuMTcsMC4xNy0wLjM3LDAuMjUtMC42MSwwLjI1Yy0wLjI1LDAtMC40Ni0wLjA4LTAuNjMtMC4yNQoJQzExNC45OSw3Mi4wMSwxMTQuOTEsNzEuOCwxMTQuOTEsNzEuNTYgTTExMy4wNSw3NS44NnYwLjM3YzAsMC4yMywwLjA3LDAuNCwwLjIsMC41MmMwLjEzLDAuMTIsMC4zNSwwLjE4LDAuNjQsMC4xOGgxLjM0Vjc0LjYKCWMtMC4zMywwLjA2LTAuNjIsMC4xNC0wLjg5LDAuMjNjLTAuMjcsMC4wOS0wLjQ5LDAuMi0wLjY4LDAuM2MtMC4xOSwwLjExLTAuMzMsMC4yMy0wLjQ0LDAuMzUKCUMxMTMuMTEsNzUuNjEsMTEzLjA1LDc1Ljc0LDExMy4wNSw3NS44NiBNMTEyLjYsNzEuNTZjMC0wLjI1LDAuMDktMC40NiwwLjI2LTAuNjRjMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjYKCWMwLjI0LDAsMC40NCwwLjA5LDAuNjEsMC4yNmMwLjE3LDAuMTgsMC4yNSwwLjM5LDAuMjUsMC42NGMwLDAuMjQtMC4wOCwwLjQ1LTAuMjUsMC42MmMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjUKCWMtMC4yNSwwLTAuNDYtMC4wOC0wLjYzLTAuMjVDMTEyLjY5LDcyLjAxLDExMi42LDcxLjgsMTEyLjYsNzEuNTYgTTExMS42NCw3Ni4wN2MwLTAuMzMsMC4wOS0wLjY1LDAuMjgtMC45NgoJYzAuMTktMC4zMSwwLjQ5LTAuNTksMC44OS0wLjg0YzAuNC0wLjI1LDAuOTItMC40NywxLjU1LTAuNjRjMC42My0wLjE4LDEuMzgtMC4zLDIuMjYtMC4zNnYzLjY3aDEuNjd2MS4yOGgtMi42CgljLTAuMDktMC4wNS0wLjE2LTAuMTMtMC4yMi0wLjIxYy0wLjA2LTAuMDktMC4xMS0wLjE3LTAuMTQtMC4yNmMtMC4wNC0wLjA5LTAuMDctMC4xOS0wLjA5LTAuMjljLTAuMDQsMC4xNS0wLjEyLDAuMjgtMC4yMywwLjM5CgljLTAuMSwwLjA5LTAuMjUsMC4xOC0wLjQ0LDAuMjZjLTAuMTksMC4wOC0wLjQ1LDAuMTItMC43NywwLjEyYy0wLjc5LDAtMS4zNS0wLjE5LTEuNjctMC41N0MxMTEuOCw3Ny4yNiwxMTEuNjQsNzYuNzQsMTExLjY0LDc2LjA3CgkiLz4KPHJlY3QgeD0iMTE4LjAxIiB5PSI3Ni45MyIgY2xhc3M9InN0MCIgd2lkdGg9IjQuMjEiIGhlaWdodD0iMS4yOCIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMTI5LjA0LDc4LjIxaC02Ljk0di0xLjI4aDMuODh2LTAuMzVjMC0wLjIzLTAuMDYtMC40Ny0wLjE5LTAuNzNjLTAuMTItMC4yNi0wLjMtMC41Mi0wLjUyLTAuNzcKCWMtMC4yMi0wLjI1LTAuNDktMC40OS0wLjgtMC43MmMtMC4zMS0wLjIzLTAuNjUtMC40My0xLjAyLTAuNTlsMC4wOS0yLjAybDQuNS0xLjU0bC0wLjM3LDEuNTZsLTIuOTMsMC45CgljMC4zMywwLjIzLDAuNjQsMC40OSwwLjk0LDAuOGMwLjMsMC4zLDAuNTYsMC42MiwwLjgsMC45NGMwLjI1LDAuMzUsMC40NiwwLjcxLDAuNjMsMS4wN2MwLjE3LDAuMzYsMC4yNiwwLjczLDAuMjYsMS4xdjAuMzVoMS42NwoJVjc4LjIxeiIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMTMwLjg5LDgwLjFjMC0wLjI1LDAuMDktMC40NiwwLjI2LTAuNjRjMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjZjMC4yNCwwLDAuNDQsMC4wOSwwLjYxLDAuMjYKCWMwLjE3LDAuMTgsMC4yNSwwLjM5LDAuMjUsMC42NGMwLDAuMjQtMC4wOCwwLjQ1LTAuMjUsMC42MWMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjVjLTAuMjUsMC0wLjQ2LTAuMDgtMC42My0wLjI1CglDMTMwLjk4LDgwLjU1LDEzMC44OSw4MC4zNSwxMzAuODksODAuMSBNMTI4Ljg3LDc2LjkzaDIuMTl2LTMuNDNsMS40OC0wLjQydjMuODZoMS44N3YxLjI4aC01LjUzVjc2LjkzeiIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMTM5LjgsNzEuNTZjMC0wLjI1LDAuMDktMC40NiwwLjI2LTAuNjRjMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjZjMC4yNCwwLDAuNDQsMC4wOSwwLjYxLDAuMjYKCWMwLjE3LDAuMTgsMC4yNSwwLjM5LDAuMjUsMC42NGMwLDAuMjQtMC4wOCwwLjQ1LTAuMjUsMC42MmMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjVjLTAuMjUsMC0wLjQ2LTAuMDgtMC42My0wLjI1CglDMTM5Ljg4LDcyLjAxLDEzOS44LDcxLjgsMTM5LjgsNzEuNTYgTTEzOC42LDY5LjMzYzAtMC4yNSwwLjA5LTAuNDYsMC4yNi0wLjY0YzAuMTctMC4xOCwwLjM5LTAuMjYsMC42My0wLjI2CgljMC4yNCwwLDAuNDQsMC4wOSwwLjYxLDAuMjZjMC4xNywwLjE4LDAuMjUsMC4zOSwwLjI1LDAuNjRjMCwwLjI0LTAuMDgsMC40NS0wLjI1LDAuNjJjLTAuMTcsMC4xNy0wLjM3LDAuMjYtMC42MSwwLjI2CgljLTAuMjUsMC0wLjQ2LTAuMDktMC42My0wLjI2QzEzOC42OSw2OS43OCwxMzguNiw2OS41OCwxMzguNiw2OS4zMyBNMTM3LjQ5LDcxLjU2YzAtMC4yNSwwLjA5LTAuNDYsMC4yNi0wLjY0CgljMC4xNy0wLjE4LDAuMzktMC4yNiwwLjYzLTAuMjZjMC4yNCwwLDAuNDQsMC4wOSwwLjYxLDAuMjZjMC4xNywwLjE4LDAuMjUsMC4zOSwwLjI1LDAuNjRjMCwwLjI0LTAuMDgsMC40NS0wLjI1LDAuNjIKCWMtMC4xNywwLjE3LTAuMzcsMC4yNS0wLjYxLDAuMjVjLTAuMjUsMC0wLjQ2LTAuMDgtMC42My0wLjI1QzEzNy41OCw3Mi4wMSwxMzcuNDksNzEuOCwxMzcuNDksNzEuNTYgTTEzNC4wNSw3Ni45M2gxLjkxdi0zLjQKCWwxLjQtMC40OXYzLjg5aDEuNTN2LTMuNGwxLjQtMC40OXYzLjg5aDEuNTJ2LTMuNGwxLjQtMC40OXY1LjE3aC05LjE1Vjc2LjkzeiIvPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNNzQuODksMTguMDdjLTEuMDgsMC4wMy0xLjkzLDAuOTYtMS44OSwyLjA3YzAuMDMsMS4xLDAuOTMsMS45NywyLjAxLDEuOTRjMS4wOC0wLjAzLDEuOTMtMC45NiwxLjg5LTIuMDYKCWMtMC4wMy0xLjA4LTAuOS0xLjk1LTEuOTUtMS45NUg3NC44OXogTTgyLjMyLDAuNDJjLTEsMC43Mi0xLjgzLDIuMzUtMS44Myw0LjgzYzAuMDEsMS41MywwLjQzLDMuMzYsMS41OCw1LjQxCgljLTEuNTQsMi4xNi0xLjgzLDQuMTQtMS4xNyw2LjA0YzAuNSwxLjQ0LDAuNzUsMS44MiwwLjk4LDIuNjljMC41NywyLjItMC4wNiw0Ljg0LTEuNzYsOC45MWMtMS4zNywzLjMyLTMuMTYsNi43OS0zLjE2LDExLjAxCgljMC4wMSwwLjk3LDAuMDksMS45MSwwLjIyLDIuODRjMC4xNi0wLjE2LDAuNS0wLjQ5LDAuOTEtMC44OGMtMC4yLTMuMzEsMS4wOC02LjY0LDIuNjctOS42M2MyLjMtNC4zNywyLjU5LTguODEsMi4xNC0xMS4yNAoJYzEuNjIsMS43Nyw0LjM0LDQuNDEsNS45Myw3LjEyYzAuNTQsMC45MSwwLjg2LDEuNzgsMC45NCwyLjY2YzAuMDgsMi4xNC0wLjU4LDMuNjgtMS44Nyw1LjE4Yy0xLjA5LDEuMjctMC43MSwyLjM5LTAuNjcsMi42MQoJYzAuMDgsMC4zNiwwLjUzLDEuNzUsMC44NCwyLjY1YzEuMjEtMi40MSw0LjUzLTMuNzcsNi4wNC01Ljc4YzAuMzUsMi40Ny0xLjQ3LDQuODItMi44Miw2LjRjLTAuMzIsMC4zNi0wLjY3LDAuNzItMS4wNywxLjExCgljLTIuNTUsMi41LTQuMjMsNC4yMS01LjEyLDUuODFjLTAuMjMsMC4zNS0wLjYsMS4xNS0wLjc4LDEuNzZjLTAuMjYsMC43Ni0wLjU5LDIuMDYtMC44Nyw0LjM0Yy0wLjIxLDEuMzUtMC40NSwyLjk1LTAuNTMsMy42NwoJYy0wLjE3LDEuNjMtMC42NSw0LjIyLTIuNjEsNC45NmMtMC4xMSwwLjA1LTAuMjEsMC4wNy0wLjMyLDAuMDl2MC4wMWMtMS44NywwLjQyLTMuNzgtMS4xOC01LjE3LTQuMDYKCWMtMC4yOSwwLjIyLTAuNiwwLjQyLTAuOTQsMC41N2MxLjg4LDQuNTUsNC43MSw2LjY0LDcuMTksNi42NGMxLjg4LDAsMy4zNy0wLjk3LDMuODQtMy43OWMwLjI1LTEuNDIsMC40Mi0zLDAuNTgtNC41MwoJYzAuMDgtMC43NCwwLjQzLTQuOSwxLjA5LTYuNDFjMC44MS0xLjY5LDIuNTgtMy4zMyw1LjIyLTYuMTFjMS42My0xLjczLDIuNTItMy4xNiwyLjk4LTQuMzJjMS41NC0yLjg4LTAuMzctOS43Mi0wLjc0LTEwLjk1CgljLTAuMDEtMC4wNC0wLjAyLTAuMDUtMC4wNC0wLjA1Yy0wLjA0LDAtMC4wNSwwLjAxLTAuMDgsMC4wNmwtMC4wMSwwLjAzYy0wLjY4LDEuMTMtMS44OSwyLjE3LTMuMDIsMy4wMQoJYzAuNjMtMS43OCwwLjQ2LTMuMTQsMC4yMS00LjI4di0wLjAxYy0wLjAyLTAuMDctMC4wMy0wLjEzLTAuMDUtMC4ybDAsMC4wMWMtMS4xNC00LjU0LTUuNjktOC41OC03LjczLTEwLjkxCgljLTIuNjYtMy4wMi0xLjc2LTQuOTYtMC43Ny02LjJjMC4xOCwwLjI4LDAuMzcsMC41NywwLjU5LDAuODdjMy42Miw1LjAyLDEwLjQ0LDEyLjk4LDE0LjAyLDIwLjU3YzAuOTEsMS45MSwxLjYsMy44LDEuOTgsNS41OQoJYzEuNDEsNy44Ni0zLjk2LDE1Ljg0LTEyLDEzLjZoMGMtMC4wNS0wLjAxLTAuMTEtMC4wMy0wLjE2LTAuMDVjLTAuMjIsMC43LTAuNDIsMS44MS0wLjYzLDMuMzNjMS4yMiwwLjUzLDIuNTQsMC44NSwzLjgyLDAuOWwwLDAKCWMwLjA5LDAsMC4xOSwwLDAuMjgsMC4wMWM2LjYxLDAuMDcsMTEuNzgtNC45OCwxMC44My0xNS42YzAsMC0wLjQtNC40Mi0yLjYzLTkuMDZjLTMuNTgtOC4xNy0xMC4xOS0xNi4yNS0xNC4yNS0yMS40NwoJYy0xLjI5LTEuNjYtMi4wNS0zLjA5LTIuNDMtNC4zM2MtMC43Ni0yLjQxLTAuMjgtNC4yOCwwLjctNS4xYzAuMjEtMC4xOCwwLjQ3LTAuMzgsMC43MS0wLjVjMC4xNS0wLjA4LDAuMDktMC4yNS0wLjAxLTAuMjcKCWMtMC4wMiwwLTAuMDUtMC4wMS0wLjA5LTAuMDFDODMuMTYtMC4wNSw4Mi44OCwwLjAxLDgyLjMyLDAuNDIgTTc3LjQzLDE0LjYzYy0xLjA4LDAuMDMtMS45MiwwLjk2LTEuODksMi4wNgoJYzAuMDMsMS4xMSwwLjkzLDEuOTgsMi4wMSwxLjk1YzAuNTktMC4wMiwxLjEtMC4zMSwxLjQ1LTAuNzNsMC4wNC0wLjA1YzAuMjMsMS42LTAuNTIsMi44Ny0yLjI1LDQuMzQKCWMtMS43OCwxLjUzLTUuOTMsMy41My04Ljg4LDUuOTJjLTQuMTYsMy4zNy01LjE0LDcuMDMtNS4zOSwxMGMtMC4xMSwxLjMyLDAuMDgsMy4wNiwwLjQzLDQuNWMwLjQ0LDEuODEsMS4wOCwzLjIsMS4wOCwzLjIKCXMwLjAzLDAuMDYsMC4wOCwwLjE2Yy0wLjExLDEuOTYsMC4wOSw1LjM5LDEuMTcsNy45OGMxLjQ1LDMuMzQsNC4wNiw2LjA3LDcuODEsNS4yN2MzLjc4LTAuOTEsNC4yLTcuMiw0LjYzLTExLjc5CgljMC4xMS0wLjc1LDAuMjMtMC44OSwwLjQ1LTEuMDhjMC42MS0wLjUzLDIuMDgtMS45NCwyLjc4LTIuNTdjMC40My0wLjM5LDAuODEtMC43OCwxLjA2LTEuMjhjMC4zMS0wLjYxLDAuMTUtMS40MiwwLjE1LTEuNDIKCWwtMC40Mi0zLjAzYy0wLjExLDAuNDMtMC42MiwxLjAzLTEuMzQsMS43OGMtMC43NSwwLjc4LTIuNzYsMi41NC0yLjk0LDIuNzNjLTAuMTgsMC4xOS0wLjgzLDAuNjctMS4xMSwyLjk4CgljLTAuNzIsNi4yOC0xLjkzLDkuMjUtNC4xLDEwLjI1Yy0wLjU3LDAuMjgtMS4yMSwwLjQxLTEuOTMsMC40MmMtMy45OC0wLjA0LTUuMDItNS01LjAxLTcuNzJjMC0wLjE2LDAuMDEtMC4zMiwwLjAyLTAuNDcKCWMwLjkyLDEuMjcsMi4yOSwyLjU0LDMuOTcsMi4yN2MyLjY5LTAuNDIsMS44NS01LjA2LDEuNDYtNi4xM2MtMC4zOC0xLjA4LTEuNDItNC4zMS0zLjY3LTQuMTVjLTEuNiwwLjExLTIuMzQsMi4wMi0yLjY4LDMuNjUKCWMtMC4zMS0xLjI4LTAuNDctMi43OC0wLjM3LTMuOTZjMC4yNC0yLjgsMS4xOC02LjMxLDUuMTYtOS43NmMyLjg0LTIuNDYsNi4wNi00LjIxLDcuODUtNS42NmMxLjE0LTAuOTIsMS44NS0xLjk1LDIuMjQtMi45MQoJYy0wLjExLDAuOTQtMC4zNCwxLjk1LTAuNzgsMy4xM2MtMS42NSw0LjQ1LTYuNjcsMTEuODEtNi43NCwyMi4yYzAsMy4xOSwwLjI5LDUuOTYsMC43OSw4LjMyYzAuMjctMC4xOSwwLjUzLTAuNDQsMC43Ny0wLjc0CgljLTAuMzUtMS42OS0wLjU1LTMuNTYtMC41NS01LjU1YzAtMTAuMzcsNC45OC0xNy43MSw2LjYxLTIyLjE1YzAuODUtMi4zNCwwLjg3LTQuMDUsMC44Ny01LjczYzAtMi4wNy0wLjQ1LTQuMjItMC44Ny01LjA3CgljLTAuNDUtMC44MS0xLjAyLTEuMTYtMS44Ni0xLjE2SDc3LjQzeiBNNjUuNjIsNDYuMThjMC4zMS0xLDAuODYtMS44OSwxLjgzLTIuNDVjMS41OS0wLjc2LDIuMjEsMS4xOCwyLjIxLDEuMTgKCWMtMC4xMSwxLjMxLTEuMDksMi0yLjE3LDJDNjYuODUsNDYuOTIsNjYuMTcsNDYuNjcsNjUuNjIsNDYuMTggTTg2LjU3LDI5Ljg1Yy0wLjE5LDAuMjEtMS4wOCwxLjIxLTEuOTQsMi4xNwoJYy0wLjc3LDAuODYtMS41LDEuNjgtMS42NiwxLjg2Yy0wLjM3LDAuNDItMC41NiwwLjgzLTAuNTEsMS4wNWwwLjIyLDEuMTJjMC4wNi0wLjIxLDAuMjktMC41OSwwLjU1LTAuODgKCWMwLjE4LTAuMjEsMS4wOC0xLjIyLDEuOTQtMi4xN2MwLjc2LTAuODYsMS41LTEuNjgsMS42Ni0xLjg3YzAuMzctMC40MSwwLjU2LTAuODIsMC41MS0xLjA0bC0wLjIzLTEuMTMKCUM4Ny4wNiwyOS4xOCw4Ni44MywyOS41NSw4Ni41NywyOS44NSBNNzEuMTEsMzEuNTJjMCwwLTEuNTcsMS4xNC0yLjIsMi42NWMtMC4zOSwwLjkyLTAuMzYsMS45Mi0wLjE0LDIuNDEKCWMwLjIyLDAuNDgsMC43NSwwLjk0LDEuNDMsMC4zOWMwLjQ4LTAuMzksMC42OS0wLjkzLDAuNzktMS40YzAuMDYtMC4yOCwwLjA5LTAuNDUsMC4wOS0wLjU5YzAtMC4xNy0wLjA2LTAuMzEtMC4yMS0wLjI3CgljLTAuNDUsMC4xNS0wLjE4LDAuNzgtMC41MSwxLjA4Yy0wLjI1LDAuMTUtMC44OSwwLjA3LTEuMDEtMC41OGMtMC4xMi0wLjY1LDAuMzYtMS40OCwwLjgtMi4wM2MwLjQ0LTAuNTUsMS4yMi0xLjI3LDEuMjItMS4yNwoJczAuNTUtMC40NywwLjM3LTAuN2MtMC4wMS0wLjAxLTAuMDMtMC4wMi0wLjA1LTAuMDJDNzEuNTEsMzEuMiw3MS4xMSwzMS41Miw3MS4xMSwzMS41MiBNODMuMjUsNDMuNTlsMi41MiwxLjIxbDEuMzktMy4wMwoJbC0yLjUxLTEuMjFMODMuMjUsNDMuNTl6IE03OC40OCw0Ni44M2MxLjA2LDIuNTUsMi42OCw0Ljc2LDQuNTMsNi4zOGMwLjE5LTEuMzMsMC40LTIuMjcsMC42LTIuOTRjLTEuODktMS4zOC0zLjI0LTIuODgtNC4xMS00LjM4CglMNzguNDgsNDYuODN6IE05MS41LDQ4Ljk2bDIuNTEsMS4yM2wxLjM5LTMuMDNsLTIuNTEtMS4yMUw5MS41LDQ4Ljk2eiBNNzcuODIsNTUuM2wyLjE0LDEuODFsMi4wOS0yLjU2bC0yLjE0LTEuODJMNzcuODIsNTUuM3oKCSBNNzcuMzUsNTkuODFsMi4xNCwxLjgxbDIuMDgtMi41OGwtMi4xNC0xLjgyTDc3LjM1LDU5LjgxeiBNODcuNDIsNTcuOWMtMC4xLDAuMDUtMC4xMywwLjIxLTAuMDcsMC40NWMwLjA3LDAuMjIsMC40NCwxLjIsMC40NCwxLjIKCWMwLjI2LDAuNzQsMC43MSwxLjU5LDEuMzEsMi4wMmMwLjY0LDAuNDYsMC45NywwLjMsMS4xLDAuMjVjMC4wOS0wLjA1LDAuNTEtMC4zMSwwLjM2LTAuOThjLTAuMTYtMC43MS0wLjI0LTAuOS0wLjM3LTEuMTYKCWMtMC4xMy0wLjI2LTAuMy0wLjQyLTAuNC0wLjM4Yy0wLjA2LDAuMDEtMC4wMSwwLjI0LTAuMDEsMC4zOWMtMC4wMSwwLjI2LTAuMDksMC40NS0wLjMsMC41NWMtMC4xOSwwLjA4LTAuNjUsMC4yNS0xLTAuMzkKCWMtMC4yOS0wLjUyLTAuNTUtMS4yLTAuNjUtMS40OGMtMC4wOS0wLjIyLTAuMjItMC40OC0wLjM2LTAuNDhDODcuNDYsNTcuODksODcuNDUsNTcuOSw4Ny40Miw1Ny45Ii8+Cjwvc3ZnPgo=' /></a>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<p><span>© 2026 Al Jazeera Media Network. All rights reserved.</span></p>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t\t\t</div>\n\t\t\t</div>\n\t\t</div>\n\t\t<script type=\"speculationrules\">\n{\"prefetch\":[{\"source\":\"document\",\"where\":{\"and\":[{\"href_matches\":\"\\/en\\/*\"},{\"not\":{\"href_matches\":[\"\\/wp-*.php\",\"\\/wp-admin\\/*\",\"\\/wp-content\\/uploads\\/*\",\"\\/wp-content\\/*\",\"\\/wp-content\\/plugins\\/*\",\"\\/resources\\/themes\\/ajmn-liberties-v2\\/*\",\"\\/en\\/*\\\\?(.+)\"]}},{\"not\":{\"selector_matches\":\"a[rel~=\\\"nofollow\\\"]\"}},{\"not\":{\"selector_matches\":\".no-prefetch, .no-prefetch a\"}}]},\"eagerness\":\"conservative\"}]}\n</script>\n<link rel='stylesheet' id='ajmn-fonts-style-css' href='https://liberties.aljazeera.com/site-modules/ajwa-fonts//fonts-v2.css' type='text/css' media='all' />\n<script type=\"text/javascript\" id=\"theme-main-js-js-extra\">\n/* <![CDATA[ */\nvar ThemeGlobals = {\"lang\":\"en\",\"is_rtl\":\"\"};\n/* ]]> */\n</script>\n<script type=\"text/javascript\" src=\"https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/assets/js/main.js\" id=\"theme-main-js-js\"></script>\n<script type=\"text/javascript\" src=\"https://liberties.aljazeera.com/resources/themes/ajmn-liberties-v2/inc/assets/slick/slick.min.js\" id=\"slick-js-js\"></script>\n<script type=\"text/javascript\" src=\"https://liberties.aljazeera.com/site-modules/ajwa-fonts//script.js\" id=\"ajmn-fonts-script-js\"></script>\n\n<!-- ************************************************* -->\n<!-- OneTrust Cookies Consent Notice start for liberties.aljazeera.com -->\r\n<script type=\"text/javascript\" src=\"https://cdn.cookielaw.org/consent/bd73ded9-38f0-4e5e-ac8b-f38b41449f9f/OtAutoBlock.js\"></script>\r\n<script src=\"https://cdn.cookielaw.org/scripttemplates/otSDKStub.js\" data-document-language=\"true\" type=\"text/javascript\" charset=\"UTF-8\" data-domain-script=\"bd73ded9-38f0-4e5e-ac8b-f38b41449f9f\"></script>\r\n<script type=\"text/javascript\">\r\nfunction OptanonWrapper() { }\r\n</script>\r\n<!-- OneTrust Cookies Consent Notice end for liberties.aljazeera.com -->\n<!-- ************************************************* -->\n\t</body>\n</html>")