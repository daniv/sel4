from typing import TYPE_CHECKING

from pydantic import validate_arguments, Field

from .. import constants
from .shared import SeleniumBy
from . import shadow
from ...utils.typeutils import OptionalInt

if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class Assertions:
    def __init__(self, test: "WebDriverTest"):
        self.test = test

    def assert_downloaded_file(self, file, timeout=None, browser=False):
        """Asserts that the file exists in SeleniumBase's [Downloads Folder].
        For browser click-initiated downloads, SeleniumBase will override
            the system [Downloads Folder] to be "./downloaded_files/",
            but that path can't be overridden when using Safari, IE,
            or Chromium Guest Mode, which keeps the default system path.
        self.download_file(file_url) will always use "./downloaded_files/".
        @Params
        file - The filename of the downloaded file.
        timeout - The time (seconds) to wait for the download to complete.
        browser - If True, uses the path set by click-initiated downloads.
                  If False, uses the self.download_file(file_url) path.
                  Those paths are often the same. (browser-dependent)
                  (Default: False).
        """
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.LARGE_TIMEOUT)
        start_ms = time.time() * 1000.0
        stop_ms = start_ms + (timeout * 1000.0)
        downloaded_file_path = self.get_path_of_downloaded_file(file, browser)
        found = False
        for x in range(int(timeout)):
            shared_utils.check_if_time_limit_exceeded()
            try:
                self.assertTrue(
                    os.path.exists(downloaded_file_path),
                    "File [%s] was not found in the downloads folder [%s]!"
                    % (file, self.get_downloads_folder()),
                )
                found = True
                break
            except Exception:
                now_ms = time.time() * 1000.0
                if now_ms >= stop_ms:
                    break
                time.sleep(1)
        if not found and not os.path.exists(downloaded_file_path):
            message = (
                "File {%s} was not found in the downloads folder {%s} "
                "after %s seconds! (Or the download didn't complete!)"
                % (file, self.get_downloads_folder(), timeout)
            )
            page_actions.timeout_exception("NoSuchFileException", message)
        if self.demo_mode:
            messenger_post = "ASSERT DOWNLOADED FILE: [%s]" % file
            try:
                js_utils.activate_jquery(self.driver)
                js_utils.post_messenger_success_message(
                    self.driver, messenger_post, self.message_duration
                )
            except Exception:
                pass

    def assert_any_of(self):
        ...

    def assert_all_of(self):
        ...

    def assert_none_of(self):
        ...

    from selenium.webdriver.support.expected_conditions import

    def assert_true(self, expr, msg=None):
        """Asserts that the expression is True.
        Will raise an exception if the statement if False."""
        self.assertTrue(expr, msg=msg)

    def assert_false(self, expr, msg=None):
        """Asserts that the expression is False.
        Will raise an exception if the statement if True."""
        self.assertFalse(expr, msg=msg)

    def assert_equal(self, first, second, msg=None):
        """Asserts that the two values are equal.
        Will raise an exception if the values are not equal."""
        self.assertEqual(first, second, msg=msg)

    def assert_not_equal(self, first, second, msg=None):
        """Asserts that the two values are not equal.
        Will raise an exception if the values are equal."""
        self.assertNotEqual(first, second, msg=msg)

    def assert_in(self, first, second, msg=None):
        """Asserts that the first string is in the second string.
        Will raise an exception if the first string is not in the second."""
        self.assertIn(first, second, msg=msg)

    def assert_not_in(self, first, second, msg=None):
        """Asserts that the first string is not in the second string.
        Will raise an exception if the first string is in the second string."""
        self.assertNotIn(first, second, msg=msg)

    def assert_raises(self, *args, **kwargs):
        """Asserts that the following block of code raises an exception.
        Will raise an exception if the block of code has no exception.
        Usage Example =>
                # Verify that the expected exception is raised.
                with self.assert_raises(Exception):
                    raise Exception("Expected Exception!")
        """
        return self.assertRaises(*args, **kwargs)

    @validate_arguments
    def assert_attribute(
            self,
            how: SeleniumBy,
            selector: str = Field(default="", strict=True, min_length=1),
            timeout: OptionalInt = None,
            attribute_name: str,
            attribute_value: Any
    ):
        """Raises an exception if the element attribute/value is not found.
        If the value is not specified, the attribute only needs to exist.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.test.__check_scope__()
        timeout = self.test.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_attribute(
            selector, attribute_name, value=attribute_value, by=by, timeout=timeout
        )
        if (
            self.demo_mode
            and not shadow.is_shadow_selector(selector)
            and self.is_element_visible(selector, by=by)
        ):
            a_a = "ASSERT ATTRIBUTE"
            i_n = "in"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_a = SD.translate_assert_attribute(self._language)
                i_n = SD.translate_in(self._language)
            if not value:
                messenger_post = "%s: {%s} %s %s: %s" % (
                    a_a,
                    attribute,
                    i_n,
                    by.upper(),
                    selector,
                )
            else:
                messenger_post = '%s: {%s == "%s"} %s %s: %s' % (
                    a_a,
                    attribute,
                    value,
                    i_n,
                    by.upper(),
                    selector,
                )
            self.__highlight_with_assert_success(messenger_post, selector, by)
        return True

    def __assert_shadow_element_present(self, selector):
        self.__get_shadow_element(selector)
        if self.demo_mode:
            a_t = "ASSERT"
            by = By.CSS_SELECTOR
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert(self._language)
            messenger_post = "%s %s: %s" % (a_t, by.upper(), selector)
            try:
                js_utils.activate_jquery(self.driver)
                js_utils.post_messenger_success_message(
                    self.driver, messenger_post, self.message_duration
                )
            except Exception:
                pass

    def __assert_shadow_element_visible(self, selector):
        element = self.__get_shadow_element(selector)
        if not element.is_displayed():
            msg = "Shadow DOM Element {%s} was not visible!" % selector
            page_actions.timeout_exception("NoSuchElementException", msg)
        if self.demo_mode:
            a_t = "ASSERT"
            by = By.CSS_SELECTOR
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert(self._language)
            messenger_post = "%s %s: %s" % (a_t, by.upper(), selector)
            try:
                js_utils.activate_jquery(self.driver)
                js_utils.post_messenger_success_message(
                    self.driver, messenger_post, self.message_duration
                )
            except Exception:
                pass

    def __assert_eq(self, *args, **kwargs):
        """ Minified assert_equal() using only the list diff. """
        minified_exception = None
        try:
            self.assertEqual(*args, **kwargs)
        except Exception as e:
            str_e = str(e)
            minified_exception = "\nAssertionError:\n"
            lines = str_e.split("\n")
            countdown = 3
            countdown_on = False
            first_differing = False
            skip_lines = False
            for line in lines:
                if countdown_on:
                    if not skip_lines:
                        minified_exception += line + "\n"
                    countdown = countdown - 1
                    if countdown == 0:
                        countdown_on = False
                        skip_lines = False
                elif line.startswith("First differing"):
                    first_differing = True
                    countdown_on = True
                    countdown = 3
                    minified_exception += line + "\n"
                elif line.startswith("First list"):
                    countdown_on = True
                    countdown = 3
                    if not first_differing:
                        minified_exception += line + "\n"
                    else:
                        skip_lines = True
                elif line.startswith("F"):
                    countdown_on = True
                    countdown = 3
                    minified_exception += line + "\n"
                elif line.startswith("+") or line.startswith("-"):
                    minified_exception += line + "\n"
                elif line.startswith("?"):
                    minified_exception += line + "\n"
                elif line.strip().startswith("*"):
                    minified_exception += line + "\n"
        if minified_exception:
            raise Exception(minified_exception)

    def __assert_exact_shadow_text_visible(self, text, selector, timeout):
        self.__wait_for_exact_shadow_text_visible(text, selector, timeout)
        if self.demo_mode:
            a_t = "ASSERT EXACT TEXT"
            i_n = "in"
            by = By.CSS_SELECTOR
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_exact_text(self._language)
                i_n = SD.translate_in(self._language)
            messenger_post = "%s: {%s} %s %s: %s" % (
                a_t,
                text,
                i_n,
                by.upper(),
                selector,
            )
            try:
                js_utils.activate_jquery(self.driver)
                js_utils.post_messenger_success_message(
                    self.driver, messenger_post, self.message_duration
                )
            except Exception:
                pass

    def __assert_shadow_text_visible(self, text, selector, timeout):
        self.__wait_for_shadow_text_visible(text, selector, timeout)
        if self.demo_mode:
            a_t = "ASSERT TEXT"
            i_n = "in"
            by = By.CSS_SELECTOR
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_text(self._language)
                i_n = SD.translate_in(self._language)
            messenger_post = "%s: {%s} %s %s: %s" % (
                a_t,
                text,
                i_n,
                by.upper(),
                selector,
            )
            try:
                js_utils.activate_jquery(self.driver)
                js_utils.post_messenger_success_message(
                    self.driver, messenger_post, self.message_duration
                )
            except Exception:
                pass

    def assert_attribute_not_present(
        self, selector, attribute, value=None, by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_attribute_not_present()
        Raises an exception if the attribute is still present after timeout.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        return self.wait_for_attribute_not_present(
            selector, attribute, value=value, by=by, timeout=timeout
        )

    def assert_element(self, selector, by=By.CSS_SELECTOR, timeout=None):
        """Similar to wait_for_element_visible(), but returns nothing.
        As above, will raise an exception if nothing can be found.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        if type(selector) is list:
            self.assert_elements(selector, by=by, timeout=timeout)
            return True
        if self.__is_shadow_selector(selector):
            self.__assert_shadow_element_visible(selector)
            return True
        self.wait_for_element_visible(selector, by=by, timeout=timeout)
        if self.demo_mode:
            selector, by = self.__recalculate_selector(
                selector, by, xp_ok=False
            )
            a_t = "ASSERT"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert(self._language)
            messenger_post = "%s %s: %s" % (a_t, by.upper(), selector)
            self.__highlight_with_assert_success(messenger_post, selector, by)
        return True

    def assert_element_visible(
        self, selector, by=By.CSS_SELECTOR, timeout=None
    ):
        """Same as self.assert_element()
        As above, will raise an exception if nothing can be found."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.assert_element(selector, by=by, timeout=timeout)
        return True

    def assert_elements(self, *args, **kwargs):
        """Similar to self.assert_element(), but can assert multiple elements.
        The input is a list of elements.
        Optional kwargs include "by" and "timeout" (used by all selectors).
        Raises an exception if any of the elements are not visible.
        Examples:
            self.assert_elements("h1", "h2", "h3")
            OR
            self.assert_elements(["h1", "h2", "h3"])"""
        self.__check_scope()
        selectors = []
        timeout = None
        by = By.CSS_SELECTOR
        for kwarg in kwargs:
            if kwarg == "timeout":
                timeout = kwargs["timeout"]
            elif kwarg == "by":
                by = kwargs["by"]
            elif kwarg == "selector":
                selector = kwargs["selector"]
                if type(selector) is str:
                    selectors.append(selector)
                elif type(selector) is list:
                    selectors_list = selector
                    for selector in selectors_list:
                        if type(selector) is str:
                            selectors.append(selector)
            else:
                raise Exception('Unknown kwarg: "%s"!' % kwarg)
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        for arg in args:
            if type(arg) is list:
                for selector in arg:
                    if type(selector) is str:
                        selectors.append(selector)
            elif type(arg) is str:
                selectors.append(arg)
        for selector in selectors:
            if self.__is_shadow_selector(selector):
                self.__assert_shadow_element_visible(selector)
                continue
            self.wait_for_element_visible(selector, by=by, timeout=timeout)
            if self.demo_mode:
                selector, by = self.__recalculate_selector(selector, by)
                a_t = "ASSERT"
                if self._language != "English":
                    from seleniumbase.fixtures.words import SD

                    a_t = SD.translate_assert(self._language)
                messenger_post = "%s %s: %s" % (a_t, by.upper(), selector)
                self.__highlight_with_assert_success(
                    messenger_post, selector, by
                )
            continue
        return True

    def assert_elements_visible(self, *args, **kwargs):
        """Same as self.assert_elements()
        Raises an exception if any element cannot be found."""
        return self.assert_elements(*args, **kwargs)

    def assert_element_absent(
        self, selector, by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_element_absent()
        As above, will raise an exception if the element stays present.
        A hidden element counts as a present element, which fails this assert.
        If you want to assert that elements are hidden instead of nonexistent,
        use assert_element_not_visible() instead.
        (Note that hidden elements are still present in the HTML of the page.)
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_element_absent(selector, by=by, timeout=timeout)
        return True

    def assert_element_not_present(
        self, selector, by=By.CSS_SELECTOR, timeout=None
    ):
        """Same as self.assert_element_absent()
        Will raise an exception if the element stays present.
        A hidden element counts as a present element, which fails this assert.
        If you want to assert that elements are hidden instead of nonexistent,
        use assert_element_not_visible() instead.
        (Note that hidden elements are still present in the HTML of the page.)
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_element_absent(selector, by=by, timeout=timeout)
        return True

    def assert_element_not_visible(
        self, selector, by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_element_not_visible()
        As above, will raise an exception if the element stays visible.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_element_not_visible(selector, by=by, timeout=timeout)
        return True

    def assert_element_present(
        self, selector, by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_element_present(), but returns nothing.
        Waits for an element to appear in the HTML of a page.
        The element does not need be visible (it may be hidden).
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        if type(selector) is list:
            self.assert_elements_present(selector, by=by, timeout=timeout)
            return True
        if self.__is_shadow_selector(selector):
            self.__assert_shadow_element_present(selector)
            return True
        self.wait_for_element_present(selector, by=by, timeout=timeout)
        return True

    def assert_elements_present(self, *args, **kwargs):
        """Similar to self.assert_element_present(),
            but can assert that multiple elements are present in the HTML.
        The input is a list of elements.
        Optional kwargs include "by" and "timeout" (used by all selectors).
        Raises an exception if any of the elements are not visible.
        Examples:
            self.assert_elements_present("head", "style", "script", "body")
            OR
            self.assert_elements_present(["head", "body", "h1", "h2"])
        """
        self.__check_scope()
        selectors = []
        timeout = None
        by = By.CSS_SELECTOR
        for kwarg in kwargs:
            if kwarg == "timeout":
                timeout = kwargs["timeout"]
            elif kwarg == "by":
                by = kwargs["by"]
            elif kwarg == "selector":
                selector = kwargs["selector"]
                if type(selector) is str:
                    selectors.append(selector)
                elif type(selector) is list:
                    selectors_list = selector
                    for selector in selectors_list:
                        if type(selector) is str:
                            selectors.append(selector)
            else:
                raise Exception('Unknown kwarg: "%s"!' % kwarg)
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        for arg in args:
            if type(arg) is list:
                for selector in arg:
                    if type(selector) is str:
                        selectors.append(selector)
            elif type(arg) is str:
                selectors.append(arg)
        for selector in selectors:
            if self.__is_shadow_selector(selector):
                self.__assert_shadow_element_visible(selector)
                continue
            self.wait_for_element_present(selector, by=by, timeout=timeout)
            continue
        return True

    def assert_text_visible(
        self, text, selector="html", by=By.CSS_SELECTOR, timeout=None
    ):
        """ Same as assert_text() """
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        return self.assert_text(text, selector, by=by, timeout=timeout)

    def assert_text(
        self, text, selector="html", by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_text_visible()
        Raises an exception if the element or the text is not found.
        The text only needs to be a subset within the complete text.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        selector, by = self.__recalculate_selector(selector, by)
        if self.__is_shadow_selector(selector):
            self.__assert_shadow_text_visible(text, selector, timeout)
            return True
        self.wait_for_text_visible(text, selector, by=by, timeout=timeout)
        if self.demo_mode:
            a_t = "ASSERT TEXT"
            i_n = "in"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_text(self._language)
                i_n = SD.translate_in(self._language)
            messenger_post = "%s: {%s} %s %s: %s" % (
                a_t,
                text,
                i_n,
                by.upper(),
                selector,
            )
            self.__highlight_with_assert_success(messenger_post, selector, by)
        return True

    def assert_exact_text(
        self, text, selector="html", by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to assert_text(), but the text must be exact,
        rather than exist as a subset of the full text.
        (Extra whitespace at the beginning or the end doesn't count.)
        Raises an exception if the element or the text is not found.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        selector, by = self.__recalculate_selector(selector, by)
        if self.__is_shadow_selector(selector):
            self.__assert_exact_shadow_text_visible(text, selector, timeout)
            return True
        self.wait_for_exact_text_visible(
            text, selector, by=by, timeout=timeout
        )
        if self.demo_mode:
            a_t = "ASSERT EXACT TEXT"
            i_n = "in"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_exact_text(self._language)
                i_n = SD.translate_in(self._language)
            messenger_post = "%s: {%s} %s %s: %s" % (
                a_t,
                text,
                i_n,
                by.upper(),
                selector,
            )
            self.__highlight_with_assert_success(messenger_post, selector, by)
        return True

    def assert_link_status_code_is_not_404(self, link):
        status_code = str(self.get_link_status_code(link))
        bad_link_str = 'Error: "%s" returned a 404!' % link
        self.assertNotEqual(status_code, "404", bad_link_str)

    def assert_link_text(self, link_text, timeout=None):
        """Similar to wait_for_link_text_visible(), but returns nothing.
        As above, will raise an exception if nothing can be found.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_link_text_visible(link_text, timeout=timeout)
        if self.demo_mode:
            a_t = "ASSERT LINK TEXT"
            messenger_post = "%s: {%s}" % (a_t, link_text)
            self.__highlight_with_assert_success(
                messenger_post, link_text, by=By.LINK_TEXT
            )
        return True

    def assert_no_404_errors(self, multithreaded=True, timeout=None):
        """Assert no 404 errors from page links obtained from:
        "a"->"href", "img"->"src", "link"->"href", and "script"->"src".
        Timeout is on a per-link basis using the "requests" library.
        (A 404 error represents a broken link on a web page.)
        """
        all_links = self.get_unique_links()
        links = []
        for link in all_links:
            if (
                "data:" not in link
                and "mailto:" not in link
                and "javascript:" not in link
                and "://fonts.gstatic.com" not in link
                and "://fonts.googleapis.com" not in link
                and "://googleads.g.doubleclick.net" not in link
            ):
                links.append(link)
        if timeout:
            if not type(timeout) is int and not type(timeout) is float:
                raise Exception('Expecting a numeric value for "timeout"!')
            if timeout < 0:
                raise Exception('The "timeout" cannot be a negative number!')
            self.__requests_timeout = timeout
        broken_links = []
        if multithreaded:
            from multiprocessing.dummy import Pool as ThreadPool

            pool = ThreadPool(10)
            results = pool.map(self.__get_link_if_404_error, links)
            pool.close()
            pool.join()
            for result in results:
                if result:
                    broken_links.append(result)
        else:
            broken_links = []
            for link in links:
                if self.__get_link_if_404_error(link):
                    broken_links.append(link)
        self.__requests_timeout = None  # Reset the requests.get() timeout
        if len(broken_links) > 0:
            broken_links = sorted(broken_links)
            bad_links_str = "\n".join(broken_links)
            if len(broken_links) == 1:
                self.fail("Broken link detected:\n%s" % bad_links_str)
            elif len(broken_links) > 1:
                self.fail("Broken links detected:\n%s" % bad_links_str)
        if self.demo_mode:
            a_t = "ASSERT NO 404 ERRORS"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_no_404_errors(self._language)
            messenger_post = "%s" % a_t
            self.__highlight_with_assert_success(messenger_post, "html")

        def assert_no_broken_links(self, multithreaded=True):
            """ Same as self.assert_no_404_errors() """
            self.assert_no_404_errors(multithreaded=multithreaded)

        def assert_no_js_errors(self):
            """Asserts that there are no JavaScript "SEVERE"-level page errors.
            Works ONLY on Chromium browsers (Chrome or Edge).
            Does NOT work on Firefox, IE, Safari, or some other browsers:
                * See https://github.com/SeleniumHQ/selenium/issues/1161
            Based on the following Stack Overflow solution:
                * https://stackoverflow.com/a/41150512/7058266
            """
            self.__check_scope()
            time.sleep(0.1)  # May take a moment for errors to appear after loads.
            try:
                browser_logs = self.driver.get_log("browser")
            except (ValueError, WebDriverException):
                # If unable to get browser logs, skip the assert and return.
                return
            messenger_library = "//cdnjs.cloudflare.com/ajax/libs/messenger"
            underscore_library = "//cdnjs.cloudflare.com/ajax/libs/underscore"
            errors = []
            for entry in browser_logs:
                if entry["level"] == "SEVERE":
                    if (
                            messenger_library not in entry["message"]
                            and underscore_library not in entry["message"]
                    ):
                        # Add errors if not caused by SeleniumBase dependencies
                        errors.append(entry)
            if len(errors) > 0:
                for n in range(len(errors)):
                    f_t_l_r = " - Failed to load resource"
                    u_c_t_e = " Uncaught TypeError: "
                    if f_t_l_r in errors[n]["message"]:
                        url = errors[n]["message"].split(f_t_l_r)[0]
                        errors[n] = {"Error 404 (broken link)": url}
                    elif u_c_t_e in errors[n]["message"]:
                        url = errors[n]["message"].split(u_c_t_e)[0]
                        error = errors[n]["message"].split(u_c_t_e)[1]
                        errors[n] = {"Uncaught TypeError (%s)" % error: url}
                er_str = str(errors)
                er_str = er_str.replace("[{", "[\n{").replace("}, {", "},\n{")
                current_url = self.get_current_url()
                raise Exception(
                    "JavaScript errors found on %s => %s" % (current_url, er_str)
                )
            if self.demo_mode:
                if self.browser == "chrome" or self.browser == "edge":
                    a_t = "ASSERT NO JS ERRORS"
                    if self._language != "English":
                        from seleniumbase.fixtures.words import SD

                        a_t = SD.translate_assert_no_js_errors(self._language)
                    messenger_post = "%s" % a_t
                    self.__highlight_with_assert_success(messenger_post, "html")

    def assert_partial_link_text(self, partial_link_text, timeout=None):
        """Similar to wait_for_partial_link_text(), but returns nothing.
        As above, will raise an exception if nothing can be found.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        self.wait_for_partial_link_text(partial_link_text, timeout=timeout)
        if self.demo_mode:
            a_t = "ASSERT PARTIAL LINK TEXT"
            messenger_post = "%s: {%s}" % (a_t, partial_link_text)
            self.__highlight_with_assert_success(
                messenger_post, partial_link_text, by=By.PARTIAL_LINK_TEXT
            )
        return True

    def assert_pdf_text(
            self,
            pdf,
            text,
            page=None,
            maxpages=None,
            password=None,
            codec="utf-8",
            wrap=True,
            nav=False,
            override=False,
            caching=True,
    ):
        """Asserts text in a PDF file.
        PDF can be either a URL or a file path on the local file system.
        @Params
        pdf - The URL or file path of the PDF file.
        text - The expected text to verify in the PDF.
        page - The page number of the PDF to use (optional).
                If a page number is provided, looks only at that page.
                    (1 is the first page, 2 is the second page, etc.)
                If no page number is provided, looks at all the pages.
        maxpages - Instead of providing a page number, you can provide
                   the number of pages to use from the beginning.
        password - If the PDF is password-protected, enter it here.
        codec - The compression format for character encoding.
                (The default codec used by this method is 'utf-8'.)
        wrap - Replaces ' \n' with ' ' so that individual sentences
               from a PDF don't get broken up into separate lines when
               getting converted into text format.
        nav - If PDF is a URL, navigates to the URL in the browser first.
              (Not needed because the PDF will be downloaded anyway.)
        override - If the PDF file to be downloaded already exists in the
                   downloaded_files/ folder, that PDF will be used
                   instead of downloading it again.
        caching - If resources should be cached via pdfminer."""
        text = self.__fix_unicode_conversion(text)
        if not codec:
            codec = "utf-8"
        pdf_text = self.get_pdf_text(
            pdf,
            page=page,
            maxpages=maxpages,
            password=password,
            codec=codec,
            wrap=wrap,
            nav=nav,
            override=override,
            caching=caching,
        )
        if type(page) is int:
            if text not in pdf_text:
                raise Exception(
                    "PDF [%s] is missing expected text [%s] on "
                    "page [%s]!" % (pdf, text, page)
                )
        else:
            if text not in pdf_text:
                raise Exception(
                    "PDF [%s] is missing expected text [%s]!" % (pdf, text)
                )
        return True


    def assert_text_not_visible(
        self, text, selector="html", by=By.CSS_SELECTOR, timeout=None
    ):
        """Similar to wait_for_text_not_visible()
        Raises an exception if the text is still visible after timeout.
        Returns True if successful. Default timeout = SMALL_TIMEOUT."""
        self.__check_scope__()
        timeout = self.get_timeout(timeout, constants.SMALL_TIMEOUT)
        return self.wait_for_text_not_visible(
            text, selector, by=by, timeout=timeout
        )

    def assert_title(self, title):
        """Asserts that the web page title matches the expected title.
        When a web page initially loads, the title starts as the URL,
            but then the title switches over to the actual page title.
        In Recorder Mode, this assertion is skipped because the Recorder
            changes the page title to the selector of the hovered element.
        """
        self.wait_for_ready_state_complete()
        expected = title.strip()
        actual = self.get_page_title().strip()
        error = (
            "Expected page title [%s] does not match the actual title [%s]!"
        )
        try:
            if not self.recorder_mode:
                self.assertEqual(expected, actual, error % (expected, actual))
        except Exception:
            self.wait_for_ready_state_complete()
            self.sleep(settings.MINI_TIMEOUT)
            actual = self.get_page_title().strip()
            try:
                self.assertEqual(expected, actual, error % (expected, actual))
            except Exception:
                self.wait_for_ready_state_complete()
                self.sleep(settings.MINI_TIMEOUT)
                actual = self.get_page_title().strip()
                self.assertEqual(expected, actual, error % (expected, actual))
        if self.demo_mode and not self.recorder_mode:
            a_t = "ASSERT TITLE"
            if self._language != "English":
                from seleniumbase.fixtures.words import SD

                a_t = SD.translate_assert_title(self._language)
            messenger_post = "%s: {%s}" % (a_t, title)
            self.__highlight_with_assert_success(messenger_post, "html")
        return True



