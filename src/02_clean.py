"""cleans raw data & make clean dataset"""

import json
import os
import re
import unicodedata
from collections import OrderedDict

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
except ImportError:
    raise ImportError("Please install nltk first!")

try:
    from num2words import num2words
except ImportError:
    raise ImportError("Please install num2words first!")


INPUT_FILE = "data/reviews_raw.jsonl"
OUTPUT_FILE = "data/reviews_clean.jsonl"
METADATA_FILE = "data/dataset_metadata.json"

APP_NAME = "Wysa: Mental Wellbeing AI"
APP_ID = "bot.touchkin"
MIN_WORDS = 3


def download_nltk_resources():
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)


def load_reviews(path):
    reviews = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reviews.append(json.loads(line))
    return reviews


def remove_duplicates(reviews):
    unique = OrderedDict()
    for r in reviews:
        key = (
            r.get("review_text", "").strip().lower(),
            r.get("score"),
            r.get("user_name", "").strip().lower(),
        )
        if key not in unique:
            unique[key] = r
    return list(unique.values())


def remove_emojis_and_specials(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


def convert_numbers_to_words(text):
    def repl(match):
        number = match.group()
        try:
            return " " + num2words(int(number)) + " "
        except Exception:
            return " "
    return re.sub(r"\b\d+\b", repl, text)


def clean_text(text, stop_words, lemmatizer):
    if not text or not text.strip():
        return ""

    text = remove_emojis_and_specials(text)
    text = convert_numbers_to_words(text)
    text = text.lower()
    # this removes punctuation and non-letters
    text = re.sub(r"[^a-z\s]", " ", text)
    # this removes extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()
    # this removes stop words
    tokens = [t for t in tokens if t not in stop_words]
    # this lemmatizes the reviews
    tokens = [lemmatizer.lemmatize(t) for t in tokens]

    return " ".join(tokens).strip()


def main():
    download_nltk_resources()
    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    os.makedirs("data", exist_ok=True)

    raw_reviews = load_reviews(INPUT_FILE)
    raw_count = len(raw_reviews)

    deduped_reviews = remove_duplicates(raw_reviews)
    deduped_count = len(deduped_reviews)

    cleaned_reviews = []
    empty_removed = 0
    short_removed = 0

    for r in deduped_reviews:
        original_text = r.get("review_text", "")
        cleaned_text = clean_text(original_text, stop_words, lemmatizer)

        if not cleaned_text:
            empty_removed += 1
            continue

        if len(cleaned_text.split()) < MIN_WORDS:
            short_removed += 1
            continue

        cleaned_record = {
            "review_id": r.get("review_id", ""),
            "user_name": r.get("user_name", ""),
            "score": r.get("score", None),
            "review_text": original_text,
            "cleaned_text": cleaned_text,
            "review_date": r.get("review_date", ""),
            "thumbs_up_count": r.get("thumbs_up_count", 0),
            "app_name": r.get("app_name", APP_NAME),
            "app_id": r.get("app_id", APP_ID),
            "source": r.get("source", "Google Play"),
        }
        cleaned_reviews.append(cleaned_record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in cleaned_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    metadata = {
        "app_name": APP_NAME,
        "app_id": APP_ID,
        "source": "Google Play Store",
        "collection_method": "Collected programmatically using google-play-scraper",
        "raw_review_count": raw_count,
        "deduplicated_review_count": deduped_count,
        "clean_review_count": len(cleaned_reviews),
        "filters": {
            "removed_empty_reviews": empty_removed,
            "removed_extremely_short_reviews": short_removed,
            "minimum_words_required": MIN_WORDS
        },
        "cleaning_steps": [
            "removed duplicates",
            "removed empty entries",
            "removed extremely short reviews",
            "removed punctuation",
            "removed special characters and emojis",
            "converted numbers to text",
            "removed extra whitespace",
            "converted text to lowercase",
            "removed stop words",
            "lemmatized reviews"
        ],
        "notes": "Reviews come from Google Play."
    }

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Raw reviews: {raw_count}")
    print(f"After deduplication: {deduped_count}")
    print(f"Final cleaned reviews: {len(cleaned_reviews)}")
    print(f"Saved cleaned reviews to {OUTPUT_FILE}")
    print(f"Saved metadata to {METADATA_FILE}")


if __name__ == "__main__":
    main()
