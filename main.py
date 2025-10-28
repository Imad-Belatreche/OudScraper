import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

TARGET_URL = "https://www.ouedkniss.com/automobiles_vehicules/"


def setup_driver():
    driver = webdriver.Firefox()
    return driver


def horizontal_scroll(driver: webdriver.Firefox):
    print("Initiating auto horizontal scroll.....")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".search-top-announcements .swiper")
        )
    )

    is_swipe = True
    print("Swiping top horizontal announces....")
    while is_swipe:
        is_swipe = driver.execute_script(
            "return document.querySelector('.search-top-announcements .swiper').swiper.slideNext()"
        )
    time.sleep(1)
    print("Horizontal scroll finished...")


SCROLL_STEPS = 5


def auto_scroll(driver: webdriver.Firefox):
    """
    Scroll multiple times to the end of the page to make sure it loaded completly
    """
    print("Initiating auto scroll.....")

    print("[1] - Confirming page height.....")
    current_height = 0
    while current_height != driver.execute_script("return document.body.scrollHeight"):
        current_height = driver.execute_script("return document.body.scrollHeight")
        print(f"Current height is >>> {current_height}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    total_height = driver.execute_script("return document.body.scrollHeight")
    print(f"Page height is >>> {total_height}")
    time.sleep(0.2)

    print("[2]- Time to automate your lazy scroll you mfs !!!!")
    step_size = total_height / SCROLL_STEPS
    for step in range(SCROLL_STEPS + 1):
        if step == 0:
            continue

        if step == SCROLL_STEPS:
            scroll_to = total_height
        else:
            scroll_to = step_size * step

        print(f"[{step}] >> Scrolling ....")
        driver.execute_script(f"window.scrollTo(0, {scroll_to})")
        time.sleep(2.5)
    print("[/] Auto scroll finished ....")


def scrap_car_prices():
    driver = setup_driver()

    try:
        driver.get(url=TARGET_URL)
        print(" >>> Waiting for page to load ....")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        horizontal_scroll(driver)

        auto_scroll(driver)
        print(" >>> Waiting for all listings to be queryable...")

        try:
            listings = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        "[class*='v-col-sm-6 v-col-md-4 v-col-lg-3 v-col-12']",
                    ),
                )
            )
        except Exception as e:
            print(f"[x] Could not find listings after scrolling: {e}")
            listings = []  # Continue with an empty list
        potential_listings: list[WebElement] = []

        for listing in listings:
            text = listing.text.strip()
            if text and len(text) > 20:
                potential_listings.append(listing)

        print(f"Found {len(potential_listings)} potential listings after scrolling")

        for i, listing in enumerate(potential_listings[:10]):
            title = "No title"
            price = "No price"
            specification = ["No specifications"]
            city = "No city"

            try:
                id_div = listing.find_element(
                    By.CSS_SELECTOR, ".v-col-sm-6.v-col-md-4.v-col-lg-3.v-col-12 > div"
                )
                id = id_div.get_attribute("id")

                link_div = listing.find_element(By.CSS_SELECTOR, "a[class*='link']")
                link = link_div.get_attribute("href")

                title_element = listing.find_element(
                    By.CSS_SELECTOR, "h3[class*='o-announ-card-title']"
                )
                title = title_element.text.strip()

                price_element = listing.find_element(By.CSS_SELECTOR, "span.price")
                price = price_element.text.strip()
                price = re.sub("\n", " ", price)

                city_element = listing.find_element(
                    By.CSS_SELECTOR, "span[class*='city']"
                )
                city = city_element.text.strip()

                chips_elements = listing.find_elements(
                    By.CSS_SELECTOR, "span[class*='v-chip']"
                )
                for chip in chips_elements:
                    specification.append(chip.text.strip())
                specification.pop(0)

            except Exception:
                print(f"Something bad happened to lsiting nbr {i}!")
                pass
            finally:
                print("=" * 7 + f"Listing -{i}-" + "=" * 7)
                print(f"Identifier: {id}")
                print(f"Title: {title}")
                print(f"Price: {price}")
                print(f"Specifications: {specification}")
                print(f"City: {city}")
                print(f"Link: {link}")

    except Exception as e:
        print(f"[x] Error waiting for elements: {e}")
        with open("debug_page.html", "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print("Debug file saved as 'debug_page.html'")
    finally:
        print("Exiting *********")
        driver.quit()


if __name__ == "__main__":
    scrap_car_prices()
