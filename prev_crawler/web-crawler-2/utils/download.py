import requests
from utils.response import Response
import pickle

class MockRawResponse:
    """Mock response object that matches what scraper expects"""
    def __init__(self, content, url):
        self.content = content.encode('utf-8')  # scraper expects bytes
        self.url = url

def download(url, config, logger=None):
    try:
        resp = requests.get(url, headers={'User-Agent': config.user_agent})
        
        # Create a mock raw_response object that matches what scraper expects
        raw_response = MockRawResponse(resp.text, str(resp.url))
        
        return Response({
            'response': pickle.dumps(raw_response),  # Response expects pickled data
            'status': resp.status_code,
            'url': str(resp.url)
        })
    except Exception as e:
        if logger:
            logger.error(f"Direct request error: {e}")
        return Response({'error': str(e), 'status': 0, 'url': url})