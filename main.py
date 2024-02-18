from Scraper import Scraper
from dotenv import load_dotenv

import time
import os

if __name__ == '__main__':
    """ Main Method, runs continuously """
    load_dotenv()
    waiting_time = int(os.getenv('SCRAPING_TIME_INTERVAL'))
    scraper = Scraper()
    # Wait the flask_container up
    time.sleep(13)
    while True:
        scraper.post_quake_data()
        time.sleep(waiting_time)
