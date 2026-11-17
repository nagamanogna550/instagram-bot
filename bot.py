"""Instagram bot built on Selenium WebDriver.

dry_run=True (default): nothing is opened or clicked; actions are only logged.
dry_run=False: drives a real Chrome browser. Instagram changes its page layout
often, so the XPath selectors below may need updating.
"""
import logging
import os
import time

from safety import RateLimiter, human_delay, type_like_human

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:          # only needed for live mode
    webdriver = None

log = logging.getLogger("instagram_bot")
BASE = "https://www.instagram.com"


class InstagramBot:
    def __init__(self, username=None, password=None, dry_run=True, limiter=None,
                 delay_range=(4.0, 12.0), headless=False, sleep=time.sleep):
        self.username, self.password = username, password
        self.dry_run = dry_run
        self.limiter = limiter or RateLimiter()
        self.delay_range = delay_range
        self.headless = headless
        self.sleep = sleep
        self.driver = None
        self.wait = None

    # ---------- infrastructure ----------
    def _tag(self):
        return "[DRY RUN] " if self.dry_run else ""

    def _delay(self):
        d = human_delay(*self.delay_range, sleep=self.sleep)
        log.info("%swaiting %.1fs", self._tag(), d)

    def _allowed(self, action):
        if self.limiter.can_do(action):
            return True
        log.warning("Daily limit reached for '%s'; skipping.", action)
        return False

    def start(self):
        if self.dry_run:
            log.info("[DRY RUN] browser not started.")
            return
        if webdriver is None:
            raise RuntimeError("Selenium is not installed. Run: pip install selenium")
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1280,900")
        if self.headless:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)   # Selenium Manager fetches the driver
        self.wait = WebDriverWait(self.driver, 15)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _click_if_present(self, xpath, timeout=3):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))).click()
            return True
        except TimeoutException:
            return False

    def _dismiss_popups(self):
        for label in ("Allow all cookies", "Not now", "Not Now"):
            self._click_if_present(f"//button[normalize-space()='{label}']", timeout=2)

    # ---------- workflows ----------
    def login(self):
        if self.dry_run:
            log.info("[DRY RUN] would log in as %s", self.username or "<username>")
            return True
        if not (self.username and self.password):
            raise ValueError("Username and password are required for live mode.")
        self.driver.get(f"{BASE}/accounts/login/")
        self._click_if_present("//button[normalize-space()='Allow all cookies']")
        user = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
        type_like_human(user, self.username, sleep=self.sleep)
        pwd = self.driver.find_element(By.NAME, "password")
        type_like_human(pwd, self.password, sleep=self.sleep)
        pwd.send_keys(Keys.ENTER)
        self._delay()
        if any(k in self.driver.current_url for k in ("challenge", "two_factor", "suspicious")):
            input("Complete the verification in the browser, then press Enter here...")
        self._dismiss_popups()
        ok = "login" not in self.driver.current_url
        log.info("Login %s", "succeeded" if ok else "failed")
        return ok

    def search_hashtag(self, tag, max_posts=10):
        tag = tag.lstrip("#").strip().lower()
        if self.dry_run:
            log.info("[DRY RUN] would search #%s", tag)
            return [f"{BASE}/p/DRYRUN{i:03d}/" for i in range(1, max_posts + 1)]
        self.driver.get(f"{BASE}/explore/tags/{tag}/")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/p/']")))
        links = []
        for a in self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']"):
            href = a.get_attribute("href")
            if href and href not in links:
                links.append(href)
        self._delay()
        return links[:max_posts]

    def get_post_author(self, url):
        if self.dry_run:
            return "dry_user_" + url.rstrip("/").split("/")[-1][-3:]
        self.driver.get(url)
        el = self.wait.until(EC.presence_of_element_located((By.XPATH, "//header//a[@role='link']")))
        return el.text.strip()

    def like_post(self, url):
        if not self._allowed("like"):
            return False
        if self.dry_run:
            log.info("[DRY RUN] would like %s", url)
        else:
            try:
                self.driver.get(url)
                if self.driver.find_elements(By.XPATH, "//*[name()='svg'][@aria-label='Unlike']"):
                    log.info("Already liked: %s", url)
                    return False
                btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[name()='svg'][@aria-label='Like']/ancestor::div[@role='button'][1]")))
                btn.click()
            except (TimeoutException, WebDriverException) as e:
                log.error("Like failed for %s: %s", url, type(e).__name__)
                return False
        self.limiter.record("like")
        log.info("%sLiked %s", self._tag(), url)
        self._delay()
        return True

    def comment_post(self, url, text):
        if not self._allowed("comment"):
            return False
        if self.dry_run:
            log.info("[DRY RUN] would comment '%s' on %s", text, url)
        else:
            try:
                self.driver.get(url)
                box = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//textarea[contains(@aria-label,'comment')]")))
                box.click()
                type_like_human(box, text, sleep=self.sleep)
                box.send_keys(Keys.ENTER)
            except (TimeoutException, WebDriverException) as e:
                log.error("Comment failed for %s: %s", url, type(e).__name__)
                return False
        self.limiter.record("comment")
        log.info("%sCommented on %s", self._tag(), url)
        self._delay()
        return True

    def follow_user(self, username):
        if not self._allowed("follow"):
            return False
        if self.dry_run:
            log.info("[DRY RUN] would follow %s", username)
        else:
            try:
                self.driver.get(f"{BASE}/{username}/")
                btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//header//button[normalize-space()='Follow']")))
                btn.click()
            except (TimeoutException, WebDriverException) as e:
                log.error("Follow failed for %s: %s", username, type(e).__name__)
                return False
        self.limiter.record("follow")
        log.info("%sFollowed %s", self._tag(), username)
        self._delay()
        return True

    def upload_post(self, image_path, caption):
        if not self._allowed("upload"):
            return False
        if not os.path.isfile(image_path):
            raise FileNotFoundError(image_path)
        if self.dry_run:
            log.info("[DRY RUN] would upload %s with caption:\n%s", image_path, caption)
        else:
            try:
                self.driver.get(BASE)
                self._dismiss_popups()
                self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[name()='svg'][@aria-label='New post']/ancestor::*[@role='link' or @role='button'][1]"))).click()
                file_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
                file_input.send_keys(os.path.abspath(image_path))
                for _ in range(2):                       # crop step, then filter step
                    self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][normalize-space()='Next']"))).click()
                    self._delay()
                box = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@aria-label='Write a caption...']")))
                box.click()
                type_like_human(box, caption.replace("\n", " "), sleep=self.sleep)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][normalize-space()='Share']"))).click()
                self._delay()
            except (TimeoutException, WebDriverException) as e:
                log.error("Upload failed: %s", type(e).__name__)
                return False
        self.limiter.record("upload")
        log.info("%sUploaded %s", self._tag(), image_path)
        return True
