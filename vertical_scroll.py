import time
from selenium import webdriver


SCROLL_STEPS = 5


def get_total_height(driver: webdriver.Firefox):
    max_height = 15
    current_height = 0
    current_i = 0

    while (
        current_height != driver.execute_script("return document.body.scrollHeight")
        and current_i < max_height
    ):
        current_height = driver.execute_script("return document.body.scrollHeight")

        print(f"Current height is >>> {current_height}")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.3)
        current_i += 1

    total_height = driver.execute_script("return document.body.scrollHeight")
    print(f"Page height is >>> {total_height}")
    return total_height


def scroll_page(driver: webdriver.Firefox, pixels_to_scroll: int):
    driver.execute_script(f"window.scrollBy(0, {pixels_to_scroll})")


def auto_scroll(driver: webdriver.Firefox):
    """
    Scroll multiple times to the end of the page to make sure it loaded completly
    """
    print("Initiating auto scroll.....")

    print("[1] - Confirming page height.....")

    total_height = get_total_height(driver)

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
        time.sleep(1)

    print("[/] Auto scroll finished ....")
