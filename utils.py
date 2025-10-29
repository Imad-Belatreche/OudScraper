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


def get_existing_ids(file_path):
    existing_ids = set()
    try:
        df = pd.read_csv(file_path, usecols=["id"], encoding="utf-8")
        existing_ids = set(df["id"].astype(str))
    except FileNotFoundError:
        pass  # File doesn't exist yet, so no IDs to load
    return existing_ids


def save_into_file(file_path, data, fields=[]):
    """
    Save data to a file, append if the file exists and has content.
    """
    if not data:
        return

    try:
        # Ensure DataFrame columns are in the correct order
        df_new = pd.DataFrame(data, columns=fields)

        # File exists and is not empty, append without header
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            df_new.to_csv(
                file_path, mode="a", header=False, index=False, encoding="utf-8"
            )
            print(f"Successfully appended {len(df_new)} records to {file_path}")
        # File does not exist or is empty, write with header
        else:
            df_new.to_csv(
                file_path, mode="w", header=True, index=False, encoding="utf-8"
            )
            print(f"Successfully wrote {len(df_new)} new records to {file_path}")

    except Exception as e:
        print(f"Error saving to file: {e}")


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
