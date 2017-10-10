#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

r = requests.get('https://www.bitchute.com/InRangeTV/')
soup = BeautifulSoup(r.text, 'html.parser')
print(soup.prettify())
