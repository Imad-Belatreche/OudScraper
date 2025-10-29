import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def safe_find_text(element: WebElement, selector, default="Not Found"):
    try:
        found_element = element.find_element(By.CSS_SELECTOR, selector)
        return found_element.text.strip()
    except Exception:
        return default


def safe_find_attribute(element: WebElement, selector, attribute, default="Not Found"):
    try:
        found_element = element.find_element(By.CSS_SELECTOR, selector)
        return found_element.get_attribute(attribute)
    except Exception:
        return default


def safe_find_list_text(element: WebElement, selector, default=["No specifications"]):
    try:
        found_elements = element.find_elements(By.CSS_SELECTOR, selector)
        return [elm.text.strip() for elm in found_elements]
    except Exception:
        return default


def get_existing_ids(file_path):
    existing_ids = set()
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if "id" in row:
                    existing_ids.add(row["id"])
    except FileNotFoundError:
        pass  # File doesn't exist yet, so no IDs to load
    return existing_ids
