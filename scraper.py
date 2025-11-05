import re
import time
from threading import Lock
from typing import Optional, Set

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from config import (
    FILE_PATH,
    MAX_NO_CHANGE,
    SCROLL_FACTOR,
    SCROLL_PAUSE_TIME,
    TARGET_URL,
)
from utils import (
    get_existing_ids,
    safe_find_attribute,
    safe_find_list_text,
    safe_find_text,
    save_data,
    setup_driver,
)
from vertical_scroll import scroll_page


def scrap_visible_data(
    driver: webdriver.Firefox, existed_ids: Optional[Set[str]] = None
):
    """
    Scrap only currently visible data
    """
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
            id = safe_find_attribute(
                listing, ".v-col-sm-6.v-col-md-4.v-col-lg-3.v-col-12 > div", "id"
            )
            # To make sure the id doesn't exist already
            if id in visible_ids or id in existed_ids:
                continue
            title = safe_find_text(listing, "h3[class*='announ-card-title']")
            if title is None:
                continue

            city = safe_find_text(listing, "span[class*='city']")
            if city is None:
                continue

            visible_ids.add(id)

            price = safe_find_text(listing, "span.price")
            link = safe_find_attribute(listing, "a[class*='link']", "href")
            specifications = safe_find_list_text(listing, "span[class*='v-chip']")

            # To fix the price format
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
            # print(f"Fetched listing >> {id} : {title} ")
        except Exception as e:
            print(f"Something happened when scraping listing: {e}")
            continue

    return data, visible_ids


def scroll_and_scrap(driver: webdriver.Firefox, known_ids: Optional[Set[str]] = None):
    """
    Scroll and catch them data on the go, leaving nothing behind except for ads LoL !
    """
    all_data = []
    if known_ids is None:
        all_ids = set(get_existing_ids(FILE_PATH))
    else:
        all_ids = set(known_ids)

    driver.execute_script("window.scrollTo(0,0)")
    time.sleep(1)

    # Getting the first view data
    initial_data, initial_ids = scrap_visible_data(driver, all_ids)
    if initial_data:
        all_data.extend(initial_data)
        all_ids.update(initial_ids)

    iter = 1
    no_change_counter = 0
    while True:
        current_height = driver.execute_script("return window.scrollY")

        scroll_page(driver, SCROLL_FACTOR)
        time.sleep(SCROLL_PAUSE_TIME)

        # Get the new data after scrolling
        new_data, _ = scrap_visible_data(driver, all_ids)
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
        iter += 1

    return all_data


def scrap_page(
    page_num: int,
    shared_ids: Optional[Set[str]] = None,
    ids_lock: Optional[Lock] = None,
):
    """Scrap the given page"""

    driver = setup_driver()
    saved_count = 0
    snapshot_ids: Optional[Set[str]] = None

    if shared_ids is not None and ids_lock is not None:
        with ids_lock:
            snapshot_ids = set(shared_ids)
    try:
        print(f">> Scraping page number: {page_num}....")
        driver.get(TARGET_URL + str(page_num) + "?orderBy=CREATED_AT")
        new_data = scroll_and_scrap(driver, snapshot_ids)
        if new_data:
            data_to_save = new_data
            if shared_ids is not None and ids_lock is not None:
                filtred_data = []
                with ids_lock:
                    for item in new_data:
                        item_id = item.get("id")
                        if not item_id or item_id in shared_ids:
                            continue
                        shared_ids.add(item_id)
                        filtred_data.append(item)
                    data_to_save = filtred_data
            if data_to_save:
                fields = list(data_to_save[0].keys())
                save_data(FILE_PATH, data_to_save, fields, ids_lock)
                saved_count = len(data_to_save)
    except Exception as e:
        print(f"[x] Error scraping page {page_num}: {e}")

    finally:
        driver.quit()
    print(f"[/] Scraped {saved_count} listing from page {page_num}")
    return saved_count
