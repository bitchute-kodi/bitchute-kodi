#!/usr/bin/env python3
import re
import json
import time
import requests
from bs4 import BeautifulSoup
import subprocess

baseUrl = "https://www.bitchute.com"

class VideoLink:
	def __init__(self):
		self.title = None
		self.pageUrl = None
		self.id = None
		self.channelName = None
		self.thumbnail = None
		self.url = None

	def getUrl(self):
		req = fetchLoggedIn(baseUrl + "/video/" + self.id)
		soup = BeautifulSoup(req.text, 'html.parser')
		for link in soup.findAll("a", href=re.compile("^magnet")):
			magnetUrl = link.get("href")
			if magnetUrl.startswith("magnet:?"):
				return magnetUrl
		raise ValueError("Could not find the magnet link for this video.")
	def setUrl(self):
		self.url = self.getUrl()
	@staticmethod
	def getVideoFromChannelVideosContainer(containerSoup):
		video = VideoLink()

		#find the video title and URL
		titleDiv = containerSoup.findAll('div', "channel-videos-title")[0]
		linkSoup = titleDiv.findAll('a')[0]

		video.title = linkSoup.string
		video.pageUrl = linkSoup.get("href")
		video.pageUrl = video.pageUrl.rstrip('/')
		video.id = video.pageUrl.split("/")[-1]

		#before we can find thumnails let's strip out play button images.
		for playButton in containerSoup.findAll('img', "play-overlay-icon"):
			playButton.extract()
		
		thumbnailMatches = containerSoup.findAll('img', "img-responsive")
		if thumbnailMatches:
			video.thumbnail = thumbnailMatches[0].get("data-src")
		return video
	@staticmethod
	def getVideoFromVideoCard(videoSoup):
		video = VideoLink()
		linkSoup = videoSoup.findAll('a')[0]

		video.pageUrl = linkSoup.get("href")
		video.pageUrl = video.pageUrl.rstrip('/')
		video.id = video.pageUrl.split("/")[-1]

		titleSoup = videoSoup.findAll('div', 'video-card-text')[0].findAll('p')[0].findAll('a')[0]
		video.title = titleSoup.text

		thumbnailMatches = videoSoup.findAll('img', "img-responsive")
		if thumbnailMatches:
			video.thumbnail = thumbnailMatches[0].get("data-src")
		
		#try to find the name of the channel from video-card-text portion of the card.
		try:
			channelNameSoup = videoSoup.findAll('div', 'video-card-text')[0].findAll('p')[1].findAll('a')[0]
			video.channelName = channelNameSoup.get("href").split("/")[-1]
		except:
			pass
		return video
	@staticmethod
	def getVideoFromPlaylist(container):
		video = VideoLink()
		titleSoup = container.findAll('div', 'text-container')[0].findAll('div', 'title')[0].findAll('a')[0]
		video.title = titleSoup.text
		video.pageUrl = titleSoup.get("href").rstrip('/')
		video.id = video.pageUrl.split("/")[-1]
		try:
			channelNameSoup = container.findAll('div', 'text-container')[0].findAll('div', 'channel')[0].findAll('a')[0]
			video.channelName = channelNameSoup.get("href").rstrip('/').split("/")[-1]
		except:
			pass

		for thumb in container.findAll("img", {"class": "img-responsive"}):
			if(thumb.has_attr("data-src")):
				video.thumbnail = thumb.get("data-src")
			break
		return video

class Channel:
	def __init__(self, channelName, thumbnail=None):
		self.channelName = channelName
		self.videos = []
		self.thumbnail = thumbnail
		self.page = 1
		self.hasPrevPage = False
		self.hasNextPage = False

		#self.setPage(self.page)

	def setThumbnail(self):
		thumbnailReq = fetchLoggedIn(baseUrl + "/channel/" + self.channelName)
		thumbnailSoup = BeautifulSoup(thumbnailReq.text, 'html.parser')
		thumbnailImages = thumbnailSoup.findAll("img", id="fileupload-medium-icon-2")
		if thumbnailImages and thumbnailImages[0].has_attr("data-src"):
			self.thumbnail = thumbnailImages[0].get("data-src")

	def setPage(self, pageNumber):
		self.videos = []
		self.thumbnail = None
		self.page = pageNumber
		self.hasPrevPage = False
		self.hasNextPage = False
		
		r = postLoggedIn(baseUrl + "/channel/" + self.channelName + "/extend/", baseUrl + "/channel/" + self.channelName + "/",{"index": (self.page)})
		data = json.loads(r.text)
		soup = BeautifulSoup(data['html'], 'html.parser')
		
		for videoContainer in soup.findAll('div', "channel-videos-container"):
			self.videos.append(VideoLink.getVideoFromChannelVideosContainer(videoContainer))
			self.videos[-1].channnelName = self.channelName
		x = len(self.videos)
		if len(self.videos) >= 10:
			self.hasNextPage = True

		# paginationLists = soup.findAll("ul", "pagination")
		# for paginationList in paginationLists:
		# 	for page in paginationList.findAll("li"):
		# 		# skip any page number list items that have the "disabled" class.
		# 		if page.has_attr("class"):
		# 			if "disabled" in page['class']:
		# 				continue 
		# 		# it's not disabled, keep on trucking.
		# 		if page.findAll("i", "fa-angle-double-left"):
		# 			self.hasPrevPage = True
		# 		if page.findAll("i", "fa-angle-double-right"):
		# 			self.hasNextPage = True
		
		# for now I only know how to find the channel's ID from a video, so take the last item
		# in videos and find the channel's ID.
		# videoRequest = requests.get(baseUrl + self.videos[-1].pageUrl)
		# channelIdMatches = re.search('/torrent/\d+', videoRequest.text)
		# if channelIdMatches:
		# 	self.id = channelIdMatches.group().split("/")[-1]
		# else:
		# 	raise ValueError("channel Id not found for " + self.channelName + ".")
		
		# armed with a channelId we can set the url for all our videos.
		#for video in self.videos:
		#	video.setUrl(self.id)


