###### import libraries and api keys ######

import os, requests
from flask import Flask, request, jsonify
from textblob import TextBlob

#os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

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

    articles = fetch_news_articles(country_from_user)
    negative_headlines_ratios = []  # Store the ratios in a list

    # Iterate through the results of the asynchronous generator
    for result in sentimentAnalysis(articles):
      average_sentiment = result['average_sentiment']

    # Normalize the average sentiment calculation
    normalized_average_sentiment = ((average_sentiment + 1) / 2) * 10  # To move from range -1 to 1, to 0 to 1, and then 0 to 10
    print(f"normalized average sentiment: {normalized_average_sentiment}")
    overall_tolerance_score = 10 * (
      10 - normalized_average_sentiment) * (tolerance_from_user / 10)

    message = ""
    if tolerance_from_user == 0:
      message += "Your tolerance is quite low... news generally may not be your thing, friend. Let's check the headlines though...\n"
      if normalized_average_sentiment == 0:
        message += "\n Hey, looks like you're in luck! All articles are looking either positive or neutral. You're probably safe to read the news today, but given you're fragile, proceed with caution 👀"
      else:
        message += "\n\n I'm seeing some negative articles. Given you're fragile, I don't recommend reading the news today 💗"
    elif tolerance_from_user == 10:
      message += "You can tolerate anything! Read the news!\n"
      if normalized_average_sentiment == 0:
        message += "\n Oh, and also, the news is all positive anyways 🙂"
      elif normalized_average_sentiment == 10:
        message += "\n That being said... the news is pretty poopy today. Proceed with caution..."
    else:
      if normalized_average_sentiment == 0:
        message += "Hey, looks like today, all articles are looking pretty positive! You're probably safe to read the news today.\n"
      elif normalized_average_sentiment == 10:
        message += "All articles are negative. Proceed with caution!\n"
      else:
        if overall_tolerance_score >= 75:
          message += "Read the news. You'll be alright."
        elif overall_tolerance_score > 50 and overall_tolerance_score < 75:
          message += "Might be iffy. Read the news, but tread with caution."
        elif overall_tolerance_score == 50:
          message += "50/50. You may or may not like what you see today."
        elif overall_tolerance_score < 50 and overall_tolerance_score > 25:
          message += "Consider not reading the news. Doesn't look too fun."
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
  pageSize = 5  # Number of articles to retrieve (you can adjust this number as needed)
  url = f"https://newsapi.org/v2/top-headlines?country={country}&apiKey={newsKey}&pageSize={pageSize}"
  result = requests.get(url)
  data = result.json()
  #print(data.get('articles', []))
  return data.get('articles', [])


def sentimentAnalysis(articles):

  #REPLICATE_API_TOKEN = os.environ['REPLICATE_API_TOKEN']

  ###### running llama2 from replicate ######

  numArticles = 0
  article_sentiment_polarity = 0

  for article in articles:
    prompt = TextBlob(f"""{article["title"]}""")
    article_sentiment_polarity += float(prompt.sentiment.polarity)
    numArticles += 1

    print(f"""{article["title"]}""")
    print(f"""{article_sentiment_polarity}""")

    average_sentiment = article_sentiment_polarity / numArticles
    
    # Yield the result for each article one by one
    yield {
      'article': article,
      'average_sentiment': average_sentiment,
    }

  average_sentiment = article_sentiment_polarity / numArticles
  print(f"average sentiment of articles: {average_sentiment}")

  return average_sentiment, articles


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)
