#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General
# Public License, version 2 or later.  Please see the included LICENSE.txt
# file for details.  Legally, that file should have been included with this
# one.  If not, please contact Lee Braiden (email leebraid@gmail.com)
# for a copy.
#
import os
import sys
import urlparse
import httplib
import urllib
import threading
import commands
import mimetypes
import kio

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import config
import KDebug

sys.path.append(os.path.join(appRoot, 'code/thirdparty'))
import feedparser

class NamedLock:
	def __init__(self, name):
		self.__realLock = threading.RLock()
		self._name = name
	
	def acquire(self, block=True):
		return self.__realLock.acquire(block)
	
	def release(self):
		return self.__realLock.release()

def wrapURI(uri):
	uri = enableWrapping(uri)
	if len(uri) > 100:
		uri = uri[:96] + '[...]'
	return uri

def enableWrapping(textStr):
	"""Modifies HTML text with special codes to allow wordwrapping, even
	if there are no spaces in the text."""
	# insert wordbreak tags (<wbr/>) to allow text to wrap nicely
	# do this for all likely break points, such as
	# path seperators (/.:), commas, and capital letters.
	
	newStr = unicode(textStr)
	
	try:
		for i in config.textToForceBreaksOn:
			newStr = newStr.replace(i, u'<wbr>' + i)
	except UnicodeDecodeError:
		pass
	
	return newStr

class TimeoutError(Exception):
	pass

def timelimit(timeout):
	"""Function/method decorator, which makes it timeout after a given
	number of seconds."""
	def internal(function):
		def internal2(*args, **kw):
			class Calculator(threading.Thread):
				def __init__(self):
					threading.Thread.__init__(self)
					self.result = None
					self.error = None
				
				def run(self):
					try:
						self.result = function(*args, **kw)
					except:
						self.error = sys.exc_info()[0]
			
			c = Calculator()
			c.start()
			c.join(timeout)
			if c.isAlive():
				raise TimeoutError
			if c.error:
				raise c.error
			return c.result
		return internal2
	return internal

def mimetypeForHTTPURL(url):
	"""Returns the mimetype of a given URL."""
	PROTO=0
	HOSTANDPORT=1
	PATH=2
	
	urlparts = urlparse.urlparse(url)
	
	if urlparts[PROTO] != 'http' and urlparts[PROTO] != 'https':
		# can't figure this out with httplib, but it probably
		# won't be a feed anyway; just return the default
		return 'application/octet-stream'
	
	if ':' in urlparts[HOSTANDPORT]:
		host = urlparts[HOSTANDPORT][:urlparts[HOSTANDPORT].index(':')]
		port = urlparts[HOSTANDPORT][urlparts[HOSTANDPORT].index(':'):]
	else:
		host = urlparts[HOSTANDPORT]
		port = 80
	
	conn = httplib.HTTPConnection(host, port)
	conn.request('HEAD', urlparts[PATH])
	resp = conn.getresponse()
	return resp.msg.gettype()

def isAFeed(url):
	"""Returns a tuple, containing True if a URL appears to be a feed, and the final
	recommended uri to use."""
	assert url.__class__ is unicode
	
	# handle feed: uris
	prefix = url[:len('feed:')]
	if prefix == 'feed:':
		altPrefix = url[:len('feed://')]
		if altPrefix == 'feed://':
			newURL = url[len('feed://'):]
		else:
			newURL = url[len('feed:'):]
		if not '://' in newURL:
			newURL = 'http://' + newURL
		return True, newURL

	# democracy player now returns special files, but we can
	# catch the actual feed path from the URL it uses to generate those
	#
	# this converts links of the form:
	#
	#       http://subscribe.getdemocracy.com/?url1=quoteduri
	#
	# to
	#
	#       unquoteduri
	#
	democracyFeedLinkPrefix = 'http://subscribe.getdemocracy.com/?url1='
	if url.startswith(democracyFeedLinkPrefix):
		newURL = urllib.unquote(url[len(democracyFeedLinkPrefix):])
		print "replaced %s with %s" % (url, newURL)
		return True, newURL

	# handle rss: uris
	prefix = url[:len('rss:')]
	if prefix == 'rss:':
		altPrefix = url[:len('rss://')]
		if altPrefix == 'rss://':
			newURL = url[len('rss://'):]
		else:
			newURL = url[len('rss:'):]
		if not '://' in newURL:
			newURL = 'http://' + newURL
		return True, newURL
	
	# quick checks for other stuff that looks like a feed; we can
	# afford to be a little optimistic here, since the browser IS
	# a feed browser, and it's likely to be used for picking feeds
	# still need to do this properly by detecting mimetypes and
	# such though.
	for i in config.feedGiveaways:
		try:
			if i in url:
				return True, url
		except TypeError:
			print "Warning: TypeError in isAFeed.  URL is", url
			return False, None
	
	# no dice; do it the hard way
	feed = feedparser.parse(url)
	if len(feed.entries) > 0:
		return True, url
	
	# if we get to here, and didn't recognise it, it's probably not a feed
	return False, None

