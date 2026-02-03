import requests
from bs4 import BeautifulSoup

def get_stock_price(ticker, exchange):
    url = f"https://www.google.com/finance/quote/{ticker}:{exchange}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    class_name = "YMlKec fxKbKc"
    price_tag = soup.find(class_=class_name)

    if price_tag is None:
        return {
            "error": "Invalid ticker or exchange"
        }

    price = float(price_tag.text.strip()[1:].replace(",", ""))

    return {
        "ticker": ticker,
        "exchange": exchange,
        "price": price
    }
