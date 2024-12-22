import random
import requests
from alpaca import Alpaca
from textblob import TextBlob
from datetime import datetime, timedelta
from flask import Flask, render_template, request

app = Flask(__name__)

sp500_top_100 = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "BRK.B", "V", "UNH", "JPM",
    "DIS", "PYPL", "MA", "NFLX", "INTC", "BA", "GS", "IBM", "XOM", "JNJ",
    "HD", "MCD", "PFE", "KO", "PEP", "VZ", "WMT", "CVX", "ORCL", "CSCO",
    "T", "CAT", "ABT", "CVS", "MMM", "LLY", "RTX", "LOW", "ADBE", "NKE",
    "MRK", "MDT", "GE", "BA", "AMGN", "AMT", "ZTS", "MU", "TXN", "FIS",
    "WBA", "UPS", "SPGI", "NEE", "EXC", "COST", "PM", "GE", "F", "C",
    "LMT", "REGN", "SYK", "PLD", "CHTR", "MS", "QCOM", "AXP", "TMO", "SBUX",
    "DUK", "INTU", "MCHP", "ATVI", "ISRG", "NOW", "GM", "BMY", "USB", "INTU",
    "DHR", "AON", "BDX", "ADP", "VRSK", "KLAC", "ISRG", "APD", "MO", "NUE",
    "CME", "FISV", "GILD", "SHW", "ICE", "LRCX", "TRV", "CHD", "BIIB", "CB",
    "AMT", "MSCI", "BKNG", "GM", "ZBH", "WELL", "MELI", "HUM", "EFX", "FDC",
    "EQIX", "AIG", "VLO", "COP", "EOG", "MCO", "SPGI", "RSG", "RMD", "FRT",
    "TGT", "CSX", "TDG", "CHKP", "BDX", "ADSK", "NXPI", "PAYX", "MDLZ", "ORLY"
]


def generate_random_date(start_year: int, end_year: int) -> str:
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return random_date.strftime("%Y-%m-%d")

def get_sentiment(news_data: dict) -> float:
    if len(news_data['news']) > 0:
        total = 0
        count = 0
        for article in news_data['news']:
            header_blob = TextBlob(article['headline']).sentiment.polarity
            summary_blob = TextBlob(article['summary']).sentiment.polarity
            total += header_blob * 0.2 + summary_blob * 0.8
            count += 1
        return count
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


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/game')
def game():
    alpaca_client = AlpacaAPIClient(
        api_key=Alpaca.APCA_API_KEY_ID,
        secret_key=Alpaca.APCA_API_SECRET_KEY
    )
    random_date = generate_random_date(start_year=2020, end_year=2024)
    symbol = random.choice(sp500_top_100)
    stock_data = alpaca_client.get_stock_data(symbol, random_date)
    open_price = stock_data['bars'][0]['c']
    closing_price = stock_data['bars'][-1]['c']
    percent_change = ((closing_price) / open_price) * 100
    news_data = alpaca_client.get_news_data(symbol, random_date)
    sentiment = get_sentiment(news_data)
    return render_template('game.html')


@app.route('/results')
def results():
    correct = request.args.get('correct', 'false')
    return render_template('results.html', correct==correct)


if __name__ == '__main__':
    app.run(debug=True)
