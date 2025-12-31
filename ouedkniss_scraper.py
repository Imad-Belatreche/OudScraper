import re
import time
from threading import Lock
from typing import Optional, Set

import pandas as pd
from pandas.errors import EmptyDataError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from config import (
    FILE_PATH,
    MAX_NO_CHANGE,
    SCROLL_FACTOR,
    SCROLL_PAUSE_TIME,
    TARGET_URL,
    MAX_WORKERS
)
from vertical_scroll import scroll_page


class OuedknissScraper:
    def __init__(self, file_path: str, target_url: str, max_workers: int):
        self.file_path = file_path
        self.target_url = target_url
        self.max_workers = max_workers
        self.existing_ids = self._get_existing_ids()
        self.ids_lock = Lock()

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("permissions.default.image", 2)

        service = Service(executable_path="./geckodriver")
        driver = webdriver.Firefox(service=service, options=options)
        return driver

    def _get_existing_ids(self):
        existing_ids = set()
        try:
            df = pd.read_csv(self.file_path, usecols=["id"], dtype={"id": str}, encoding="utf-8")
            existing_ids = set(df["id"])
        except FileNotFoundError or EmptyDataError:
            pass
        except Exception as e:
            print(f"[@] Weird exception on getting existing ids: {e}")
            pass
        return existing_ids

    def _safe_find_text(self, element: WebElement, selector, default=None):
        try:
            found_element = element.find_element(By.CSS_SELECTOR, selector)
            return found_element.text.strip()
        except Exception:
            return default

    def _safe_find_attribute(self, element: WebElement, selector, attribute, default=None):
        try:
            found_element = element.find_element(By.CSS_SELECTOR, selector)
            return found_element.get_attribute(attribute)
        except Exception:
            return default

    def _safe_find_list_text(self, element: WebElement, selector, default=[]):
        try:
            found_elements = element.find_elements(By.CSS_SELECTOR, selector)
            return [elm.text.strip() for elm in found_elements]
        except Exception:
            return default

    def _save_into_file(self, data, fields=[]):
        if not data:
            print("[x] Empty data not saved!")
            return

        try:
            df_new = pd.DataFrame(data, columns=fields)
            if df_new.empty:
                print("No data to save.")
                return

            if not fields:
                fields = df_new.columns.tolist()
            df_new.columns = fields

            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                existing_ids = self._get_existing_ids()
                df_new = df_new[~df_new["id"].isin(existing_ids)]
                new_count = len(df_new)

                if new_count > 0:
                    df_new.to_csv(
                        self.file_path, mode="a", header=False, index=False, encoding="utf-8"
                    )
                    print(f"Successfully appended {new_count} records to {self.file_path}")
                else:
                    print("No new records to save.")
            else:
                df_new.to_csv(
                    self.file_path, mode="w", header=True, index=False, encoding="utf-8"
                )
                print(f"Successfully wrote {len(df_new)} new records to {self.file_path}")

        except Exception as e:
            print(f"Error saving to file: {e}")

    def _save_data(self, data, fields):
        try:
            with self.ids_lock:
                self._save_into_file(data, fields)
        except Exception as e:
            print(f"An error occurred during save: {e}")

    def _get_last_page(self, driver: webdriver.Firefox):
        last_page = 1
        try:
            pagination_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".v-pagination__list"))
            )
            pagination_items = pagination_container.find_elements(
                By.CSS_SELECTOR, "li.v-pagination__item"
            )
            page_numbers = []
            for item in pagination_items:
                text = item.text.strip()
                if " " in text:
                    text = re.sub(" ", "", text)
                if text.isdigit():
                    page_numbers.append(int(text))
            if page_numbers:
                last_page = max(page_numbers)
            print(f"The last page is: {last_page}")
        except Exception as e:
            print(f"Could not determine last page number, defaulting to 1. Error: {e}")
        return last_page

    def _scrap_visible_data(self, driver: webdriver.Firefox, existed_ids: Optional[Set[str]] = None):
        if existed_ids is None:
            existed_ids = set()
        data = []
        visible_ids = set()

        try:
            listings = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        "div[class*='v-col-sm-6 v-col-md-4 v-col-lg-3 v-col-12']",
                    ),
                )
            )
        except Exception:
            print("[x] No listings were loaded from the page at all!")
            listings = []
            return data, visible_ids

        for listing in listings:
            try:
                id = self._safe_find_attribute(
                    listing, ".v-col-sm-6.v-col-md-4.v-col-lg-3.v-col-12 > div", "id"
                )
                if id in visible_ids or id in existed_ids:
                    continue
                title = self._safe_find_text(listing, "h3[class*='announ-card-title']")
                if title is None:
                    continue

                city = self._safe_find_text(listing, "span[class*='city']")
                if city is None:
                    continue

                visible_ids.add(id)

                price = self._safe_find_text(listing, "span.price")
                link = self._safe_find_attribute(listing, "a[class*='link']", "href")
                specifications = self._safe_find_list_text(listing, "span[class*='v-chip']")

                if price is not None:
                    price = re.sub("\n", " ", price)

                listing_data = {
                    "id": id,
                    "title": title,
                    "price": price,
                    "specifications": specifications,
                    "city": city,
                    "link": link,
                }
                data.append(listing_data)
            except Exception as e:
                print(f"Something happened when scraping listing: {e}")
                continue

        return data, visible_ids

    def _scroll_and_scrap(self, driver: webdriver.Firefox, known_ids: Optional[Set[str]] = None):
        all_data = []
        if known_ids is None:
            all_ids = set(self._get_existing_ids())
        else:
            all_ids = set(known_ids)

        driver.execute_script("window.scrollTo(0,0)")
        time.sleep(1)

        initial_data, initial_ids = self._scrap_visible_data(driver, all_ids)
        if initial_data:
            all_data.extend(initial_data)
            all_ids.update(initial_ids)

        no_change_counter = 0
        while True:
            current_height = driver.execute_script("return window.scrollY")

            scroll_page(driver, SCROLL_FACTOR)
            time.sleep(SCROLL_PAUSE_TIME)

            new_data, _ = self._scrap_visible_data(driver, all_ids)
            true_data = [data for data in new_data if data.get("id") not in all_ids]

            if true_data:
                all_data.extend(true_data)
                new_ids_set = {item["id"] for item in true_data}
                all_ids.update(new_ids_set)

            new_height = driver.execute_script("return window.scrollY")

            if new_height == current_height:
                no_change_counter += 1
            else:
                no_change_counter = 0

            if no_change_counter >= MAX_NO_CHANGE:
                break

        return all_data

    def scrap_page(self, page_num: int):
        driver = self._setup_driver()
        saved_count = 0
        snapshot_ids: Optional[Set[str]] = None

        with self.ids_lock:
            snapshot_ids = set(self.existing_ids)
        try:
            print(f">> Scraping page number: {page_num}....")
            driver.get(self.target_url + str(page_num) + "?orderBy=CREATED_AT")
            new_data = self._scroll_and_scrap(driver, snapshot_ids)
            if new_data:
                data_to_save = new_data
                filtred_data = []
                with self.ids_lock:
                    for item in new_data:
                        item_id = item.get("id")
                        if not item_id or item_id in self.existing_ids:
                            continue
                        self.existing_ids.add(item_id)
                        filtred_data.append(item)
                    data_to_save = filtred_data
                if data_to_save:
                    fields = list(data_to_save[0].keys())
                    self._save_data(data_to_save, fields)
                    saved_count = len(data_to_save)
        except Exception as e:
            print(f"[x] Error scraping page {page_num}: {e}")

        finally:
            driver.quit()
        print(f"[/] Scraped {saved_count} listing from page {page_num}")
        return saved_count

    def run_scraper(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        start_time = time.time()
        driver = self._setup_driver()
        try:
            driver.get(self.target_url)
            last_page = self._get_last_page(driver)
            print(f"Found {last_page} to scrap !")
        except Exception as e:
            print(f"[x] Error extracting the last page: {e}")
            return # Exit if we can't get the last page
        finally:
            driver.quit()

        total_count = 0
        print(f"[!] Fetched {len(self.existing_ids)} element from {self.file_path}")
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as excutor:
                future_to_page = {
                    excutor.submit(self.scrap_page, page_num): page_num
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
                        print(f"[x] Page {page} generated an error: {e}")
        except KeyboardInterrupt:
            print(
                "\n[!] Keyboard interrupt received, shutting down workers. Please wait..."
            )
        finally:
            excutor.shutdown(wait=True, cancel_futures=True)
            end_time = time.time()
            print(f"Total scraping time: {(end_time - start_time):.2f} seconds")
            print(f"Total extracted listings {total_count} ")