def getMimetype(filepath):
	#NOTE: we use the unix command "file" here, instead of the python mimetypes module, since it understands
	# file contents (file magic) and not just the file's name
	fileOutput = commands.getoutput(u"file -i '%s'" % filepath)
	if not u':' in fileOutput or not u':' in fileOutput:
		# must be bad
		raise OSError, u"Can't figure out the mimetype for %s; the file command failed." % filepath
	else:
		mimetype = fileOutput[fileOutput.index(u':')+2:]
		if u';' in mimetype:
			# remove the encoding
			mimetype = mimetype[:mimetype.index(u';')]
		return mimetype

def properExtensionForMimetype(mimetype, currentExten):
	"""Finds the correct extension for a mimetype, trying to preserve the current extension, if it's valid."""
	# NOTE: we currently specify strict here, thereby forcing a rename of even slightly dodgy extensions
	# this could be changed, but could make players fail for some types they would otherwise handle.
	validExtens = mimetypes.guess_all_extensions(mimetype, strict=True)
	if currentExten in validExtens:
		return currentExten
	else:
		return mimetypes.guess_extension(mimetype)

def prettyPrintBytes(bytes):
	try:
		bytes = int(bytes)
	except ValueError:
		bytes = 0
	if bytes / 1024:
		# at least 1K
		if bytes / (1024 * 1024):
			# at least 1M
				if bytes / (1024 * 1024 * 1024):
					# at least 1G
					return u"%.2f GB" % (bytes / float(1024 * 1024 * 1024))
				else:
					return u"%.2f MB" % (bytes / float(1024 * 1024))
		else:
			return u"%.2f KB" % (bytes / float(1024))
	else:
		return u"%d Bytes" % (bytes)

def prettyPrintBitsPerSec(bps):
	try:
		bps = float(bps)
	except TypeError:
		bps = 0.0
	
	# convert to bytes per second
	bps /= 8.0
	
	if (bps / 1024.0) >= 1.0:
		# at least 1Kbps
		if (bps / float(1024 * 1024)) >= 1.0:
			# at least 1Mbps
				if (bps / float(1024 * 1024 * 1024)) >= 1.0:
					# at least 1Gbps
					return u"%.2f GBytes/sec" % (bps / float(1024 * 1024 * 1024))
				else:
					return u"%.2f MBytes/sec" % (bps / float(1024 * 1024))
		else:
			return u"%.2f KBytes/sec" % (bps / float(1024))
	else:
		return u"%d Bytes/sec (very slow!)" % bps

def prettyPrintSeconds(secs):
	try:
		secs = float(secs)
	except:
		return "(not available)"
	
	if (secs / 60) >= 1:
		# at least a minute
		if (secs / (60 * 60)) >= 1:
			# at least an hour
			if (secs / (60 * 60 * 24)) >= 1:
				# at least a day
				if (secs / (60 * 60 * 24 * 7)) >= 1:
					# at least a week
					return "%d weeks" % int(secs / float(60 * 60 * 24 * 7))
				else:
					return "%d days" % int(secs / float(60 * 60 * 24))
			else:
				return "%d hours" % int(secs / float(60 * 60))
		else:
			return "%d minutes" % int(secs / float(60))
	else:
		return "%d seconds" % secs

def uriToArgs(uri):
	try:
		kwArgs = uri.split('&')
	except ValueError:
		kwArgs = uri
	
	res = {}
	for arg in kwArgs:
		try:
			k, v = arg.split('=', 1)
			k = uniUnquote(k)
			v = uniUnquote(v)
		except ValueError:
			k = arg
			v = None
		res[k] = v
	
	return res

def uniQuote(u):
	u = unicode(u)
	u8 = u.encode('utf-8')
	uQ = urllib.quote(u8)
	return uQ

def uniUnquote(rQ):
	rU = urllib.unquote(rQ)
	r8 = rU.decode('utf-8')
	r = unicode(r8)
	return r

def argsToURI(kwArgs):
	encodedStr = ""
	
	for k in kwArgs.keys():
		if encodedStr != "":
			encodedStr += "&"
		
		k = unicode(k)
		encodedStr += uniQuote(k)
		encodedStr += '='
		
		v = uniQuote(kwArgs[k])
		encodedStr += v
	
	return encodedStr

def pruneSubPaths(rootPath):
	"""Remove any empty directories under a given root directory path"""
	for root, dirs, files in os.walk(rootPath, topdown=False):
		for dirname in dirs:
			fullPath = os.path.join(root, dirname)
			
			subFiles = os.listdir(fullPath)
			if len(subFiles) == 0:
				os.rmdir(fullPath)
	
	# if we deleted the rootPath (only happens if it's empty), then
	# we re-create it.  Doing it this way may help to free diskspace
	# that isn't always freed by unlinking the files themselves.
	try:
		os.makedirs(rootPath)
	except:
		pass

