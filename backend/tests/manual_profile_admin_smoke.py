"""Manual browser smoke test for the live profile administration page."""

import json
import sys

from playwright.sync_api import sync_playwright


def main() -> None:
    base_url = sys.argv[1]
    screenshot_path = sys.argv[2]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{base_url}/profiles/admin")
        page.locator("#profileSelect").wait_for()

        page.get_by_role("button", name="Neues Profil").click()
        page.locator("#displayName").fill("Browser-Smoke-Test")
        page.locator("#profileReason").fill("Automatischer Browser-Test")
        page.locator("#saveProfile").click()
        page.wait_for_function(
            """() => [...document.querySelector('#profileSelect').options]
                .some(option => option.textContent.includes('Browser-Smoke-Test'))"""
        )

        page.get_by_role("button", name="Eintrag hinzufügen").click()
        form = page.locator("#entryForm")
        form.locator('[name="canonical_name"]').fill("Browser Test Skill")
        form.locator('[name="category"]').fill("test")
        form.locator('[name="de_title"]').fill("Browser-Test-Skill")
        form.locator('[name="en_title"]').fill("Browser test skill")
        form.locator('[name="change_reason"]').fill("Browser workflow verified")
        with page.expect_response(
            lambda response: "/skills" in response.url
            and response.request.method == "POST"
        ) as response_info:
            form.get_by_role("button", name="Speichern").click()
        response = response_info.value
        if not response.ok:
            raise RuntimeError(response.text())
        page.get_by_text("Browser Test Skill", exact=True).wait_for()

        page.get_by_role("button", name="Revisionen").click()
        page.get_by_text("Revision 1", exact=True).wait_for()
        page.screenshot(path=screenshot_path, full_page=True)

        profile_id = page.locator("#profileSelect").input_value()
        skill_id = page.locator(".card.active").get_attribute("data-id")
        print(json.dumps({"profile_id": profile_id, "skill_id": skill_id}))
        browser.close()


if __name__ == "__main__":
    main()
