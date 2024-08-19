###### import libraries and api keys ######

import os, requests, json, replicate
from flask import Flask, request, jsonify, render_template

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
    for result in negativeHeadlinesRatioCalc(articles):
      negative_headlines_ratio = result['ratio_bad_to_good']
      negative_headlines_ratios.append(negative_headlines_ratio)

    # Calculate the overall negative headlines ratio
    overall_negative_headlines_ratio = sum(negative_headlines_ratios) / len(
      negative_headlines_ratios)
    normalized_negative_headlines_ratio = overall_negative_headlines_ratio * 10  # To put on a scale of 0-10
    overall_tolerance_score = 10 * (
      10 - normalized_negative_headlines_ratio) * (tolerance_from_user / 10)

    message = ""
    if tolerance_from_user == 0:
      message += "Your tolerance is quite low... news generally may not be your thing, friend. Let's check the headlines though...\n"
      if overall_negative_headlines_ratio == 0:
        message += "\n Hey, looks like you're in luck! All articles are looking either positive or neutral. You're probably safe to read the news today, but given you're fragile, proceed with caution 👀"
      else:
        message += "\n\n I'm seeing some negative articles. Given you're fragile, I don't recommend reading the news today 💗"
    elif tolerance_from_user == 10:
      message += "You can tolerate anything! Read the news!\n"
      if overall_negative_headlines_ratio == 0:
        message += "\n Oh, and also, the news is all positive anyways 🙂"
      elif overall_negative_headlines_ratio == 1:
        message += "\n That being said... the news is a pretty poopy today. Proceed with caution..."
    else:
      if overall_negative_headlines_ratio == 0:
        message += "Hey, looks like today, all articles are looking pretty positive! You're probably safe to read the news today.\n"
      elif overall_negative_headlines_ratio == 10:
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
          message += "Best to avoid reading the news today. It's quite negative."
    # Return the articles and sentiment analysis as JSON
    response_data = {
      'articles': articles,
      'ratio_bad_to_good': overall_negative_headlines_ratio,
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
  print(data.get('articles', []))
  return data.get('articles', [])


def negativeHeadlinesRatioCalc(articles):

  REPLICATE_API_TOKEN = os.environ['REPLICATE_API_TOKEN']

  ###### running llama2 from replicate ######

  numArticles = 0
  negativeArticles = 0
  neutralArticles = 0
  positiveArticles = 0

  for article in articles[:5]:
    prompt = (
      f"""Is the following headline positive, negative, or neutral? {article["title"]}"""
    )
    output = replicate.run(
      "a16z-infra/llama-2-13b-chat:d5da4236b006f967ceb7da037be9cfc3924b20d21fed88e1e94f19d56e2d3111",
      input={
        "prompt": prompt,
        "system_prompt":
        "You can only respond with one word: 'Positive', 'Negative', or 'Neutral'.",
        "max_new_tokens": 5
      })

    outputSTRING = ""

    for item in output:
      outputSTRING += item

    if "Negative" in outputSTRING:
      negativeArticles += 1
      article["sentiment"] = "Negative"
    elif "Neutral" in outputSTRING:
      neutralArticles += 1
      article["sentiment"] = "Neutral"
    elif "Positive" in outputSTRING:
      positiveArticles += 1
      article["sentiment"] = "Positive"

    numArticles += 1

    print(f"outputString: {outputSTRING}")
    print(f"number of negative articles: {negativeArticles}")
    print(f"number of neutral articles: {neutralArticles}")
    print(f"number of positive articles: {positiveArticles}")

    ratio_bad_to_good_headlines = negativeArticles / numArticles

    # Yield the result for each article one by one
    yield {
      'article': article,
      'ratio_bad_to_good': ratio_bad_to_good_headlines,
    }

  ratio_bad_to_good_headlines = negativeArticles / numArticles

  print(f"number of negative articles: {negativeArticles}")
  print(f"number of neutral articles: {neutralArticles}")
  print(f"number of positive articles: {positiveArticles}")
  print(f"ratio of bad to good headlines: {ratio_bad_to_good_headlines}")
  return ratio_bad_to_good_headlines, articles


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)
