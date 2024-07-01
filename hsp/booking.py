from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException,
                                        WebDriverException)
from .errors import (CourseIdNotListed, CourseIdAmbiguous,
                     CourseNotBookable, InvalidCredentials, LoadingFailed)
from .conditions import submit_successful, element_inner_html_has_changed


def start_firefox():

    driver = webdriver.Firefox()
    return driver


def start_headless_firefox():

    ff_options = FirefoxOptions()
    ff_options.headless = True
    driver = webdriver.Firefox(options=ff_options)
    return driver


def start_chrome():
    chrome_options = ChromeOptions()
    chrome_options.add_experimental_option("detach", True)
    # prevent detection with window.navigator.webdriver check
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=chrome_options)
    # driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});window.navigator = navigator;")
    return driver


def start_headless_chrome():

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def start_edge():
    edge_options = EdgeOptions()
    edge_options.add_experimental_option("detach", True)
    # prevent detection with window.navigator.webdriver check
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Edge(options=edge_options)
    return driver


class HSPCourse:
    """
    """

    def __init__(self, course, driver=None):
        self.timeout = 20  # waiting time for site to load in seconds
        self.driver = driver or self._init_driver()
        self.course = course
        self.time = None
        self.weekday = None
        self.location = None
        self.level = None
        self._scrape_course_detail()

        self.course_name = None
        self.booking_possible = None
        self.waitinglist_exists = None
        self.course_status = None
        self._scrape_course_status()

        self._booking_page = None

    def _get_el_from_coursepage(self, xpath):

        assert(self.driver.current_url == self.course.url)
        return self.driver.find_element("xpath", xpath)

    def _cl_get_time(self, course_row_xpath):

        time_xpath = course_row_xpath + '/td[@class="bs_szeit"]'
        return self._get_el_from_coursepage(time_xpath).text

    def _cl_get_weekday(self, course_row_xpath):

        weekday_xpath = course_row_xpath + '/td[@class="bs_stag"]'
        return self._get_el_from_coursepage(weekday_xpath).text

    def _cl_get_location(self, course_row_xpath):

        location_xpath = course_row_xpath + '/td[@class="bs_sort"]'
        return self._get_el_from_coursepage(location_xpath).text

    def _cl_get_level(self, course_row_xpath):

        location_xpath = course_row_xpath + '/td[@class="bs_sdet"]'
        return self._get_el_from_coursepage(location_xpath).text

    def _cp_get_course_name(self):

        title_xp = "//div[@class='bs_head']"
        course_name_div = self._get_el_from_coursepage(title_xp)
        return course_name_div.text

    def _cp_get_bookingbtn_or_status_element(self):

        course_code = "K" + self.course.id
        xpath = "//a[@id='{}']/following::*".format(course_code)
        return self._get_el_from_coursepage(xpath)

    def _scrape_course_detail(self):
        try:
            self.driver.get(self.course.url)

            # course site features a table:
            # extract the row that starts with the course id
            xpath = '//td[text()="{}"]/parent::tr'
            course_row_xpath = xpath.format(self.course.id)

            self.time = self._cl_get_time(course_row_xpath)
            self.weekday = self._cl_get_weekday(course_row_xpath)
            self.location = self._cl_get_location(course_row_xpath)
            self.level = self._cl_get_level(course_row_xpath)
            # self.course_page_url = self._cl_get_course_link(course_row_xpath)

        except TimeoutException as e:
            print(e)
            raise LoadingFailed("Timeout while loading course list page")

        except NoSuchElementException as e:
            print(e)
            raise CourseIdNotListed(self.course.id)

    def _scrape_course_status(self):

        self.driver.get(self.course.url)

        self.course_name = self._cp_get_course_name()
        bookbtn_or_status = self._cp_get_bookingbtn_or_status_element()

        # If bookbtn_or_status is a <span> ... </span> element,
        # the course is not bookable and there is it contains a
        # no-booking-possible status
        if bookbtn_or_status.tag_name == "span":
            self.course_status = bookbtn_or_status.text
            self.booking_possible = False
            self.waitinglist_exists = False

        elif "bs_btn_warteliste" in bookbtn_or_status.get_attribute("class"):
            self.course_status = "queue signup"
            self.booking_possible = False
            self.waitinglist_exists = True

        elif "bs_btn_buchen" in bookbtn_or_status.get_attribute("class"):
            self.course_status = "booking possible"
            self.booking_possible = True
            self.waitinglist_exists = False

        else:
            self.course_status = "unknown"
            self.booking_possible = False
            self.waitinglist_exists = False

    def _init_driver(self):

        try:
            driver = start_headless_chrome()
        except WebDriverException as e:
            print(e)
            print("[!] Loading Chrome webdriver failed")
            print("... Attempting to use Firefox webdriver")
            driver = start_headless_chrome()
        return driver

    def info(self):
        infostr = "#{}: {} {}, {} {}".format(self.course.id or "",
                                             self.course_name or "",
                                             self.level or "",
                                             self.weekday or "",
                                             self.time or "")
        return infostr

    def status(self):
        return "Status: {}".format(self.course_status)

    def is_bookable(self):
        return self.booking_possible

    def has_waitinglist(self):
        return self.waitinglist_exists

    def _switch_to_booking_page(self):

        if self.has_waitinglist() or not self.is_bookable():
            raise CourseNotBookable(self.course.id, self.status())

        self.driver.get(self.course.url)

        # at this point, the course is bookable
        booking_btn = self._cp_get_bookingbtn_or_status_element()

        # snapshot of open windows / tabs
        old_windows = self.driver.window_handles

        # press the booking button, which opens a new tab
        booking_btn.click()

        # find the new tab
        new_tab = (set(self.driver.window_handles) - set(old_windows)).pop()

        # switch to new tab
        self.driver.switch_to.window(new_tab)

        # make the window larger, so no fields are being hidden
        self.driver.set_window_size(height=1500, width=2000)

        self._booking_page = self.driver.current_url

    def _bp_enter_personal_details(self, credentials):

        assert (self.driver.current_url == self._booking_page)

        if not credentials or not credentials.is_valid:
            raise InvalidCredentials("Credentials are invalid")

        # status dropdown and matriculation number / employee phone
        status_xpath_template = '//select[@id="BS_F1600"]//option[@value="{}"]'
        status_xpath = status_xpath_template.format(credentials.status)
        # student status
        if credentials.status in ("S-RWTH", "S-aH"):
            self.driver.find_element("xpath", status_xpath).click()
            pid_xpath = '//input[@id="BS_F1700"][@name="matnr"]'
            self.driver.find_element("xpath", pid_xpath).send_keys(
                credentials.pid)
        # employee status
        elif credentials.status in ("B-UNIT", "B-UKT", "B-aH"):
            self.driver.find_element("xpath", status_xpath).click()
            pid_xpath = '//input[@id="BS_F1700"][@name="mitnr"]'
            self.driver.find_element("xpath", pid_xpath).send_keys(
                credentials.pid)
        elif credentials.status == "Extern":
            self.driver.find_element("xpath", status_xpath).click()

        # gender radio select
        gender_xpath = '//input[@name="sex"][@value="{}"]'.format(
            credentials.gender)
        self.driver.find_element("xpath", gender_xpath).click()

        # name field
        name_xpath = '//input[@id="BS_F1100"][@name="vorname"]'
        self.driver.find_element("xpath", name_xpath).send_keys(
            credentials.name)

        # surname field
        surname_xpath = '//input[@id="BS_F1200"][@name="name"]'
        self.driver.find_element("xpath", surname_xpath).send_keys(
            credentials.surname)

        # street+no field
        street_xpath = '//input[@id="BS_F1300"][@name="strasse"]'
        self.driver.find_element("xpath", street_xpath).send_keys(
            credentials.street + " " + credentials.number)

        # zip+city field
        city_xpath = '//input[@id="BS_F1400"][@name="ort"]'
        self.driver.find_element("xpath", city_xpath).send_keys(
            credentials.zip_code + " " + credentials.city)

        # email field
        email_xpath = '//input[@id="BS_F2000"][@name="email"]'
        self.driver.find_element("xpath", email_xpath).send_keys(
            credentials.email)

        tel_xpath = '//input[@id="BS_F2100"][@name="telefon"]'
        self.driver.find_element("xpath", tel_xpath).send_keys(
            credentials.tel)

        self._bp_enter_iban(credentials)

    def _update_personal_details(self, credentials):
        assert (self.driver.current_url == self._booking_page)

        if not credentials or not credentials.is_valid:
            raise InvalidCredentials("Credentials are invalid")

        # street+no field
        street_xpath = '//input[@id="BS_F1300"][@name="strasse"]'
        street_input = self.driver.find_element("xpath", street_xpath)
        street_input.clear()
        street_input.send_keys(credentials.street + " " + credentials.number)

        # zip+city field
        city_xpath = '//input[@id="BS_F1400"][@name="ort"]'
        city_input = self.driver.find_element("xpath", city_xpath)
        city_input.clear()
        city_input.send_keys(credentials.zip_code + " " + credentials.city)


    def _bp_enter_iban(self, credentials):
        try:
            iban_xpath = '//input[@id="BS_F_iban"][@name="iban"]'
            wait = WebDriverWait(self.driver, 1)
            iban_input = wait.until(EC.presence_of_element_located((By.XPATH, iban_xpath,)))
            iban_input.clear()
            iban_input.send_keys(credentials.iban)
        except TimeoutException:
            pass

    def _bp_agree_to_eula(self):
        # agree to EULA
        eula_xpath = '//input[@name="tnbed"]'
        wait = WebDriverWait(self.driver, 1)
        eula = wait.until(EC.presence_of_element_located((By.XPATH, eula_xpath,)))
        eula.click()

    def _bp_enter_user_login(self, credentials):
        assert (self.driver.current_url == self._booking_page)

        if not credentials or not credentials.is_valid:
            raise InvalidCredentials("Credentials are invalid")

        login_xpath = '//div[@id="bs_pw_anmlink"]'
        self.driver.find_element("xpath", login_xpath).click()

        email_xpath = '//input[@name="pw_email"]'
        email_input = WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.XPATH, email_xpath,)))
        email_input.send_keys(credentials.email)

        pw_xpath = '//input[contains(@name, "pw_pwd_")]'
        self.driver.find_element("xpath", pw_xpath).send_keys(credentials.password)

    def _bp_confirm_user_login(self):
        xpath = "//input[@type='submit'][@value='weiter zur Buchung']"
        submit_locator = (By.XPATH, xpath)

        observed_xpath = '//input[contains(@name, "pw_pwd_")]'
        control_locator = (By.XPATH, observed_xpath)

        self._retry_submit(submit_locator, control_locator)

    def _bp_enter_password(self, password):
        assert (self.driver.current_url == self._booking_page)

        password_xpath = "//input[@class='bs_form_field'][@name='passwd']"

        try:
            self.driver.find_element("xpath", password_xpath).send_keys(password)

            button_xpath = "//input[@type='submit'][@value='weiter']"
            submit_locator = (By.XPATH, button_xpath)

            observed_xpath = password_xpath
            control_locator = (By.XPATH, observed_xpath)

            self._retry_submit(submit_locator, control_locator)
        except NoSuchElementException:
            pass

    def _bp_enter_confirm_email(self, email):

        assert(self.driver.current_url == self._booking_page)

        xpath = "//input[@class='bs_form_field'][contains(@name, 'email_check_')]"

        try:
            self.driver.find_element("xpath", xpath).send_keys(email)
        except NoSuchElementException:
            pass

    def _retry_submit(self, submit_loc, control_loc):
        """
        Retry submitting, until control_loc disappears
        """

        assert(self.driver.current_url == self._booking_page)

        wait = WebDriverWait(self.driver, self.timeout)
        wait.until(submit_successful(submit_loc, control_loc))

    def _bp_wait_until_submit(self):
        """
        Retries submitting the data, until the confirmation page is loaded.
        Pag chage is detected by observing a checkbox field, that disappears.
        """
        xpath = "//input[@type='submit'][@value='weiter zur Buchung']"
        submit_locator = (By.XPATH, xpath)

        observed_xpath = "//input[@type='checkbox'][@name='tnbed']"
        control_locator = (By.XPATH, observed_xpath)

        # skip wait
        try:
            self.driver.execute_script('document.getElementById("bs_counter").className ="hidden"; document.getElementById("bs_submit").className = "sub";send = 1;')
        except:
            pass

        self._retry_submit(submit_locator, control_locator)

    def _bp_wait_until_confirm(self):
        """
        Retries confirming the form, until the ticket is loaded
        """
        xpath = "//input[@type='submit'][contains(@value, 'buchen')]"
        submit_locator = (By.XPATH, xpath)

        observed_xpath = "//div[contains(@class, 'bs_text_red') and contains(@class, 'bs_text_big')]"
        control_locator = (By.XPATH, observed_xpath)

        self._retry_submit(submit_locator, control_locator)

    def _save_screenshot(self, outfile):

        if outfile is None:
            tmpl = "booking_confirmation_{}.png"
            outfile = tmpl.format(self.course.id)

        # save the final page as a screenshot
        self.driver.save_screenshot(outfile)
        print("[*] Booking ticket saved to {}".format(outfile))

    def book(self, credentials, test=False, confirmation_file=None):

        self._switch_to_booking_page()

        # fill in password if exists
        if self.course.password:
            self._bp_enter_password(self.course.password)

        if credentials.password:
            self._bp_enter_user_login(credentials)
            self._bp_confirm_user_login()
            self._update_personal_details(credentials)
            self._bp_enter_iban(credentials)
        else:
            # verify and fill in the personal data
            self._bp_enter_personal_details(credentials)

        self._bp_agree_to_eula()

        # wait until inputs are submited and page changes
        self._bp_wait_until_submit()

        # fill in confirm email field, if it exists
        self._bp_enter_confirm_email(credentials.email)

        # wait until confirm button is pressed and page changes
        if not test:
            self._bp_wait_until_confirm()

        self._save_screenshot(confirmation_file)

        # close the driver
        # self.driver.quit()
