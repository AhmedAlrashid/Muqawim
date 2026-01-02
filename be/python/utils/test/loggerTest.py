import sys
import os
from pathlib import Path

# Add the parent of parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import myGetLogger, log_warning, log_success, get_urlhash, normalize
import unittest
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import os


class TestLoggerUtils(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test logs
        self.temp_dir = tempfile.mkdtemp()
        self.test_logs_dir = Path(self.temp_dir) / "test_logs"
        self.test_logs_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch.dict(os.environ, {'LOGS_DIR': ''})
    def test_myGetLogger_creates_logger(self):
        """Test that myGetLogger creates a logger with proper configuration."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            # Check logger is created
            self.assertIsInstance(logger, logging.Logger)
            self.assertEqual(logger.level, logging.DEBUG)
            
            # Check handlers are added
            self.assertGreater(len(logger.handlers), 0)
            
    def test_log_warning_structure(self):
        """Test that log_warning creates properly structured warning messages."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            # Capture log output
            with self.assertLogs(logger, level='WARNING') as cm:
                log_warning(logger, "https://example.com/broken", 404, "Page not found", retries=2)
            
            # Check the log message structure
            log_output = cm.output[0]
            self.assertIn("Scrape warning: Page not found", log_output)
            self.assertIn("https://example.com/broken", log_output)
            self.assertIn("404", log_output)
            self.assertIn("retries", log_output)
            
    def test_log_success_structure(self):
        """Test that log_success creates properly structured success messages."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            # Capture log output
            with self.assertLogs(logger, level='INFO') as cm:
                log_success(logger, "https://example.com/page", items_scraped=25, duration_sec=1.234)
            
            # Check the log message structure
            log_output = cm.output[0]
            self.assertIn("Scrape success", log_output)
            self.assertIn("https://example.com/page", log_output)
            self.assertIn("items_scraped", log_output)
            self.assertIn("25", log_output)
            self.assertIn("duration_sec", log_output)
            self.assertIn("1.234", log_output)
            
    def test_log_success_with_extras(self):
        """Test log_success with extra parameters."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            with self.assertLogs(logger, level='INFO') as cm:
                log_success(logger, "https://example.com", items_scraped=10, 
                          user_agent="test-bot", response_size="1024")
            
            log_output = cm.output[0]
            self.assertIn("user_agent", log_output)
            self.assertIn("test-bot", log_output)
            self.assertIn("response_size", log_output)
            
    def test_log_warning_with_extras(self):
        """Test log_warning with extra parameters."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            with self.assertLogs(logger, level='WARNING') as cm:
                log_warning(logger, "https://example.com/timeout", 500, 
                          "Server error", retries=3, timeout=30)
            
            log_output = cm.output[0]
            self.assertIn("retries", log_output)
            self.assertIn("3", log_output)
            self.assertIn("timeout", log_output)
            self.assertIn("30", log_output)
            
    def test_get_urlhash(self):
        """Test URL hash generation."""
        # Test basic URL
        url1 = "https://example.com/page"
        hash1 = get_urlhash(url1)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length
        
        # Test same URL gives same hash
        hash2 = get_urlhash(url1)
        self.assertEqual(hash1, hash2)
        
        # Test different URLs give different hashes
        url2 = "https://example.com/different-page"
        hash3 = get_urlhash(url2)
        self.assertNotEqual(hash1, hash3)
        
        # Test URL with query params
        url3 = "https://example.com/page?param=value"
        hash4 = get_urlhash(url3)
        self.assertNotEqual(hash1, hash4)
        
    def test_normalize(self):
        """Test URL normalization."""
        # Test trailing slash removal
        self.assertEqual(normalize("https://example.com/"), "https://example.com")
        self.assertEqual(normalize("https://example.com/page/"), "https://example.com/page")
        
        # Test URLs without trailing slash remain unchanged
        self.assertEqual(normalize("https://example.com"), "https://example.com")
        self.assertEqual(normalize("https://example.com/page"), "https://example.com/page")
        
        # Test multiple trailing slashes
        self.assertEqual(normalize("https://example.com///"), "https://example.com")
        
        # Test empty string
        self.assertEqual(normalize(""), "")
        
    def test_log_success_without_duration(self):
        """Test log_success without duration parameter."""
        with patch('utils.logs_dir', self.test_logs_dir):
            logger = myGetLogger()
            
            with self.assertLogs(logger, level='INFO') as cm:
                log_success(logger, "https://example.com", items_scraped=5)
            
            log_output = cm.output[0]
            self.assertIn("items_scraped", log_output)
            self.assertIn("5", log_output)
            # Duration should not be in output when not provided
            self.assertNotIn("duration_sec", log_output)


if __name__ == "__main__":
    unittest.main()