def ensureDirExistsForFile(filePath):
	"""Makes sure that the subdirectory exists for a given filename"""
	fullDirPath = os.path.dirname(filePath)
	try:
		os.makedirs(fullDirPath)
	except OSError:
		pass

def destPathFromURI(uri):
	"""Return the local path where a uri should be stored"""
	urlParts = urlparse.urlparse(uri)
	# take the leading / off the path part, and return it
	pathPart = urlParts[2][1:]
	fullPath = os.path.join(config.mediaStoreRoot, urllib.url2pathname(urlParts[1]), pathPart)
	
	# check if the pathname is already in use, and if it is,
	# append a number that increments until we find a
	# filename that's available.
	pathNameOK = not os.path.exists(fullPath)
	count = 1
	while not pathNameOK:
		# another download has this filename already
		try:
			basename = pathPart[:pathPart.rindex(u'.')]
			exten = pathPart[pathPart.rindex(u'.'):]
		except ValueError:
			basename = pathPart
			exten = ""
		
		fullPath = os.path.join(config.mediaStoreRoot, urllib.url2pathname(urlParts[1]), basename + u'_' + unicode(count) + exten)
		pathNameOK = not os.path.exists(fullPath)
		count += 1
	return fullPath

def renameForMimetype(localPath, mimetype):
	assert localPath is not None
	assert mimetype is not None

	try:
		currentExten = localPath[localPath.rindex('.'):]
	except ValueError:
		currentExten = ""
	
	bestExten = properExtensionForMimetype(mimetype, currentExten)

	if bestExten and (currentExten != bestExten):
		newPath = localPath + bestExten
		try:
			os.rename(localPath, newPath)
			return newPath
		except OSError, e:
			print "Warning: tried to rename '%s' to '%s', but couldn't.  Error is" % (localPath, newPath), e
			return localPath
	else:
		return localPath

def btFormatETA(n):
	# this func copyright Bram Cohen;
	# taken from PenguinTV, presumably
	# originally from bittorrent.
	# previously called 'hours'
	if n == -1:
		return '<unknown>'
	if n == 0:
		return 'complete!'
	n = long(n)
	h, r = divmod(n, 60 * 60)
	m, sec = divmod(r, 60)
	if h > 1000000:
		return '<unknown>'
	if h > 0:
		return '%d:%02d:%02d' % (h, m, sec)
	else:
		return '%d:%02d' % (m, sec)

def isMediaFile(localFilePath):
	mimetype = getMimetype(localFilePath)
	if mimetype.startswith('video') or mimetype.startswith('audio'):
		return True

def allMediaInDir(rootDirPath):
	mediaFiles = []
	
	for root, dirs, files in os.walk(rootDirPath, topdown=False):
		for filename in files:
			fullPath = os.path.join(root, filename)
			if isMediaFile(fullPath):
				mediaFiles.append(fullPath)

	assert isinstance(mediaFiles, list)
	return mediaFiles

def mostLikelyMedia(mediaFiles):
	biggestFile = None
	biggestFileSize = 0

	assert isinstance(mediaFiles, list)
	
	for mFile in mediaFiles:
		mFileSize = os.path.getsize(mFile)
		if mFileSize > biggestFileSize:
			biggestFile = mFile
			biggestFileSize = mFileSize
	
	return biggestFile

def mimetypeToPrettyType(mimetype):
	"""Returns a more human-readable description of a mimetype."""
	kdeMimetype = kio.KMimeType.mimeType(mimetype)
	prettyType = kdeMimetype.comment()
	
	# if KDE doesn't know it, then just return the main type ('video' instead of 'video/mpeg', etc.)
	# FIXME: this won't work if/when KDE returns a localised translation of the comment
	if prettyType == u"Unknown":
		if u'/' in mimetype:
			prettyType = mimetype[:mimetype.index(u'/')]

	return prettyType

def synchronized(lock):
	""" Synchronization decorator. """
	def wrap(f):
		def newFunction(*args, **kw):
			lock.acquire()
			try:
				return f(*args, **kw)
			finally:
				lock.release()
		return newFunction
	return wrap

def isValidPageLink(uri):
	"""Determine if a feed's link back to the episode page is valid.
	Mostly necessary because some feeds also link to their content that
	way, rather than linking to a web page.  In other words, it prevents
	listing enclosures as a webpage link, when we already have them listed
	perfectly well as enclosures."""
	if "http://www.bt-chat.com/download.php?info_hash=" in uri:
		# this is a direct link to a torrent (possibly from
		# tvsrrs.net).  Skip it.
		return False
	
	# otherwise, assume it's OK
	return True

def isExternalURL(url):
	"""Check for URLs that should NOT be handled internally, by
	KatchTV.  Most importantly, this includes KatchTV updates."""
	if "www.digitalunleashed.com/download" in url:
		return True
	
	return False

