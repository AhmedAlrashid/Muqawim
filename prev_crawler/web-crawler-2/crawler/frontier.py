import os
import shelve

from threading import Thread, RLock, Lock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = list()
        
        # Hybrid approach: RAM cache + periodic shelve flushes
        self.ram_cache = {}  # Fast dict for immediate operations
        self.cache_lock = Lock()  # Thread safety for cache operations
        self.flush_threshold = 50000  # Flush to shelve every 50k URLs (roughly 10-15MB)
        self.cache_count = 0
        
        # Initialize shelve for persistence
        if not os.path.exists(self.config.save_file) and not restart:
            self.logger.info(f"Did not find save file {self.config.save_file}, starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            self.logger.info(f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)
        
        # Load existing data from shelve into RAM cache
        self.save = shelve.open(self.config.save_file)
        self._load_from_shelve()
        
        if restart or not self.ram_cache:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()
            if not self.ram_cache:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _load_from_shelve(self):
        """Load existing URLs from shelve into RAM cache on startup"""
        try:
            self.ram_cache = dict(self.save)  # Load all shelve data into RAM
            self.cache_count = len(self.ram_cache)
            self.logger.info(f"Loaded {self.cache_count} URLs from shelve into RAM cache")
        except Exception as e:
            self.logger.warning(f"Error loading from shelve: {e}")
            self.ram_cache = {}
            self.cache_count = 0

    def _flush_to_shelve(self):
        """Flush RAM cache to shelve and clear cache"""
        with self.cache_lock:
            try:
                # Update shelve with all RAM cache data
                self.save.update(self.ram_cache)
                self.save.sync()  # Force write to disk
                
                flushed_count = self.cache_count
                self.ram_cache.clear()
                self.cache_count = 0
                
                self.logger.info(f"Flushed {flushed_count} URLs to shelve, RAM cache cleared")
            except Exception as e:
                self.logger.error(f"Error flushing to shelve: {e}")

    def _check_and_flush(self):
        """Check if cache is full and flush if needed"""
        if self.cache_count >= self.flush_threshold:
            self.logger.info(f"RAM cache hit {self.flush_threshold} URLs, flushing to shelve...")
            self._flush_to_shelve()

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.ram_cache)
        tbd_count = 0
        for url, completed in self.ram_cache.values():
            if not completed and is_valid(url):
                self.to_be_downloaded.append(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")

    def get_tbd_url(self):
        try:
            return self.to_be_downloaded.pop()
        except IndexError:
            return None

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)
        with self.cache_lock:
            # Only check RAM cache to avoid SQLite threading issues
            # URLs in shelve are already loaded into RAM cache on startup
            if urlhash not in self.ram_cache:
                self.ram_cache[urlhash] = (url, False)
                self.cache_count += 1
                self.to_be_downloaded.append(url)
                
                # Check if we need to flush to shelve
                self._check_and_flush()
    
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        with self.cache_lock:
            # Only check RAM cache to avoid SQLite threading issues
            if urlhash not in self.ram_cache:
                # This should not happen.
                self.logger.error(
                    f"Completed url {url}, but have not seen it before.")
                # Add to cache anyway
                self.ram_cache[urlhash] = (url, True)
                self.cache_count += 1
            else:
                # Mark as complete in RAM cache
                url_data = self.ram_cache[urlhash]
                self.ram_cache[urlhash] = (url_data[0], True)
            
            # Check if we need to flush to shelve
            self._check_and_flush()

    def cleanup(self):
        """Final cleanup - flush any remaining RAM cache to shelve"""
        if self.cache_count > 0:
            self.logger.info(f"Final cleanup: flushing {self.cache_count} URLs to shelve")
            self._flush_to_shelve()
        self.save.close()
