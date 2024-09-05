import json
import nltk
import os
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
from heapq import nlargest
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

# Set NLTK data path to the current directory
nltk.data.path.append(os.getcwd())

# Download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    print("NLTK data downloaded successfully.")
except Exception as e:
    print(f"Failed to download NLTK data: {e}")
    print("Using fallback summarization method.")

def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

def summarize_text(text, sentences_count=5):
    # Tokenize the text into sentences and words
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())

    # Remove stopwords and lemmatize
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    pos_tags = nltk.pos_tag(words)
    words = [lemmatizer.lemmatize(word, get_wordnet_pos(pos)) for word, pos in pos_tags 
             if word.isalnum() and word not in stop_words]

    # Calculate word frequencies
    freq = FreqDist(words)

    # Score sentences based on word frequencies
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        for word, pos in nltk.pos_tag(word_tokenize(sentence.lower())):
            word = lemmatizer.lemmatize(word, get_wordnet_pos(pos))
            if word in freq:
                if i not in sentence_scores:
                    sentence_scores[i] = freq[word]
                else:
                    sentence_scores[i] += freq[word]

    # Select top sentences
    summary_sentences = nlargest(sentences_count, sentence_scores, key=sentence_scores.get)
    summary = ' '.join([sentences[i] for i in sorted(summary_sentences)])

    return summary
def process_json_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processed_data = []

    for item in data:
        url = item['URL']
        content = item['content']

        title = url.replace("https://portal.thirdweb.com/typescript/v5/", "").strip("/")
        
        summarized_content = summarize_text(content)

        processed_item = {
            "title": title,
            "content": summarized_content
        }

        processed_data.append(processed_item)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)

    print(f"Processed data saved to {output_file}")

# Usage
input_file = 'scraped_data.json'
output_file = 'processed_data.json'
process_json_file(input_file, output_file)