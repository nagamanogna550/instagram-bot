# Instagram Bot (Selenium)

Automates Instagram workflows with Selenium WebDriver: login, caption drafting,
image upload, hashtag search, and scheduled liking / commenting / following with
randomised human-like delays and daily rate limits.

> **Warning:** automating Instagram violates its Terms of Use and can get an account
> restricted or banned. This project defaults to **dry-run mode** (no browser, no
> account). Use `--live` only with a throwaway test account. For legitimate
> publishing, Instagram offers the official Graph API.

## Safety features
- Dry-run by default; `--live` needs an explicit YES confirmation
- Daily caps (like 60, comment 10, follow 15, upload 2), saved to disk, reset each day
- Randomised delays (minimum 3 s, occasional longer pauses) and character-by-character typing
- Active-hours window (09:00-22:00) in live mode
- Credentials from `.env` or a prompt, never hard-coded
- Comments never repeat within a session; session actions are shuffled

## Setup
pip install -r requirements.txt
(Live mode also needs Google Chrome; Selenium downloads the driver automatically.)

## Usage
python main.py draft --topic "Sunset at the beach" --keywords sunset beach travel
python main.py run --hashtag travel --likes 5 --comments 2 --follows 2
python main.py upload --image photo.jpg --caption "Hello #world"
python main.py status
Add --live to use a real browser and account.

## Test
python test_bot.py

## Note
Instagram changes its page layout often, so the XPath selectors in bot.py may need updating.
