# shouldireadthenewstoday

How this tool works
Step 1: The app queries an API from newsapi.org to pull in a bunch of news headlines from the country that you, the user, chose.

Step 2: It feeds those headlines to an AI model, (in this case, Meta's Llama 2). The AI model conducts a sentiment analysis on the headlines (rating them "Positive", "Negative", or "Neutral").

Step 3: Finally, the app calculates a "bad to good headlines" ratio, and using a pre-defined formula, along with the tolerance of bad news provided by the user, recommends whether or not the user should read the news today!
