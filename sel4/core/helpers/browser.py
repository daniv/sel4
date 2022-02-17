from pydantic import (
    BaseModel,
    HttpUrl,
    FileUrl,
    AnyHttpUrl,
    AnyUrl,
    ValidationError,
    validator
)


def is_http_url(url: str):
    class ValidateHttpUrl(BaseModel):
        url: HttpUrl

    try:
        url = ValidateHttpUrl(url=url)
        return True
    except ValidationError:
        return False


def is_file_url(url: str):
    class ValidateFileUrl(BaseModel):
        url: FileUrl

    try:
        url = ValidateFileUrl(url=url)
        return True
    except ValidationError:
        return False


def is_any_http_url(url: str):
    class ValidateAnyHttpUrl(BaseModel):
        url: AnyHttpUrl

    try:
        url = ValidateAnyHttpUrl(url=url)
        return True
    except ValidationError:
        return False


def is_webdriver_url(url: str):
    class WebDriverUrl(BaseModel):
        url: str


def is_any_url(url: str):
    class ValidateAnyUrl(BaseModel):
        url: AnyUrl

    try:
        url = ValidateAnyUrl(url=url)
        return True
    except ValidationError:
        return False



if __name__ == "__main__":
    print("data:", is_any_url("data:"))
    print("http://google.com", is_http_url("http://google.com"))
    print("https://google.com", is_http_url("https://google.com"))
    print("://google.com", is_any_url("://google.com"))
    print("file://google.com", is_file_url("file://google.com"))
    print("about:", is_any_url("about:"))
    print("chrome:", is_any_url("chrome:"))
    print("http://localhost:63342/:", is_any_http_url("http://localhost:63342/"))
    print("chrome://version/", is_any_http_url("chrome://version/"))
