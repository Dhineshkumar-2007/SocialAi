import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"
TEST_CASES = "tests/test_cases"


def fill_problem(page, title, description):
    page.goto(BASE_URL)
    inputs = page.locator("input")
    inputs.nth(0).fill(title)
    page.locator("textarea").fill(description)
    inputs.nth(1).fill("10.7905")
    inputs.nth(2).fill("78.7047")


def test_page_loads(page: Page):
    page.goto(BASE_URL)
    expect(page.get_by_text("Report a problem")).to_be_visible()
    expect(page.get_by_role("button", name="Submit & Analyze")).to_be_visible()


def test_valid_problem(page: Page):
    fill_problem(
        page,
        "Non-Functional Streetlights Causing Safety Issues",
        "Around 15 streetlights have not been working for three weeks. "
        "The road becomes dark at night and residents are concerned about safety."
    )
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(20000)
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


def test_empty_title(page: Page):
    page.goto(BASE_URL)
    page.locator("textarea").fill("Several streetlights are not working.")
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(2000)
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


def test_empty_description(page: Page):
    page.goto(BASE_URL)
    inputs = page.locator("input")
    inputs.nth(0).fill("Broken Streetlights")
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(2000)
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


def test_relevant_evidence(page: Page):
    fill_problem(
        page,
        "Non-Functional Streetlights Causing Safety Issues",
        "Several streetlights are not working and the road becomes dark at night."
    )
    page.locator('input[type="file"]').set_input_files(
        f"{TEST_CASES}/streetlight.jpg"
    )
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(20000)
    print(page.locator("body").inner_text())
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


@pytest.mark.parametrize("image", ["deer.jpg", "pizza.jpg"])
def test_irrelevant_evidence(page: Page, image):
    fill_problem(
        page,
        "Non-Functional Streetlights Causing Safety Issues",
        "Several streetlights are not working and the road becomes dark at night."
    )
    page.locator('input[type="file"]').set_input_files(
        f"{TEST_CASES}/{image}"
    )
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(20000)
    print(f"\n===== {image} =====\n")
    print(page.locator("body").inner_text())
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


def test_invalid_coordinates(page: Page):
    page.goto(BASE_URL)
    inputs = page.locator("input")
    inputs.nth(0).fill("Broken Streetlights")
    page.locator("textarea").fill("Streetlights are not working.")
    inputs.nth(1).fill("999")
    inputs.nth(2).fill("999")
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(5000)
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")


def test_long_description(page: Page):
    fill_problem(
        page,
        "Streetlight Infrastructure Problem",
        "Streetlights are not working. " * 500
    )
    page.get_by_role("button", name="Submit & Analyze").click()
    page.wait_for_timeout(5000)
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")
