import csv
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
    safe_find_attribute,
    safe_find_list_text,
    safe_find_text,
)

TARGET_URL = "https://www.ouedkniss.com/automobiles_vehicules/"
FILE_NAME = "cars_file.csv"


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    driver = webdriver.Firefox(options=options)
    return driver


def scroll_page(driver: webdriver.Firefox, pixels_to_scroll: int):
    driver.execute_script(f"window.scrollBy(0, {pixels_to_scroll})")


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
        listings = []

    for listing in listings:
        try:
            title = safe_find_text(listing, "h3[class*='announ-card-title']")
            if title == "Not Found":
                continue

            id = safe_find_attribute(
                listing, ".v-col-sm-6.v-col-md-4.v-col-lg-3.v-col-12 > div", "id"
            )
            if id in visible_ids or id in existed_ids:
                continue
            visible_ids.add(id)

            city = safe_find_text(listing, "span[class*='city']")
            price = safe_find_text(listing, "span.price", None)
            link = safe_find_attribute(listing, "a[class*='link']", "href")
            specifications = safe_find_list_text(listing, "span[class*='v-chip']", None)

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
            print(list(listing_data.values()))
        except Exception as e:
            print(f"Something happened when scraping listing: {e}")
            continue
    return data, visible_ids


def scroll_and_scrap(driver: webdriver.Firefox):
    """
    Scroll and catch them data on the go, leaving nothing behind
    """
    all_data = []
    all_ids = set()
    scroll_pause = 1
    scroll_pixels = 1000

    all_ids.update(get_existing_ids(f"./{FILE_NAME}"))

    print("Starting the scroll & scrap ........")
    driver.execute_script("window.scrollTo(0,0)")
    time.sleep(1)

    # Getting the initial data
    initial_data, initial_ids = scrap_visible_data(driver, all_ids)
    print(f"Initial load: {len(initial_ids) + len(all_ids)}")

    iter = 0
    no_change_counter = 0
    max_no_change = 3
    while True:
        current_height = driver.execute_script("return document.body.scrollHeight")

        print(f"Scroll iteration attempt {iter + 1}...")
        scroll_page(driver, scroll_pixels)
        time.sleep(scroll_pause)
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

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == current_height:
            print(f"Page height has not changed. Counter: {no_change_counter}")
            no_change_counter += 1
        else:
            no_change_counter = 0

        if no_change_counter >= max_no_change:
            print("Reached bottom of page (height stopped changing for 3 attempts).")
            break
        iter += 1

    return all_data


def scrap_page():
    driver = setup_driver()
    data = []

    for i in range(1, 10):
        print(
            f"\n================================ Scraping page {i} ================================"
        )
        try:
            driver.get(url=TARGET_URL + str(i))

            # SCRAP, SCROLL AND LET THE BALL GROW
            data.extend(scroll_and_scrap(driver))

        except Exception as e:
            print(f"[x] Error waiting for elements: {e}")
            with open("debug_page.html", "w", encoding="utf-8") as file:
                file.write(driver.page_source)
            print("Debug file saved as 'debug_page.html'")
            driver.quit()
            sys.exit(1)

    if data:
        with open(FILE_NAME, "a", newline="", encoding="utf-8") as csvfile:
            fields = list(data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            if not get_existing_ids(FILE_NAME):
                writer.writeheader()
            writer.writerows(data)
            print(f"Successfully saved {len(data)} listings to {FILE_NAME}")
    else:
        print("No data was scraped")

    print("********* Exiting *********")
    driver.quit()


if __name__ == "__main__":
    scrap_page()
