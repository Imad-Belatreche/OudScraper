from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

from config import MAX_WORKERS
from scraper import FILE_PATH, TARGET_URL, scrap_page
from utils import get_existing_ids, get_last_page, setup_driver


def main():
    start_time = time.time()
    driver = setup_driver()
    try:
        driver.get(TARGET_URL)
        last_page = get_last_page(driver)
        print(f"Found {last_page} to scrap !")
    except Exception as e:
        print(f"[x] Error extracting the last page: {e}")
    finally:
        driver.quit()

    total_count = 0
    shared_ids = get_existing_ids(FILE_PATH)
    print(f"[!] Fetched {len(shared_ids)} element from {FILE_PATH}")
    ids_lock = Lock()
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as excutor:
            future_to_page = {
                excutor.submit(scrap_page, page_num, shared_ids, ids_lock): page_num
                for page_num in range(1, last_page + 1)
            }
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    saved_count = future.result()
                    if saved_count:
                        print(
                            f"Finished scraping data from page {page}, found {saved_count} new listing"
                        )
                        total_count += saved_count
                except Exception as e:
                    print(f"[x] Page {page} generated an error: {e.with_traceback}")
    except KeyboardInterrupt:
        print(
            "\n[!] Keyboard interrupt received, shutting down workers. Please wait..."
        )
    finally:
        excutor.shutdown(wait=True, cancel_futures=True)
        end_time = time.time()
        print(f"Total scraping time: {(end_time - start_time):.2f} seconds")
        print(f"Total extracted listings {total_count} ")


if __name__ == "__main__":
    main()
