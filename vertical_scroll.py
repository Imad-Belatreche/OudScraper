from selenium import webdriver


def scroll_page(driver: webdriver.Firefox, screen_multi: int):
    """
    Scroll vertically by the page height + the given pixels
    """
    driver.execute_script(f"window.scrollBy(0, (window.innerHeight * {screen_multi}))")
