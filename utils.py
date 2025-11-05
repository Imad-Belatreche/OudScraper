import os
import re
import sys
import termios
import tty
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pandas.errors import EmptyDataError

# from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service


def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("permissions.default.image", 2)

    service = Service(executable_path="./geckodriver")
    driver = webdriver.Firefox(service=service, options=options)
    return driver


# 3 functions to safly extract needed text
def safe_find_text(element: WebElement, selector, default=None):
    try:
        found_element = element.find_element(By.CSS_SELECTOR, selector)
        return found_element.text.strip()
    except Exception:
        return default


def safe_find_attribute(element: WebElement, selector, attribute, default=None):
    try:
        found_element = element.find_element(By.CSS_SELECTOR, selector)
        return found_element.get_attribute(attribute)
    except Exception:
        return default


def safe_find_list_text(element: WebElement, selector, default=[]):
    try:
        found_elements = element.find_elements(By.CSS_SELECTOR, selector)
        return [elm.text.strip() for elm in found_elements]
    except Exception:
        return default


# Extract existing
def get_existing_ids(file_path):
    """Extract already existing data from the .csv file"""
    existing_ids = set()
    try:
        df = pd.read_csv(file_path, usecols=["id"], dtype={"id": str}, encoding="utf-8")
        existing_ids = set(df["id"])
    except FileNotFoundError or EmptyDataError:
        pass  # File doesn't exist yet, so no IDs to load
    except Exception as e:
        print(f"[@] Weird exception on getting existing ids: {e}")
        pass
    return existing_ids


# def check_dupli(data_frame: pd.DataFrame):
#     existing_ids = get_existing_ids()
#     if "id" in data_frame.columns:
#         data_frame["id"] = data_frame["id"].astype(str)
#         org_count = len(data_frame)
#         data_frame = data_frame[~data_frame["id"].isin(existing_ids)]


def save_into_file(file_path, data, fields=[]):
    """
    Save data to a file, append if the file exists and has content and avoid duplicates
    """
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

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            existing_ids = get_existing_ids(file_path)
            df_new = df_new[~df_new["id"].isin(existing_ids)]
            new_count = len(df_new)

            if new_count > 0:
                df_new.to_csv(
                    file_path, mode="a", header=False, index=False, encoding="utf-8"
                )
                print(f"Successfully appended {new_count} records to {file_path}")
            else:
                print("No new records to save.")
        else:
            df_new.to_csv(
                file_path, mode="w", header=True, index=False, encoding="utf-8"
            )
            print(f"Successfully wrote {len(df_new)} new records to {file_path}")

    except Exception as e:
        print(f"Error saving to file: {e}")


def save_data(file_path, data, fields, lock=None):
    try:
        if lock:
            with lock:
                save_into_file(file_path, data, fields)
        else:
            save_into_file(file_path, data, fields)
    except Exception as e:
        print(f"An error occurred during save: {e}")


def get_last_page(driver: webdriver.Firefox):
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


# TODO: May use it later for a more interactive session
def get_key():
    """Read a keyboard press from the terminal."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
