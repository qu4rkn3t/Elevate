import random
import requests
import pandas as pd
from alpaca import Alpaca
from textblob import TextBlob
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


class CONSTANTS:
    def __init__(self):
        self.sp500_top_100 = [
            "AAPL", "MSFT", "GOOG", "AMZN",
            "NVDA", "TSLA", "BRK.B", "V",
            "UNH", "JPM", "DIS", "PYPL",
            "NFLX", "IBM", "ORCL", "CSCO",
            "T", "CAT", "NKE"
        ]
        self.PRICE1 = -1
        self.PRICE2 = -1


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
        end_time = (
                datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%dT00:00:00Z")
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


def generate_random_date(start_year: int, end_year: int) -> tuple:
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    next_date = random_date + timedelta(days=1)
    return (random_date.strftime("%Y-%m-%d"), next_date.strftime("%Y-%m-%d"))


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


def aggregate_bars(stock_bars, period='1H'):
    df = pd.DataFrame(stock_bars)
    df['t'] = pd.to_datetime(df['t'])
    df.set_index('t', inplace=True)
    resampled = df.resample(period).agg({
        'o': 'first',
        'c': 'last',
        'h': 'max',
        'l': 'min',
    }).dropna().reset_index()
    return resampled.to_dict(orient='records')


def plot_data(stock_bars, symbol, path):
    aggregated_bars = aggregate_bars(stock_bars)
    timestamps = [bar['t'] for bar in aggregated_bars]
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, bar in enumerate(aggregated_bars):
        open_price = bar['o']
        close_price = bar['c']
        high_price = bar['h']
        low_price = bar['l']
        color = 'lime' if close_price > open_price else 'red'
        ax.plot([i, i], [low_price, high_price], color='white', linewidth=1, alpha=0.8)
        rect = Rectangle((i - 0.3, min(open_price, close_price)), 0.6, abs(open_price - close_price), color=color, alpha=0.8)
        ax.add_patch(rect)
    ax.set_xticks(range(len(aggregated_bars)))
    ax.set_xticklabels([timestamps[i].strftime('%Y-%m-%d %H:%M') for i in range(len(timestamps))], rotation=45, ha='right', color='white')
    ax.set_title(f'{symbol}', color='white', fontsize=14)
    ax.set_xlabel('Time', color='white', fontsize=12)
    ax.set_ylabel('Price', color='white', fontsize=12)
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    fig.patch.set_facecolor('black')
    plt.tight_layout()
    plt.savefig(f'static/{path}', dpi=300)
    plt.close(fig)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/game', methods=['GET', 'POST'])
def game():
    if request.method == 'POST':
        choice = request.form.get('choice')
        print(choice)
        win = True
        if (choice == 'buy' and constant.PRICE2 < constant.PRICE1) or (choice == 'sell' and constant.PRICE2 > constant.PRICE1):
            win = False
        print(win)
        return redirect(url_for('results', win=win))
    alpaca_client = AlpacaAPIClient(
        api_key=Alpaca.APCA_API_KEY_ID,
        secret_key=Alpaca.APCA_API_SECRET_KEY
    )
    symbol = None
    stock_data = {'bars': None}
    stock_data2 = {'bars': None}
    news_data = {'news': []}
    while True:
        symbol = random.choice(constant.sp500_top_100)
        random_date, next_date = generate_random_date(start_year=2020, end_year=2024)
        stock_data = alpaca_client.get_stock_data(symbol, random_date)
        stock_data2 = alpaca_client.get_stock_data(symbol, next_date)
        news_data = alpaca_client.get_news_data(symbol, random_date)
        if stock_data['bars'] is not None and stock_data2['bars'] is not None and len(news_data['news']) > 0:
            break
    indicator = Indicators(stock_data['bars'])
    open_price = stock_data['bars'][0]['c']
    closing_price = stock_data['bars'][-1]['c']
    constant.PRICE1 = closing_price
    constant.PRICE2 = stock_data2['bars'][0]['c']
    for bar in stock_data2['bars']:
        constant.PRICE2 = max(constant.PRICE2, bar['c'])
    print(constant.PRICE2)
    percent_change = (closing_price - open_price) / open_price * 100
    sentiment = get_sentiment(news_data['news'])
    plot_data(stock_bars=stock_data['bars'], symbol=symbol, path='graph1.png')
    plot_data(stock_bars=stock_data2['bars'], symbol=symbol, path='graph2.png')
    res = {
        'symbol': symbol,
        'closing_price': closing_price,
        'percent_change': float(str(round(percent_change, 2))),
        'sentiment': float(str(round(sentiment, 2))),
        'simple_moving_average': float(str(round(indicator.simple_moving_average(), 2))),
        'average_true_range': float(str(round(indicator.average_true_range(), 2)))
    }
    return render_template('game.html', res=res, plot_url=url_for('static', filename='graph1.png'))


@app.route('/results')
def results():
    win = request.args.get('win', 'false').lower() == 'true'
    percent_change = float(str(round((constant.PRICE2 - constant.PRICE1) / constant.PRICE1 * 100, 2)))
    return render_template('results.html', win=win, price1=constant.PRICE1, price2=constant.PRICE2, percent_change=percent_change, plot_url=url_for('static', filename='graph2.png'))


if __name__ == '__main__':
    global constant
    constant = CONSTANTS()
    app.run(debug=True)
