"""Generate deterministic text and image-only PDF integration fixtures."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(os.environ.get("PDF_FIXTURE_OUTPUT_DIR", "/data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOB_SENTENCE = "Build reliable data platforms with Python, SQL and cloud technologies."

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.set_content(f"<h1>Data Engineer</h1><p>{JOB_SENTENCE * 20}</p>")
    page.pdf(path=OUTPUT_DIR / "text-job.pdf", format="A4")

    page.set_content(
        """
        <canvas id="job" width="1200" height="1600"></canvas>
        <script>
          const context = document.getElementById("job").getContext("2d");
          context.font = "32px sans-serif";
          context.fillText("Data Engineer", 50, 80);
          context.font = "22px sans-serif";
          for (let line = 0; line < 20; line += 1) {
            context.fillText(
              "Build reliable data platforms with Python SQL and cloud.",
              50,
              140 + line * 45
            );
          }
        </script>
        """
    )
    page.pdf(path=OUTPUT_DIR / "image-job.pdf", format="A4")
    browser.close()
