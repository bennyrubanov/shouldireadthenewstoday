###### import libraries and api keys ######

import os, requests, json
from flask import Flask, request, jsonify

#import VADER sentiment analysis
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
sentimentAnalyzer = SentimentIntensityAnalyzer()

from google.cloud import translate_v2 as translate
from google.cloud import storage
from google.oauth2 import service_account

# Load the path to the credentials file from the environment variable
#credentials_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS_PATH']
googleAppCredentials = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
gcp_json_credentials_dict = json.loads(googleAppCredentials)

# Open and load the JSON credentials file directly
# with open(credentials_path, 'r') as f:
#     gcp_json_credentials_dict = json.load(f)

# Create credentials and client
# Explicitly create credentials
credentials = service_account.Credentials.from_service_account_info(gcp_json_credentials_dict)

# Create the client with explicit credentials
client = storage.Client(credentials=credentials)

translate_client = translate.Client(credentials=credentials)


###### flask app launch ######
app = Flask(__name__)


@app.route('/result', methods=['GET', 'POST'])
def result():
  if request.method == 'POST':
    tolerance_from_user = int(request.form.get('tolerance'))
    country_from_user = request.form.get('countryDropdown')

    if not country_from_user:
      error_message = "Oh no! You forgot to put in your country of interest."
      return jsonify({'error': error_message})

    print(f"""user tolerance: {tolerance_from_user}""")
    print(f"""user-selected country: {country_from_user}""")
    articles = fetch_news_articles(country_from_user)

    numArticles = 0
    total_article_sentiment_polarity = 0

    # Iterate through the results of the asynchronous generator
    for result in sentimentAnalysis(articles):
      #print(f"""result in sentimentAnalysis(articles): {result['average_sentiment']}""")
      this_article_sentiment_polarity = result['this_article_sentiment_polarity']
      numArticles += float(1)
      total_article_sentiment_polarity += this_article_sentiment_polarity
      
    average_sentiment = float(total_article_sentiment_polarity / numArticles)
    print(f"average sentiment after iterating through results of async generator: {average_sentiment}")

    # Normalize the average sentiment calculation
    normalized_average_sentiment = ((average_sentiment + 1) / 2) * 10  # To move from range -1 to 1, to 0 to 2, to 0 to 1, and then 0 to 10
    print(f"normalized average sentiment: {normalized_average_sentiment}")

    #final calculations of tolerance score using linear regression model https://docs.google.com/spreadsheets/d/13YoMFgr4G3KCnPvMfEpkAM-h2onmjtut74ge3aSl41s/edit?usp=sharing
    overall_tolerance_score = -33.43614719 + (8.398268398 * normalized_average_sentiment) + (8.262987013 * tolerance_from_user)
    print(f"overall tolerance score: {overall_tolerance_score}")

    message = ""
    if tolerance_from_user <= 0:
      message += "Your tolerance is quite low... news generally may not be your thing, friend. Let's check the headlines though...\n"
      if normalized_average_sentiment >= 9:
        message += "\n Hey, looks like you're in luck! The set of articles analyzed are looking mostly positive or neutral. You're probably safe to read the news today, but given you're fragile, proceed with caution 👀"
      else:
        message += "\n\n I'm seeing some negative articles. Given you're fragile, I don't recommend reading the news today 💗"
    elif tolerance_from_user == 10:
      message += "You can tolerate anything! Read the news!\n"
      if normalized_average_sentiment >= 9:
        message += "\n Oh, and also, the news is pretty much all positive anyways 🙂"
      elif normalized_average_sentiment <= 1:
        message += "\n That being said... the news is pretty 😟 today. Proceed with caution..."
    else:
      if normalized_average_sentiment >= 9:
        message += "Hey, looks like today, all articles are looking pretty positive! You're probably safe to read the news today.\n"
      elif normalized_average_sentiment <= 1:
        message += "The articles analyzed are generally quite negative. Proceed with caution!\n"
      else:
        if overall_tolerance_score >= 75:
          message += "Read the news. You'll be alright."
        elif overall_tolerance_score > 55 and overall_tolerance_score < 75:
          message += "Might be iffy. Read the news, but tread with caution."
        elif overall_tolerance_score > 45 and overall_tolerance_score < 55:
          message += "It's a close call. You may or may not like what you see today."
        elif overall_tolerance_score < 45 and overall_tolerance_score > 25:
          message += "Consider not reading the news. Might be tough."
        elif overall_tolerance_score <= 25:
          message += "Best to avoid reading the news today. It looks to be too negative for you."
    # Return the articles and sentiment analysis as JSON
    response_data = {
      'articles': articles,
      'ratio_bad_to_good': normalized_average_sentiment,
      'tolerance_score': overall_tolerance_score,
      'message': message  # Add the message key to the response_data dictionary
    }
    return jsonify(response_data)


