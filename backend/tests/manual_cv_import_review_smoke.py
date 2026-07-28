"""Manual browser smoke test for controlled CV suggestion review."""

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
        page.locator("#displayName").fill("CV-Review-Smoke-Test")
        page.locator("#profileReason").fill("Automatischer CV-Prüftest")
        page.locator("#saveProfile").click()
        page.wait_for_function(
            """() => [...document.querySelector('#profileSelect').options]
                .some(option => option.textContent.includes('CV-Review-Smoke-Test'))"""
        )
        profile_id = page.locator("#profileSelect").input_value()

        page.locator('[data-resource="cv-imports"]').click()
        page.locator("#newEntry").click()
        page.locator("#cancelCvImport").click()
        page.locator("#cvImportDialog").wait_for(state="hidden")
        page.locator("#newEntry").click()
        page.locator("#structuredCv").fill(
            json.dumps(
                {
                    "profile": {"summary": "Nicht kanonisch übernehmen"},
                    "skills": {
                        "categories": [
                            {
                                "category": "Programming",
                                "skills": ["Browser CV Skill", "Browser Bulk Skill"],
                            }
                        ],
                        "languages": [],
                    },
                    "work_experience": [],
                    "education": [],
                    "certificates": [],
                    "references": [],
                }
            )
        )
        with page.expect_response(
            lambda response: "/cv-imports/structured" in response.url
            and response.request.method == "POST"
        ) as response_info:
            page.get_by_role("button", name="Vorschläge erzeugen").click()
        result = response_info.value.json()
        if not response_info.value.ok:
            raise RuntimeError(json.dumps(result))
        page.get_by_text("Browser CV Skill", exact=True).wait_for()
        page.locator("#selectAllCv").check()
        page.locator("#applySelectedCv").click()
        page.get_by_text("Übernommen", exact=True).first.wait_for()
        page.locator('[data-resource="skills"]').click()
        page.get_by_text("Browser CV Skill", exact=True).wait_for()
        page.get_by_text("Browser Bulk Skill", exact=True).wait_for()
        page.locator(".card", has_text="Browser CV Skill").click()
        assert (
            page.locator('[name="category"] option:checked').text_content()
            == "Programmiersprachen"
        )
        assert page.locator('[name="proficiency_level"]').evaluate(
            "(element) => element.tagName"
        ) == "SELECT"
        page.screenshot(path=screenshot_path, full_page=False)

        print(
            json.dumps(
                {
                    "profile_id": profile_id,
                    "batch_id": result["id"],
                    "suggestion_ids": [item["id"] for item in result["suggestions"]],
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
