import random
import requests
from alpaca import Alpaca
from textblob import TextBlob
from datetime import datetime, timedelta
from flask import Flask, render_template, request

app = Flask(__name__)

sp500_top_100 = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "BRK.B", "V", "UNH", "JPM", "DIS", "PYPL", "NFLX", "IBM", "ORCL", "CSCO", "T", "CAT", "NKE"
]


def generate_random_date(start_year: int, end_year: int) -> tuple:
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    next_date = random_date + timedelta(days=1)
    return (
        random_date.strftime("%Y-%m-%d"),
        next_date.strftime("%Y-%m-%d")
    )


def get_sentiment(news_data: list) -> float:
    if len(news_data) > 0:
        total = 0
        count = 0
        for article in news_data:
            header_blob = TextBlob(article['headline']).sentiment.polarity
            summary_blob = TextBlob(article['summary']).sentiment.polarity
            total += (header_blob * 0.2 + summary_blob * 0.8)
            count += 1
        return (total / count) * 10 + 1
    return 0


class AlpacaAPIClient:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.stock_base_url = "https://data.alpaca.markets/v2"
        self.news_base_url = "https://data.alpaca.markets/v1beta1"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }

    def get_stock_data(self, symbol: str, date: str) -> dict:
        start_time = f"{date}T00:00:00Z"
        end_time = f"{date}T23:59:59Z"
        url = f"{self.stock_base_url}/stocks/{symbol}/bars"
        params = {
            "start": start_time,
            "end": end_time,
            "timeframe": "1Min"
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stock data: {e}")
            return None

    def get_news_data(self, symbol: str, date: str) -> dict:
        start_time = f"{date}T00:00:00Z"
        end_time = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        url = f"{self.news_base_url}/news"
        params = {
            "start": start_time,
            "end": end_time,
            "symbols": symbol,
            "sort": "asc",
            "limit": 50,
            "include_content": "false"
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news data: {e}")
            return None


class Indicators:
    def __init__(self, bars):
        self.bars = bars
        self.period = len(bars)
        self.high_prices = [bar['h'] for bar in bars]
        self.low_prices = [bar['l'] for bar in bars]
        self.opening_prices = [bar['o'] for bar in bars]
        self.closing_prices = [bar['c'] for bar in bars]

    def simple_moving_average(self):
        return sum(self.closing_prices) / self.period

    def average_true_range(self):
        true_ranges = []
        for i in range(1, self.period):
            high_low = self.high_prices[i] - self.low_prices[i]
            high_close = abs(self.high_prices[i] - self.closing_prices[i - 1])
            low_close = abs(self.low_prices[i] - self.closing_prices[i - 1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        return sum(true_ranges) / self.period


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/game')
def game():
    alpaca_client = AlpacaAPIClient(
        api_key=Alpaca.APCA_API_KEY_ID,
        secret_key=Alpaca.APCA_API_SECRET_KEY
    )
    symbol = None
    stock_data = {'bars': None}
    stock_data2 = {'bars': None}
    news_data = {'news': []}
    while True:
        symbol = random.choice(sp500_top_100)
        random_date, next_date = generate_random_date(start_year=2020, end_year=2024)
        stock_data = alpaca_client.get_stock_data(symbol, random_date)
        stock_data2 = alpaca_client.get_stock_data(symbol, next_date)
        news_data = alpaca_client.get_news_data(symbol, random_date)
        if stock_data['bars'] != None and stock_data2['bars'] != None and len(news_data['news']) > 0:
            break
    indicator = Indicators(stock_data['bars'])
    open_price = stock_data['bars'][0]['c']
    closing_price = stock_data['bars'][-1]['c']
    percent_change = (abs(closing_price - open_price) / open_price) * 100
    sentiment = get_sentiment(news_data['news'])
    res = {
        'symbol': symbol,
        'closing_price': closing_price,
        'percent_change': percent_change,
        'sentiment': str(round(sentiment, 2)),
        'simple_moving_average': indicator.simple_moving_average(),
        'average_true_range': indicator.average_true_range()
    }
    return render_template('game.html', res=res)


@app.route('/results')
def results():
    correct = request.args.get('correct', 'false')
    return render_template('results.html', correct == correct)


if __name__ == '__main__':
    app.run(debug=True)
