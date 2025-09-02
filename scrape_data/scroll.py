# scroll.py
# Hàm cuộn "bền" cho khối list (role="feed") của Google Maps

import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from config import SCROLL_PATIENCE, SCROLL_MAX_ROUNDS, SCROLL_WAIT_ITEM, SCROLL_GAP_MINMAX

def _count_cards(driver):
    return len(driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK"))

def scroll_to_list_bottom(driver, feed_elem,
                          patience=SCROLL_PATIENCE, max_rounds=SCROLL_MAX_ROUNDS):
    # Chờ có item đầu tiên
    WebDriverWait(driver, SCROLL_WAIT_ITEM).until(lambda d: _count_cards(d) > 0)

    prev = -1
    same = 0
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_elem)

        try:
            WebDriverWait(driver, 3).until(lambda d: _count_cards(d) > prev)
            curr = _count_cards(driver)
        except TimeoutException:
            curr = _count_cards(driver)

        if curr == prev:
            same += 1
        else:
            same = 0
            prev = curr

        if same >= patience:
            break

        time.sleep(random.uniform(*SCROLL_GAP_MINMAX))
