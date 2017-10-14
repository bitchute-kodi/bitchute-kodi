#!/usr/bin/env python3
import re
import requests
from bs4 import BeautifulSoup

baseUrl = "https://www.bitchute.com"

class VideoLink:
	def __init__(self, linkSoup):
		self.title = linkSoup.string
		self.pageUrl = linkSoup.get("href")
		self.id = self.pageUrl.split("/")[-1]

	def getUrl(self, channelId):
		return(baseUrl + "/torrent/" + channelId + "/" + self.id + ".torrent")

class Channel:
	def __init__(self, channelName):
		self.channelName = channelName
		self.videos = []

		r = requests.get(baseUrl + "/" + self.channelName)
		soup = BeautifulSoup(r.text, 'html.parser')
		for div in soup.findAll('div', "channel-videos-title"):
			for link in div.findAll('a'):
				self.videos.append(VideoLink(link))

		# for now I only know how to find the ID from a video, so take the last item
		# in videos and find the channel's ID.
		videoRequest = requests.get(baseUrl + self.videos[-1].pageUrl)
		channelIdMatches = re.search('/torrent/\d+', videoRequest.text)
		if channelIdMatches:
			self.id = channelIdMatches.group().split("/")[-1]
		else:
			raise ValueError("channel Id not found for " + self.channelName + ".")

x = Channel("InRangeTV")
print(x.channelName + " (" + x.id + ")")
print("Videos:")
for video in x.videos:
	print(video.title + "\n" + video.getUrl(x.id))

