import re


class Config(object):
    def __init__(self, config):
        # Simple user agent for direct downloads
        self.user_agent = "Python Web Crawler"
        self.threads_count = int(config["LOCAL PROPERTIES"]["THREADCOUNT"])
        self.save_file = config["LOCAL PROPERTIES"]["SAVE"]

        self.seed_urls = config["CRAWLER"]["SEEDURL"].split(",")
        self.time_delay = float(config["CRAWLER"]["POLITENESS"])

        # No cache server needed for direct downloads
        self.cache_server = None
