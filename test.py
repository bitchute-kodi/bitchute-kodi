#!/usr/bin/env python3
import re
import json
import time
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
		self.page = 1
		self.hasPrevPage = False
		self.hasNextPage = False

		r = requests.get(baseUrl + "/" + self.channelName)
		soup = BeautifulSoup(r.text, 'html.parser')

		thumbnailImages = soup.findAll("img", id="fileupload-medium-icon-2")
		if thumbnailImages:
			self.thumbnail = baseUrl + thumbnailImages[0].get("src")

		for videoContainer in soup.findAll('div', "channel-videos-container"):
			self.videos.append(VideoLink(videoContainer))

		paginationLists = soup.findAll("ul", "pagination")
		for paginationList in paginationLists:
			for page in paginationList.findAll("li"):
				# skip any page number list items that have the "disabled" class.
				if page.has_attr("class"):
					if "disabled" in page['class']:
						continue 
				# it's not disabled, keep on trucking.
				if page.findAll("i", "fa-angle-double-left"):
					self.hasPrevPage = True
				if page.findAll("i", "fa-angle-double-right"):
					self.hasNextPage = True
		
		# for now I only know how to find the channel's ID from a video, so take the last item
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
	
def getSessionCookie():
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
	loginUser = soup.findAll("div", {"class":"login-user"})
	if loginUser:
		profileLink = loginUser[0].findAll("a",{"class":"dropdown-item", "href":"/profile"})
		if profileLink:
			return req
	#Our cookies have gone stale, clear them out.
	cookiesFile = open("cookies.json", "w")
	cookiesFile.write("")
	cookiesFile.close()
	raise ValueError("Not currently logged in.")

def getSubscriptions():
	subscriptions = []
	req = fetchLoggedIn(baseUrl + "/subscriptions")
	soup = BeautifulSoup(req.text, 'html.parser')
	for container in soup.findAll("div", {"class":"subscription-container"}):
		for link in container.findAll("a", {"rel":"author"}):
			name = link.get("href").split("/")[-1]
			subscriptions.append(Channel(name))
	return(subscriptions)

sessionCookies = getSessionCookie()
channels = getSubscriptions()

for channel in channels:
	print(channel.channelName + " (" + channel.id + ")")
	print(channel.thumbnail)
	print("Videos:")
	for video in channel.videos:
		print(video.title + "\n" + video.thumbnail + "\n" + video.url + "\n")
	if channel.hasPrevPage:
		print("Has Prev: true")
	else:
		print("Has Prev: false")
	if channel.hasNextPage:
		print("Has Next: true")
	else:
		print("Has Next: false")

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