from typing import TYPE_CHECKING

from pydantic import validate_arguments, Field

from .. import constants
from .shared import SeleniumBy
from . import shadow
from ...utils.typeutils import OptionalInt

if TYPE_CHECKING:
    from sel4.core.webdriver_test import WebDriverTest


class Messenger:
    def __init__(self, test: "WebDriverTest"):
        self.test = test

    def activate_messenger(self):
        self.__check_scope()
        self.__check_browser()
        js_utils.activate_messenger(self.driver)
        self.wait_for_ready_state_complete()

    def set_messenger_theme(
        self, theme="default", location="default", max_messages="default"
    ):
        """Sets a theme for posting messages.
        Themes: ["flat", "future", "block", "air", "ice"]
        Locations: ["top_left", "top_center", "top_right",
                    "bottom_left", "bottom_center", "bottom_right"]
        max_messages is the limit of concurrent messages to display.
        """
        self.__check_scope()
        self.__check_browser()
        if not theme:
            theme = "default"  # "flat"
        if not location:
            location = "default"  # "bottom_right"
        if not max_messages:
            max_messages = "default"  # "8"
        else:
            max_messages = str(max_messages)  # Value must be in string format
        js_utils.set_messenger_theme(
            self.driver,
            theme=theme,
            location=location,
            max_messages=max_messages,
        )

    def post_message(self, message, duration=None, pause=True, style="info"):
        """Post a message on the screen with Messenger.
        Arguments:
            message: The message to display.
            duration: The time until the message vanishes. (Default: 2.55s)
            pause: If True, the program waits until the message completes.
            style: "info", "success", or "error".
        You can also post messages by using =>
            self.execute_script('Messenger().post("My Message")')
        """
        self.__check_scope()
        self.__check_browser()
        if style not in ["info", "success", "error"]:
            style = "info"
        if not duration:
            if not self.message_duration:
                duration = settings.DEFAULT_MESSAGE_DURATION
            else:
                duration = self.message_duration
        if (self.headless or self.xvfb) and float(duration) > 0.75:
            duration = 0.75
        try:
            js_utils.post_message(self.driver, message, duration, style=style)
        except Exception:
            print(" * %s message: %s" % (style.upper(), message))
        if pause:
            duration = float(duration) + 0.15
            time.sleep(float(duration))

    def post_message_and_highlight(
        self, message, selector, by=By.CSS_SELECTOR
    ):
        """Post a message on the screen and highlight an element.
        Arguments:
            message: The message to display.
            selector: The selector of the Element to highlight.
            by: The type of selector to search by. (Default: CSS Selector)
        """
        self.__check_scope__()
        self.__highlight_with_assert_success(message, selector, by=by)

    def post_success_message(self, message, duration=None, pause=True):
        """Post a success message on the screen with Messenger.
        Arguments:
            message: The success message to display.
            duration: The time until the message vanishes. (Default: 2.55s)
            pause: If True, the program waits until the message completes.
        """
        self.__check_scope()
        self.__check_browser()
        if not duration:
            if not self.message_duration:
                duration = settings.DEFAULT_MESSAGE_DURATION
            else:
                duration = self.message_duration
        if (self.headless or self.xvfb) and float(duration) > 0.75:
            duration = 0.75
        try:
            js_utils.post_message(
                self.driver, message, duration, style="success"
            )
        except Exception:
            print(" * SUCCESS message: %s" % message)
        if pause:
            duration = float(duration) + 0.15
            time.sleep(float(duration))

    def post_error_message(self, message, duration=None, pause=True):
        """Post an error message on the screen with Messenger.
        Arguments:
            message: The error message to display.
            duration: The time until the message vanishes. (Default: 2.55s)
            pause: If True, the program waits until the message completes.
        """
        self.__check_scope()
        self.__check_browser()
        if not duration:
            if not self.message_duration:
                duration = settings.DEFAULT_MESSAGE_DURATION
            else:
                duration = self.message_duration
        if (self.headless or self.xvfb) and float(duration) > 0.75:
            duration = 0.75
        try:
            js_utils.post_message(
                self.driver, message, duration, style="error"
            )
        except Exception:
            print(" * ERROR message: %s" % message)
        if pause:
            duration = float(duration) + 0.15
            time.sleep(float(duration))