# CN-Novel-Bookmark-Backup
## Note

This is only to extract the RAW title and translated title and not the whole novel itself.  I'm also not very familiar with web scraping, so this script was generated with the help of AI and should be treated as a small personal-use utility rather than a polished scraping tool.

# Bookmark Novel Title Extractor
I had difficulty backing up a lot of my bookmarks from raw CN novel websites, which has been unstable at times. The problem was that these website had human verification prompts and a simple web scraping to extract the raw title and translated title would not work. So this repository is a simple Python script for bypassing those prompts and extract novel titles from an exported Chrome bookmarks file.

The script filters bookmarks from a specific website domain, cleans the saved bookmark title, optionally translates it to English, and saves the results to a CSV file.

## Features

* Reads exported Chrome bookmarks in HTML format
* Filters bookmarks by target website/domain
* Extracts the saved bookmark title
* Cleans website-specific title text
* Translates titles to English
* Saves results to CSV
* Supports test mode for processing only the first few bookmarks

## Output

The generated CSV contains the following columns:

```text
novel_title_original,novel_title_english,url
```

## Requirements

Install the required Python packages:

```bash
python -m pip install beautifulsoup4 deep-translator
```

## Usage

1. Export your bookmarks from Chrome as an HTML file.
2. Place the bookmark file in the same directory as the script.
3. Edit the settings in the script:

```python
BOOKMARK_FILE = "Bookmarks.html"
TARGET_DOMAIN = "shubaowb.com"
OUTPUT_CSV = "backup_novel.csv"

TEST_LIMIT = 5  # Set to None to process all matching bookmarks
```

4. Run the script:

```bash
python extract_bookmark_titles.py
```

## Test Mode

By default, the script can process only the first few matching bookmarks:

```python
TEST_LIMIT = 5
```

To process all matching bookmarks, change it to:

```python
TEST_LIMIT = None
```

## Notes

This script does not scrape webpage content directly. Instead, it uses the bookmark titles saved in the exported Chrome bookmarks file. This avoids issues with sites that use Cloudflare, Turnstile, or other browser verification systems.

Translations are generated automatically and may not always perfectly match the original title meaning, so the original title is also saved in the CSV.
