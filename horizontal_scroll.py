import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver

# NOT NEEDED CURRENTLY


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