@app.route('/', methods=['GET', 'POST'])
def index():

  page = ""
  f = open("templates/reveal_articles.html", "r")
  page = f.read()
  f.close()
  return page


@app.route('/about')
def about():
  page = ""
  f = open("templates/about.html", "r")
  page = f.read()
  f.close()
  return page


def fetch_news_articles(country):
  newsKey = os.environ['newsapi']
  pageSize = 10  # Number of articles to retrieve (you can adjust this number as needed)
  url = f"https://newsapi.org/v2/top-headlines?country={country}&apiKey={newsKey}&pageSize={pageSize}"
  result = requests.get(url)
  data = result.json()
  return data.get('articles', [])


def sentimentAnalysis(articles):

  ###### running Google Cloud Translate API + sentiment analysis package ######

  numArticles = 0
  total_article_sentiment_polarity = 0

  
  for article in articles:

    # Check if the article has a title
    if 'title' not in article or not article['title']:
      continue  # Skip this article if title is missing or empty
    #print(f"""article: {article}""")
    #pull in the article, pass it to google translate cloud API, print translated article
    print(f"""article title: {article["title"]}""")
    articleTitle = article["title"]
    translatedArticleObject = translate_client.translate(articleTitle)
    translatedArticleHeadlineText = translatedArticleObject["translatedText"]
    print(f"""translated article title: {translatedArticleHeadlineText}""")

    ##     print tests     ##
    #print(f"""translated article: {translatedArticleObject}""")
    #print("Text: {}".format(translatedArticleObject["input"]))
    #print("Translation: {}".format(translatedArticleObject["translatedText"]))
    #print("Detected source language: {}".format(translatedArticleObject["detectedSourceLanguage"]))
  
    #textBlob sentiment analysis 
    #prompt = TextBlob(f"""{translatedArticleHeadlineText}""")

    #VADER sentiment analysis
    sentiment_dict = sentimentAnalyzer.polarity_scores(f"""{translatedArticleHeadlineText}
    
    """)
    print()
    print(f"""compound value: {sentiment_dict["compound"]}""")
    this_article_sentiment_polarity = float(sentiment_dict["compound"])
    numArticles += float(1)
    total_article_sentiment_polarity += this_article_sentiment_polarity

    print(f"""this article sentiment polarity: {this_article_sentiment_polarity}""")
    print(f"""total article sentiment polarity: {total_article_sentiment_polarity}""")
    
    #create sentiment analysis property for each article dictionary and pass it through the yield function to the javascript in reveal_articles.html waiting to call it
    if this_article_sentiment_polarity >= -1 and this_article_sentiment_polarity < -0.5:
      article["sentiment"] = "Very Negative"
    elif this_article_sentiment_polarity >= -0.5 and this_article_sentiment_polarity < -0.25:
      article["sentiment"] = "Somewhat Negative"
    elif this_article_sentiment_polarity >= -0.25 and this_article_sentiment_polarity < -0.1:
      article["sentiment"] = "Slightly Negative"
    elif this_article_sentiment_polarity >= -0.1 and this_article_sentiment_polarity < 0.1:
      article["sentiment"] = "Neutral"
    elif this_article_sentiment_polarity >= 0.1 and this_article_sentiment_polarity < 0.25:
      article["sentiment"] = "Slightly Positive"
    elif this_article_sentiment_polarity >= 0.25 and this_article_sentiment_polarity < 0.5:
      article["sentiment"] = "Somewhat Positive"
    elif this_article_sentiment_polarity >= 0.5 and this_article_sentiment_polarity <= 1:
      article["sentiment"] = "Very Positive"

    print(f"""article sentiment: {article["sentiment"]}
    
    """)


    # Yield the result for each article one by one
    yield {
      'article': article,
      'this_article_sentiment_polarity': this_article_sentiment_polarity,
    }

  average_sentiment = float(total_article_sentiment_polarity / numArticles)
  print(f"average sentiment of articles: {average_sentiment}")
  print(f"num articles: {numArticles}")
  
  return average_sentiment, articles


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)
