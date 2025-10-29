import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils import (
    get_existing_ids,
    get_last_page,
    safe_find_attribute,
    safe_find_list_text,
    safe_find_text,
    save_into_file,
)
from vertical_scroll import scroll_page

TARGET_URL = "https://www.ouedkniss.com/automobiles_vehicules/"
FILE_PATH = "./cars_file.csv"
NUMBER_SCROLL_MULTIP = 2.5
SCROLL_PAUSE_TIME = 1
MAX_NO_CHANGE = 2


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("permissions.default.image", 2)
    driver = webdriver.Firefox(options=options)
    return driver


def scrap_visible_data(driver: webdriver.Firefox, existed_ids=set()):
    """
    Scrap only currently visible data
    """
    data = []
    visible_ids = set()

    try:
        listings = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (
                    By.CSS_SELECTOR,
                    "div[class*='v-col-sm-6 v-col-md-4 v-col-lg-3 v-col-12']",
                ),
            )
        )
    except Exception:
        print("No listings were loaded at all!")
        listings = []

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
            print(f"Fetched listing >> {id} : {title} ")
        except Exception as e:
            print(f"Something happened when scraping listing: {e}")
            continue

    return data, visible_ids


def scroll_and_scrap(driver: webdriver.Firefox):
    """
    Scroll and catch them data on the go, leaving nothing behind except for ads LoL !
    """
    all_data = []
    all_ids = set()

    all_ids.update(get_existing_ids(FILE_PATH))

    print("Starting the scroll & scrap ........")
    driver.execute_script("window.scrollTo(0,0)")
    time.sleep(1)

    # Getting the first view data
    initial_data, initial_ids = scrap_visible_data(driver, all_ids)
    if initial_data:
        all_data.extend(initial_data)
        all_ids.update(initial_ids)
        print(f"Initial load: {len(initial_ids) + len(all_ids)}")
    else:
        print("No new initial data ...")

    iter = 1
    no_change_counter = 0
    while True:
        current_height = driver.execute_script("return window.scrollY")

        print(f"Scroll iteration attempt {iter}...")
        scroll_page(driver, NUMBER_SCROLL_MULTIP)
        time.sleep(SCROLL_PAUSE_TIME)

        # Get the new data after scrolling
        new_data, new_ids = scrap_visible_data(driver, all_ids)
        true_data = [data for data in new_data if data.get("id") not in all_ids]

        if true_data:
            all_data.extend(true_data)
            new_ids_set = {item["id"] for item in true_data}
            all_ids.update(new_ids_set)

            print(
                f"New data added! {len(true_data)} listing. (Total is {len(all_data)})"
            )
        else:
            print("No new listings found !")

        new_height = driver.execute_script("return window.scrollY")

        if new_height == current_height:
            print(f"Page height has not changed. Counter: {no_change_counter}")
            no_change_counter += 1
        else:
            no_change_counter = 0

        if no_change_counter >= MAX_NO_CHANGE:
            print("Reached bottom of page (height stopped changing for 3 attempts).")
            break
        iter += 1

    return all_data


def scrap_page():
    driver = setup_driver()

    try:
        driver.get(TARGET_URL)
        last_page = get_last_page(driver)
        print(f"Found {last_page} pages to scrape.")

        for i in range(1, last_page + 1):
            print(
                f"\n================================ Scraping page {i} ================================"
            )
            try:
                if i > 1:
                    driver.get(TARGET_URL + str(i))

                new_data = scroll_and_scrap(driver)
                if new_data:
                    fields = list(new_data[0].keys())
                    save_into_file(FILE_PATH, new_data, fields)

            except KeyboardInterrupt:
                print("\n[!] Keyboard interrupt detected. Exiting gracefully...")
                break
            except Exception as e:
                print(f"[x] Error scraping page {i}: {e}")
                with open("debug_page.html", "w", encoding="utf-8") as file:
                    file.write(driver.page_source)
                print("Debug file saved as 'debug_page.html'")
                continue

    except Exception as e:
        print(f"[x] An unexpected error occurred: {e}")
    finally:
        print("********* Exiting *********")
        driver.quit()


if __name__ == "__main__":
    scrap_page()
