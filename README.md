# stock_price_predictor

Overview

This project utilizes machine learning techniques to predict stock movements based on sentiment analysis of Reddit posts. The model scrapes Reddit data from the "stocks" subreddit, analyzes sentiment using Natural Language Processing (NLP), and then uses this sentiment and historical stock data to predict stock prices. Both Random Forest and Long Short-Term Memory (LSTM) models are trained to forecast stock movements.


Features

Reddit Data Scraping: Scrapes the latest posts from the "stocks" subreddit.
Sentiment Analysis: Analyzes sentiment from Reddit post titles using the VADER sentiment analysis tool from the nltk library.
Stock Data: Retrieves historical stock price data for the specified ticker using yfinance.
Machine Learning Models: Trains Random Forest and LSTM models to predict stock prices based on sentiment and previous stock prices.
Model Evaluation: Evaluates model performance using various metrics, including RMSE, MAE, R², EVS, MAPE, and MSLE.
Visualization: Displays a comparison between predicted and actual stock prices.


Requirements
Before running the project, you need to install the required dependencies.

Dependencies

pandas
numpy
praw
yfinance
nltk
scikit-learn
tensorflow
matplotlib

You can install all the dependencies by running the following command:

pip install -r requirements.txt

Setup
Create Reddit API Credentials:

To access Reddit data, you need a Reddit API client.
Go to Reddit Developer Portal and create an application to get your client_id, client_secret, and user_agent.


Install Python Dependencies: Install the necessary libraries:

pip install -r requirements.txt
Set Up API Keys: In the script (main.py), replace the placeholders for the Reddit API keys (CLIENT_ID, CLIENT_SECRET, USER_AGENT) with your actual credentials.

Running the Code
1. Run the Script:
To run the entire pipeline, including scraping Reddit data, analyzing sentiment, and training the models, execute the main.py script:

python main.py
This will:

Scrape Reddit data from the "stocks" subreddit.
Perform sentiment analysis on the post titles.
Fetch historical stock data for the specified ticker.
Merge Reddit sentiment data with stock data.
Train and evaluate both Random Forest and LSTM models.
Display evaluation metrics and plot the predictions vs. actual stock prices.
2. Jupyter Notebooks:
For a step-by-step breakdown of the project, you can run the provided Jupyter notebooks. These will guide you through each part of the process, including data scraping, preprocessing, model training, and evaluation:

Data_Scraping.ipynb: Demonstrates how to scrape Reddit data and analyze sentiment.
Data_Preprocessing.ipynb: Shows how to merge the Reddit sentiment with stock data and prepare the dataset for model training.
Model_Training.ipynb: Trains and evaluates both Random Forest and LSTM models, including the evaluation metrics and visualization of predictions.

Example Output
The models will display their evaluation metrics on the terminal. For instance, you might see something like:

Random Forest Metrics: RMSE=5.03, MAE=4.12, R²=0.85, EVS=0.86, MAPE=3.45%, MSLE=0.12
LSTM Metrics: RMSE=4.75, MAE=3.98, R²=0.87, EVS=0.88, MAPE=3.25%, MSLE=0.10


License
This project is licensed under the MIT License.



