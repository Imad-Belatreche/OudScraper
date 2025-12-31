from ouedkniss_scraper import OuedknissScraper
from config import FILE_PATH, TARGET_URL, MAX_WORKERS
import time


def main():
    start_time = time.time()
    scraper = OuedknissScraper(FILE_PATH, TARGET_URL, MAX_WORKERS)
    scraper.run_scraper()
    end_time = time.time()
    print(f"Total scraping time: {(end_time - start_time):.2f} seconds")


if __name__ == "__main__":
    main()
