#!/usr/bin/env python3
import re
import requests
from bs4 import BeautifulSoup

baseUrl = "https://www.bitchute.com"
channelName = "InRangeTV"

r = requests.get(baseUrl + "/" + channelName)
soup = BeautifulSoup(r.text, 'html.parser')

links = []
linksDivs = soup.findAll('div', "channel-videos-title")
for div in linksDivs:
	for link in div.findAll('a'):
		print(link.string)
		print(link.get("href"))
		links.append(link.get("href"))

videoId = links[-1].split("/")[-1]
print("Video ID: " + videoId)

videoRequest = requests.get(baseUrl + links[-1])

channelIdMatches = re.search('/torrent/\d+', videoRequest.text)
if channelIdMatches:
	channelId = channelIdMatches.group().split("/")[-1]
	print("Channel Id: " + channelId)
else:
	print("channelId not found.")

torrentUrl = baseUrl + "/torrent/" + channelId + "/" + videoId + ".torrent"
print(torrentUrl)
