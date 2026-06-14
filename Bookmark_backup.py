# %%
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from seleniumbase import SB
from deep_translator import GoogleTranslator
import csv
import time

# =========================
# User settings
# =========================

BOOKMARK_FILE = "Bookmark.html"
TARGET_DOMAIN = "shubaowb.com"
OUTPUT_CSV = "backup_novels.csv"

TEST_LIMIT = None  # Set to None later to process all bookmarks

TRANSLATE_TITLE = True
DELAY_SECONDS = 2

# Optional: keeps browser session/cookies between runs
USER_DATA_DIR = "seleniumbase_chrome_profile"


# =========================
# Domain/bookmark helpers
# =========================


def normalize_domain(value: str) -> str:
    """
    Normalize a domain or URL.

    Examples:
    "https://shubaowb.com" -> "shubaowb.com"
    "www.shubaowb.com" -> "shubaowb.com"
    """
    value = value.strip().lower()
    parsed = urlparse(value)

    if parsed.netloc:
        domain = parsed.netloc
    else:
        domain = value

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def get_domain_from_url(url: str) -> str:
    """
    Extract the domain from a URL.
    """
    parsed = urlparse(url.strip())
    return normalize_domain(parsed.netloc)


def find_bookmarks_by_domain(bookmark_file: str, target_domain: str):
    """
    Find bookmarks that belong to the target domain or its subdomains.
    """
    bookmark_file = Path(bookmark_file)
    target_domain = normalize_domain(target_domain)

    if not bookmark_file.exists():
        raise FileNotFoundError(f"Bookmark file not found: {bookmark_file}")

    with open(bookmark_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    matches = []

    for link in soup.find_all("a"):
        url = link.get("href", "").strip()
        bookmark_title = link.get_text(strip=True)

        if not url:
            continue

        try:
            domain = get_domain_from_url(url)
        except Exception:
            continue

        if domain == target_domain or domain.endswith("." + target_domain):
            matches.append(
                {
                    "bookmark_title": bookmark_title,
                    "url": url,
                    "domain": domain,
                }
            )

    return matches


# =========================
# Title extraction helpers
# =========================


def clean_title(title: str) -> str:
    """
    Clean shubaowb title text.
    """
    if not title:
        return ""

    title = " ".join(title.split())

    remove_parts = [
        " - 书宝网完本",
        "_书宝网完本",
        " | 书宝网完本",
        "书宝网完本",
    ]

    for part in remove_parts:
        title = title.replace(part, "")

    return title.strip(" -_|")


def extract_title_from_html(html: str) -> str:
    """
    Extract novel title from page HTML.
    Prefer h1 because it is often cleaner than the browser title.
    """
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if text:
            return clean_title(text)

    if soup.title and soup.title.get_text(strip=True):
        return clean_title(soup.title.get_text(strip=True))

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return clean_title(og_title["content"])

    return "TITLE_NOT_FOUND"


def translate_to_english(text: str) -> str:
    """
    Translate extracted title to English.
    """
    if not text or text == "TITLE_NOT_FOUND":
        return ""

    try:
        translated = GoogleTranslator(source="auto", target="en").translate(text)

        return translated

    except Exception as e:
        return f"TRANSLATION_ERROR: {e}"


# =========================
# Cloudflare/manual check helper
# =========================


def page_may_have_challenge(html: str) -> bool:
    """
    Detect possible Cloudflare/Turnstile challenge page.
    This only detects it; it does not bypass it.
    """
    lower_html = html.lower()

    indicators = [
        "cf-turnstile",
        "challenges.cloudflare.com",
        "verify you are human",
        "checking if the site connection is secure",
        "just a moment",
    ]

    return any(indicator in lower_html for indicator in indicators)


def wait_for_manual_verification():
    """
    Pause so you can manually complete verification in the browser.
    """
    print()
    print("A Cloudflare/Turnstile challenge may be present.")
    print("Please complete it manually in the browser window.")
    input("After the real page loads, press ENTER here to continue...")
    print()


# =========================
# SeleniumBase page processing
# =========================


def process_page(sb, bookmark: dict) -> dict:
    """
    Open one bookmark URL, extract original title, translate it,
    and return a result dictionary.
    """
    url = bookmark["url"]

    try:
        sb.uc_open_with_reconnect(url, 4)
        sb.sleep(4)

        html = sb.get_page_source()

        if page_may_have_challenge(html):
            wait_for_manual_verification()
            sb.sleep(3)
            html = sb.get_page_source()

        novel_title_original = extract_title_from_html(html)

        # Fallback to browser title if needed
        if novel_title_original == "TITLE_NOT_FOUND":
            try:
                novel_title_original = clean_title(sb.get_page_title())
            except Exception:
                novel_title_original = "TITLE_NOT_FOUND"

        if TRANSLATE_TITLE:
            novel_title_english = translate_to_english(novel_title_original)
        else:
            novel_title_english = ""

        status = sb.execute_script("""
            const entries = window.performance.getEntriesByType('navigation');
            return entries.length ? entries[0].responseStatus : null;
        """)

        return {
            "bookmark_title": bookmark["bookmark_title"],
            "url": url,
            "domain": bookmark["domain"],
            "novel_title_original": novel_title_original,
            "novel_title_english": novel_title_english,
            "page_status": status,
            "error": "",
        }

    except Exception as e:
        return {
            "bookmark_title": bookmark["bookmark_title"],
            "url": url,
            "domain": bookmark["domain"],
            "novel_title_original": "",
            "novel_title_english": "",
            "page_status": "",
            "error": str(e),
        }


# =========================
# CSV helper
# =========================


def save_results_to_csv(results, output_csv: str):
    fieldnames = [
        "novel_title_original",
        "novel_title_english",
        "url",
    ]

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            writer.writerow(
                {
                    "novel_title_original": row.get("novel_title_original", ""),
                    "novel_title_english": row.get("novel_title_english", ""),
                    "url": row.get("url", ""),
                }
            )


# =========================
# Main workflow
# =========================


def main():
    print(f"Searching bookmarks for domain: {TARGET_DOMAIN}")

    bookmarks = find_bookmarks_by_domain(
        BOOKMARK_FILE,
        TARGET_DOMAIN,
    )

    print(f"Found {len(bookmarks)} matching bookmarks")

    if TEST_LIMIT is not None:
        bookmarks = bookmarks[:TEST_LIMIT]
        print(f"Test mode enabled. Processing first {len(bookmarks)} bookmarks only.")

    if not bookmarks:
        print("No matching bookmarks found. Exiting.")
        return

    results = []

    with SB(
        uc=True,
        test=True,
        browser="chrome",
        headless=False,
        user_data_dir=USER_DATA_DIR,
    ) as sb:

        for idx, bookmark in enumerate(bookmarks, start=1):
            print()
            print(f"[{idx}/{len(bookmarks)}] Opening:")
            print(bookmark["url"])

            result = process_page(sb, bookmark)
            results.append(result)

            save_results_to_csv(results, OUTPUT_CSV)

            print("Original title:", result["novel_title_original"])
            print("English title:", result["novel_title_english"])

            if result["error"]:
                print("Error:", result["error"])

            print(f"Saved progress to: {OUTPUT_CSV}")

            time.sleep(DELAY_SECONDS)

    print()
    print(f"Done. Saved {len(results)} records to:")
    print(OUTPUT_CSV)


if __name__ == "__main__":
    main()
# %%
