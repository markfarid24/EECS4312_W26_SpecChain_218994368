# EECS4312\_W26\_SpecChain\_218994368

Mark Farid

## Instructions

### Application: \[Wysa: Mental Wellbeing AI]



#### Data Collection Method

The dataset was collected from the Google Play Store using the `google-play-scraper` Python package.



#### Dataset

\- `reviews_raw.jsonl` contains the collected raw Google Play reviews for Wysa.

\- `reviews_clean.jsonl` contains the cleaned and preprocessed review dataset.

\- The original raw dataset contains 2000 reviews.

\- The final cleaned dataset contains 1650 reviews.



#### Repository Structure

\- `data/` contains raw reviews, cleaned reviews, metadata, and grouped review files

\- `personas/` contains manual, automated, and hybrid persona files

\- `spec/` contains manual, automated, and hybrid specifications

\- `tests/` contains manual, automated, and hybrid validation tests

\- `metrics/` contains all metrics files and the final comparison summary

\- `prompts/` contains the automated prompt used for Groq-based generation

\- `src/` contains the executable Python scripts

\- `reflection/` contains the final reflection



#### How to Run

1\. Clone and open the project in command prompt:
git clone https://github.com/markfarid24/EECS4312_W26_SpecChain_218994368.git

cd EECS4312_W26_SpecChain_218994368



2\. Install required packages:

pip install google-play-scraper nltk num2words requests



3\. Set the Groq API key in Command Prompt:

set GROQ\_API\_KEY= "paste key here"



4\. Run repository validation:

python src/00\_validate\_repo.py



5\. Run the cleaning script directly if needed:

python src/02\_clean.py



6\. Run the automated pipeline from start to finish:

python src/run\_all.py