def login():
	#BitChute uses a token to prevent csrf attacks, get the token to make our request.
	r = requests.get(baseUrl)
	csrfJar = r.cookies
	soup = BeautifulSoup(r.text, 'html.parser')
	csrftoken = soup.findAll("input", {"name":"csrfmiddlewaretoken"})[0].get("value")

	username = None
	password = None

	#Fetch the user info from settings.json
	settingsFile = open("settings.json", "r")
	settings = json.loads(settingsFile.read())
	settingsFile.close()
	for key in settings.keys():
		if key == "username":
			username = settings[key]
		elif key == "password":
			password = settings[key]

	post_data = {'csrfmiddlewaretoken': csrftoken, 'username': username, 'password': password}
	headers = {'Referer': baseUrl + "/", 'Origin': baseUrl}
	response = requests.post(baseUrl + "/accounts/login/", data=post_data, headers=headers, cookies=csrfJar)
	authCookies = []
	for cookie in response.cookies:
		authCookies.append({ 'name': cookie.name, 'value': cookie.value, 'domain': cookie.domain, 'path': cookie.path, 'expires': cookie.expires })
	
	#stash our cookies in our JSON cookie jar
	cookiesJson = json.dumps(authCookies)
	cookiesFile = open("cookies.json", "w")
	cookiesFile.write(cookiesJson)
	cookiesFile.close()
	
	return(authCookies)
	
def setSessionCookies():
	cookiesFile = open("cookies.json", "r")
	cookiesString = cookiesFile.read()
	cookiesFile.close()
	if cookiesString:
		cookies = json.loads(cookiesString)
	else:
		cookies = login()
	
	#If our cookies have expired we'll need to get new ones.
	now = int(time.time())
	for cookie in cookies:
		if now >= cookie['expires']:
			cookies = login()
			break
	
	jar = requests.cookies.RequestsCookieJar()
	for cookie in cookies:
		jar.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'], expires=cookie['expires'])
	
	return jar

def fetchLoggedIn(url):
	req = requests.get(url, cookies=sessionCookies)
	soup = BeautifulSoup(req.text, 'html.parser')
	loginUser = soup.findAll("ul", {"class":"user-menu-dropdown"})
	if loginUser:
		profileLink = loginUser[0].findAll("a",{"class":"dropdown-item", "href":"/profile/"})
		if profileLink:
			return req
	#Our cookies have gone stale, clear them out.
	cookiesFile = open("cookies.json", "w")
	cookiesFile.write("")
	cookiesFile.close()
	raise ValueError("Not currently logged in.")

def postLoggedIn(url, referer, params):
	#BitChute uses a token to prevent csrf attacks, get the token to make our request.
	csrftoken = None
	for cookie in sessionCookies:
		if cookie.name == 'csrftoken':
			csrftoken = cookie.value
			break

	post_data = {'csrfmiddlewaretoken': csrftoken}
	for param in params:
		post_data[param] = params[param]

	headers = {'Referer': referer, 'Host': 'www.bitchute.com', 'Origin': baseUrl, 'Pragma': 'no-cache', 'Cache-Control': 'no-cache'}
	response = requests.post(url, data=post_data, headers=headers, cookies=sessionCookies)
	return response

def getSubscriptions():
	subscriptions = []
	req = fetchLoggedIn(baseUrl + "/subscriptions")
	soup = BeautifulSoup(req.text, 'html.parser')
	for container in soup.findAll("div", {"class":"subscription-container"}):
		thumbnail = None
		for thumb in container.findAll("img", {"class":"subscription-image"}):
			if thumb.has_attr("data-src"):
				thumbnail = thumb.get("data-src")
				thumbnail = thumbnail.replace("_small.", "_large.")
				break
		for link in container.findAll("a", {"rel":"author"}):
			href = link.get("href").rstrip('/')
			name = href.split("/")[-1]
			subscriptions.append(Channel(name, thumbnail))
		print(thumbnail)
	return(subscriptions)

def getWatchLater():
	videos = []
	req = fetchLoggedIn(baseUrl + "/playlist/watch-later/")
	soup = BeautifulSoup(req.text, 'html.parser')
	for container in soup.findAll("div", {"class": "playlist-video"}):
		videos.append(VideoLink.getVideoFromPlaylist(container))
	return videos
		

sessionCookies = setSessionCookies()

wl = getWatchLater()
raise ValueError("done testing")

subs = getSubscriptions()
chan = Channel("inrangetv")
chan.setThumbnail()
chan.setPage(1)
subscriptionActivity = postLoggedIn(baseUrl + "/extend/", baseUrl,{"name": "subscribed", "index": 0})
data = json.loads(subscriptionActivity.text)
soup = BeautifulSoup(data['html'], 'html.parser')
videos = []
for videoContainer in soup.findAll('div', "video-card"):
	videos.append(VideoLink.getVideoFromVideoCard(videoContainer))



vid = videos[-1]
vid.setUrl()

output = ""
cnt = 0
dlnaUrl = None
webTorrentClient = subprocess.Popen('/usr/local/bin/webtorrent-hybrid "' +  vid.url + '" --dlna', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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