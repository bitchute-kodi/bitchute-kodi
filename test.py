#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

r = requests.get('https://www.bitchute.com/InRangeTV/')
soup = BeautifulSoup(r.text, 'html.parser')

linksDivs = soup.findAll('div', "channel-videos-title")
for div in linksDivs:
	for link in div.findAll('a'):
		print(link.string)
		print(link.get("href"))
#print(linksDivs.prettify())
