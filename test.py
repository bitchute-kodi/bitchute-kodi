#!/usr/bin/env python3
import re
import requests
from bs4 import BeautifulSoup

baseUrl = "https://www.bitchute.com"

class VideoLink:
	def __init__(self, containerSoup):
		titleDiv = containerSoup.findAll('div', "channel-videos-title")[0]
		linkSoup = titleDiv.findAll('a')[0]
		
		self.title = linkSoup.string
		self.pageUrl = linkSoup.get("href")
		self.id = self.pageUrl.split("/")[-1]
		self.thumbnail = None
		#before we can find thumnails let's strip out play button images.
		for playButton in containerSoup.findAll('img', "play-overlay-icon"):
			playButton.extract()
		
		thumbnailMatches = containerSoup.findAll('img', "img-responsive")
		
		if thumbnailMatches:
			self.thumbnail = baseUrl + thumbnailMatches[0].get("src")

	def getUrl(self, channelId):
		return(baseUrl + "/torrent/" + channelId + "/" + self.id + ".torrent")

class Channel:
	def __init__(self, channelName):
		self.channelName = channelName
		self.videos = []

		r = requests.get(baseUrl + "/" + self.channelName)
		soup = BeautifulSoup(r.text, 'html.parser')

		for videoContainer in soup.findAll('div', "channel-videos-container"):
			self.videos.append(VideoLink(videoContainer))

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
	print(video.title + "\n" + video.thumbnail + "\n" + video.getUrl(x.id) + "\n")

