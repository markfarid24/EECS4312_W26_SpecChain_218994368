"""imports or reads your raw dataset; if you scraped, include scraper here"""

from google_play_scraper import reviews, Sort
import json
import os

APP_ID = "bot.touchkin"
APP_NAME = "Wysa: Mental Wellbeing AI"
OUTPUT_FILE = "data/reviews_raw.jsonl"
TARGET_COUNT = 2000

def main():
    os.makedirs("data", exist_ok=True)

    all_reviews = []
    continuation_token = None

    while len(all_reviews) < TARGET_COUNT:
        batch, continuation_token = reviews(
            APP_ID,
            lang="en",
            country="ca",
            sort=Sort.NEWEST,
            count=min(200, TARGET_COUNT - len(all_reviews)),
            continuation_token=continuation_token,
        )

        if not batch:
            break

        all_reviews.extend(batch)

        if continuation_token is None:
            break

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for i, r in enumerate(all_reviews, start=1):
            record = {
                "review_id": str(r.get("reviewId", f"review_{i}")),
                "user_name": r.get("userName", ""),
                "score": r.get("score", None),
                "review_text": r.get("content", ""),
                "review_date": str(r.get("at", "")),
                "thumbs_up_count": r.get("thumbsUpCount", 0),
                "app_name": APP_NAME,
                "app_id": APP_ID,
                "source": "Google Play"
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Saved {len(all_reviews)} reviews to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()