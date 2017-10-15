#!/usr/bin/env python3
import re
import requests
from bs4 import BeautifulSoup
import subprocess

baseUrl = "https://www.bitchute.com"
class VideoLink:
	def __init__(self, containerSoup):
		titleDiv = containerSoup.findAll('div', "channel-videos-title")[0]
		linkSoup = titleDiv.findAll('a')[0]
		
		self.title = linkSoup.string
		self.pageUrl = linkSoup.get("href")
		self.id = self.pageUrl.split("/")[-1]
		self.thumbnail = None
		self.url = None
		#before we can find thumnails let's strip out play button images.
		for playButton in containerSoup.findAll('img', "play-overlay-icon"):
			playButton.extract()
		
		thumbnailMatches = containerSoup.findAll('img', "img-responsive")
		
		if thumbnailMatches:
			self.thumbnail = baseUrl + thumbnailMatches[0].get("src")

	def getUrl(self, channelId):
		return(baseUrl + "/torrent/" + channelId + "/" + self.id + ".torrent")
	def setUrl(self, channelId):
		self.url = self.getUrl(channelId)

class Channel:
	def __init__(self, channelName):
		self.channelName = channelName
		self.videos = []
		self.thumbnail = None

		r = requests.get(baseUrl + "/" + self.channelName)
		soup = BeautifulSoup(r.text, 'html.parser')

		thumbnailImages = soup.findAll("img", id="fileupload-medium-icon-2")
		if thumbnailImages:
			self.thumbnail = baseUrl + thumbnailImages[0].get("src")

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
		
		# armed with a channelId we can set the url for all our videos.
		for video in self.videos:
			video.setUrl(self.id)

subscriptions = ["InRangeTV", "mediamonarchy"]
channels = []
for channel in subscriptions:
	channels.append(Channel(channel))

for channel in channels:
	print(channel.channelName + " (" + channel.id + ")")
	print(channel.thumbnail)
	print("Videos:")
	for video in channel.videos:
		print(video.title + "\n" + video.thumbnail + "\n" + video.url + "\n")

vid = channels[-1].videos[-1]

output = ""
cnt = 0
dlnaUrl = None
webTorrentClient = subprocess.Popen(["/usr/local/bin/webtorrent-hybrid", vid.url, "--dlna"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print("running with PID " + str(webTorrentClient.pid))
for stdout_line in webTorrentClient.stdout:
	output += stdout_line.decode()
	cnt += 1
	if cnt > 10:
		break
webTorrentClient.stdout.close()
print("done with capturing output.")

dlnaMatches = re.search('http:\/\/((\w|\d)+(\.)*)+:\d+\/\d+', output)
if dlnaMatches:
	dlnaUrl = dlnaMatches.group()
else:
	webTorrentClient.terminate()
	raise ValueError("could not determine the dlna URL.")

print("Streaming at: " + dlnaUrl)
webTorrentClient.terminate()
# poll = webTorrentClient.poll()
# while poll == None:
# 	print(webTorrentClient.communicate()[0])
	# poll = webTorrentClient.poll()


# x = Channel("InRangeTV")
# print(x.channelName + " (" + x.id + ")")
# print("Videos:")
# for video in x.videos:
# 	print(video.title + "\n" + video.thumbnail + "\n" + video.getUrl(x.id) + "\n")

