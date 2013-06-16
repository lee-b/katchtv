#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email leebraid@gmail.com) for a copy.
#

# TODO: drop raw feed after parsing it, so we don't use too much memory
# TODO: offload unneeded episodes/enclosures to disk, to save memory

import sys
import os
import datetime
import traceback
import threading
import md5

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import config
import utils
import Media
import KDebug
import DataStore

sys.path.append(os.path.join(appRoot, 'code/thirdparty'))
import feedparser


class FeedEnclosure:
	def __init__(self, downloadURI, title, desc, mimetype, prettyType, feedURI, sizeInBytes=None):
		assert isinstance(prettyType, unicode)
		
		self.__downloadURI = downloadURI
		self.__title = title
		self.__desc = desc
		self.__mimetype = mimetype
		self.__prettyType = prettyType
		self.__sizeInBytes = sizeInBytes
		self.__feedURI = feedURI
		
		self.__mediaItem = None						# when not downloading or downloaded, no media item is present
	
	def getKWArgsForConstruct(self):
		args = {
			'downloadURI':			self.__downloadURI,
			'title':						self.__title,
			'desc':						self.__desc,
			'mimetype':					self.__mimetype,
			'prettyType':				self.__prettyType,
			'sizeInBytes':			self.__sizeInBytes,
			'feedURI':					self.__feedURI,
#			'mediaItem':				self.__mediaItem,				# saved separately; can be re-attached later
		}
		return args

	@classmethod
	def constructFromKWArgs(cls, kwArgs):
		assert isinstance(kwArgs['prettyType'], unicode)
		
		enc = FeedEnclosure(kwArgs['downloadURI'], kwArgs['title'], kwArgs['desc'], kwArgs['mimetype'], kwArgs['prettyType'], kwArgs['feedURI'], kwArgs['sizeInBytes'])
		return enc
	
	def title(self):
		return self.__title
	
	def _downloadURI(self):
		return self.__downloadURI
	
	def mediaItem(self):
		return self.__mediaItem
	
	def hasMediaItem(self):
		return self.__mediaItem is not None
	
	def mimetype(self):
		return self.__mimetype
	
	def prettyType(self):
		return self.__prettyType
	
	def description(self):
		return self.__desc
	
	def sizeInBytes(self):
		return self.__sizeInBytes
	
	def getMediaItemKWArgs(self):
		"""Returns keyword arguments suitable for passing to a Media.Item constructor"""
		ctorArgs = {
			Media.Item.URI:							self.__downloadURI,
			Media.Item.TITLE:						self.__title,
			Media.Item.DESCRIPTION:			self.__desc,
			Media.Item.MIMETYPE:					self.__mimetype,
			Media.Item.PRETTY_TYPE:				self.__prettyType,
			Media.Item.SOURCE_FEED_URI:	self.__feedURI,
		}
		
		if self.__sizeInBytes:
			ctorArgs[Media.Item.TOTAL_BYTES] = self.__sizeInBytes
		
		return ctorArgs
	
	def _attachMediaItem(self, mediaItem):
		self.__mediaItem = mediaItem

	def _detachMediaItem(self):
		self.__mediaItem = None

class FeedEpisode:
	def __init__(self, id, title, date, htmlBody, enclosures, link):
		assert isinstance(enclosures, list)
		
		self.__id = id
		self.__title = title
		self.__date = date
		self.__body = htmlBody
		self.__enclosures = enclosures
		self.__link = link
		self.__isNew = True
	
	def getID(self):
		return self.__id
	
	def getKWArgsForConstruct(self):
		enclosures = []
		for enc in self.__enclosures:
			encKWArgs = enc.getKWArgsForConstruct()
			enclosures.append(encKWArgs)
		
		args = {
			'id':				self.__id,
			'title':			self.__title,
			'date':			self.__date,
			'body':			self.__body,
			'enclosures':	enclosures,
			'link':			self.__link,
			'isNew':			self.__isNew,
		}
		
		return args
	
	@classmethod 
	def constructFromKWArgs(cls, kwArgs):
		ep = FeedEpisode(kwArgs['id'], kwArgs['title'], kwArgs['date'], kwArgs['body'], [], kwArgs['link'])
		ep.__isNew = kwArgs['isNew']
		
		for encKWs in kwArgs['enclosures']:
			assert isinstance(encKWs, dict)
			enc = FeedEnclosure.constructFromKWArgs(encKWs)
			ep.__enclosures.append(enc)
		
		return ep
	
	def enclosures(self):
		return self.__enclosures
	
	def title(self):
		return self.__title
	
	def body(self):
		return self.__body
	
	def date(self):
		return self.__date
	
	def link(self):
		return self.__link
	
	def hasLink(self):
		return self.__link is not None
	
	def setNew(self, isNew):
		self.__isNew = isNew
		
	def isNew(self):
		return self.__isNew

class Feed:
	__rawFeedCache = {}
	
	def __init__(self, feedURI, feedTitle=None, updateMins=config.defaultChannelUpdateMins):
		assert isinstance(feedURI, unicode)
		
		self.__feedURI = feedURI
		self.__title = feedTitle
		self.__updateMins = updateMins
		
		self.__summary = config.defaultFeedSummary
		self.__logoURI = config.defaultFeedLogoURI
		
		self.__cachedRawFeed = None
		self.__lastFeedDownload = None
		self.__episodes = []
		
		self.__lock = utils.NamedLock("Lock for Feed '%s'" % feedURI)

	def acquireLock(self):
		self.__lock.acquire()
	
	def releaseLock(self):
		self.__lock.release()
	
	def addEpisode(self, epi):
		self.__episodes.append(epi)
	
	def getKWArgsForConstruct(self):
		constructEpisodes = []
		for ep in self.__episodes:
			constructEpisodes.append(ep.getKWArgsForConstruct())
		
		args = {
			u'uri':						self.__feedURI,
			u'episodes':				constructEpisodes,
			u'title':						self.__title,
			u'summary':					self.__summary,
			u'logoURI':					self.__logoURI,
			u'updateMins':			self.__updateMins,
			u'lastFeedDownload':	self.__lastFeedDownload,
		}
		return args
	
	@classmethod
	def constructFromKWArgs(cls, kwArgs):
		feed = Feed(kwArgs['uri'], feedTitle=kwArgs['title'], updateMins=kwArgs['updateMins'])
		feed.__logoURI = kwArgs['logoURI']
		feed.__summary = kwArgs['summary']
		feed.__lastFeedDownload = kwArgs['lastFeedDownload']
		
		for epKWs in kwArgs['episodes']:
			epi = FeedEpisode.constructFromKWArgs(epKWs)
			feed.addEpisode(epi)
		
		return feed
	
	def markAllEpisodesAsSeen(self):
		for epi in self.__episodes:
			epi.setNew(False)
	
	def __getEnclosureTypes(self, enclosure):
		encType = enclosure.get(u'type', u'')
		return encType, utils.mimetypeToPrettyType(encType)
	
	def __generateEnclosuresForRawFeedEpisode(self, episode):
		"""Builds a list of Media.Items (enclosures) from a given raw feed entry ("episode")"""
		enclosures = []
		
		if episode.has_key(u'enclosures') and len(episode[u'enclosures']) > 0:
			if episode.has_key(u'title'):
				episodeTitle = self.__reliableUnidecode(episode[u'title'])
			else:
				episodeTitle = u""
				
			if episode.has_key(u'description'):
				episodeDesc = self.__reliableUnidecode(episode[u'description'])
			else:
				episodeDesc = u""
			
			for enclosure in episode[u'enclosures']:
				# get a title for the enclosure, if possible, or fudge it
				enclosureTitle = enclosure.get(u'title', episodeTitle)
				encType, prettyEncType = self.__getEnclosureTypes(enclosure)
				
				# convert from QString to unicode
				encType = unicode(encType)
				prettyEncType = unicode(prettyEncType)
				
				# FIXME: get enclosure description here, if available.
				enclosureDesc = episodeDesc
				
				length = None
				if enclosure.has_key(u'length'):
					try:
						length = int(enclosure[u'length'])
					except ValueError:
						pass
				
				enclosureObj = FeedEnclosure(enclosure[u'href'], enclosureTitle, enclosureDesc, encType, prettyEncType, self.__feedURI, length)
				
				enclosures.append(enclosureObj)
		
		return enclosures
	
	@classmethod
	def getAndParseFeedURI(cls, uriStr, forceUpdate=False):
		@utils.timelimit(config.maxFeedParseSeconds)
		def getRawFeed(uriStr):
			return feedparser.parse(uriStr)
		
		if not forceUpdate and cls.__rawFeedCache.has_key(uriStr):
			return cls.__rawFeedCache[uriStr]
		
		assert isinstance(uriStr, unicode)
		
		try:
			rawFeed = getRawFeed(uriStr)
			cls.__rawFeedCache[uriStr] = rawFeed
			return rawFeed
		except utils.TimeoutError:
			print u"Warning feed from %s took more than %s seconds to parse; aborted!" % (uriStr, config.maxFeedParseSeconds)
			return None

	def __reliableUnidecode(self, text):
		try:
			newText = unicode(text)
		except UnicodeDecodeError:
			newText = u"(unicode decode error)"
		return newText

	def __postprocessRawFeed(self, rawFeed):
		"""Extracts all useful info from a raw feed, creating high-level objects."""
		assert not isinstance(rawFeed, Feed)
		
		if not self.__title:
			if rawFeed.feed.has_key(u'title'):
				self.__title = self.__reliableUnidecode(rawFeed.feed[u'title'])
			else:
				self.__title = config.defaultChannelTitle
		
		try:
			if rawFeed.feed.has_key('subtitle'):
				self.__summary = self.__reliableUnidecode(rawFeed.feed[u'subtitle'])
		except KeyError:
			self.__summary = config.defaultFeedSummary
		
		if rawFeed.feed.has_key('image'):
			self.__logoURI = rawFeed.feed.image.href
		else:
			self.__logoURI = config.defaultFeedLogoURI
		
		for episode in rawFeed.entries:
				self.acquireLock()
				try:
					epi = self._buildEpisodeIfNew(episode, rawFeed)
					if epi:
						self.addEpisode(epi)
				finally:
					self.releaseLock()

	def _buildEpisodeIfNew(self, rawEpisode, rawFeed):
		try:
			episodeTitle = self.__reliableUnidecode(rawEpisode['title'])
		except KeyError:
			episodeTitle = self.__title
		
		try:
			episodeDesc = self.__reliableUnidecode(rawEpisode['description'])
		except (KeyError, TypeError):
			episodeDesc = config.defaultEpisodeBody
		
		# get date from episode.  Try to use static creation
		# dates only, rather than last update/comment date,
		# and use current date if that fails
		if rawEpisode.has_key(u'created_parsed'):
			episodeDate = rawEpisode[u'created_parsed']
		elif rawEpisode.has_key(u'published_parsed'):
			episodeDate = rawEpisode[u'published_parsed']
		else:
			# no date in episode's feed, so just pretend it's as old as time itself
			# -- unix time, that is ;)
			episodeDate = datetime.datetime(year=1970, month=1, day=1)
		
		try:
			webPageLink = rawEpisode.links[0][u'href']
		except AttributeError:
			webPageLink = None
		
		if rawEpisode.has_key(u'id'):
			id = rawEpisode[u'id']
		else:
			md5h = md5.new()
			md5h.update(episodeTitle)
			md5h.update(str(episodeDate))
			md5h.update(episodeDesc)
			id = md5h.digest()
		
		if self.hasEpisode(id):
			oopEpisode = None
		else:
			enclosures = self.__generateEnclosuresForRawFeedEpisode(rawEpisode)
			oopEpisode = FeedEpisode(id, episodeTitle, episodeDate, episodeDesc, enclosures, webPageLink)
		
		return oopEpisode
	
	def hasEpisode(self, id):
		"""Figure out if this feed already has the given episode."""
		#FIXME: should probably use more reliable (unique) data
		# for this since titles, dates etc. could be identical.
		
		for episode in self.__episodes:
			if episode.getID() == id:
				return True
		
		return False

	def updateIsDue(self):
		acceptableDate = datetime.datetime.now() - datetime.timedelta(minutes=self.__updateMins)
		
		if not self.__lastFeedDownload or self.__lastFeedDownload < acceptableDate:
			return True
		else:
			return False
	
	def doUpdate(self, forceUpdate=False):
		"""Updates the feed if necessary (or demanded), according to internal
		information about refresh times.  Intended to be called at startup,
		and at regular intervals through timer events."""
		
		if self.updateIsDue():
			rawFeed = Feed.getAndParseFeedURI(self.__feedURI, forceUpdate)
			if rawFeed is not None:
				self.__lastFeedDownload = datetime.datetime.utcnow()
				self.__postprocessRawFeed(rawFeed)
	
	def updateMins(self):
		return self.__updateMins
	
	def setUpdateMins(self, newMins):
		self.__updateMins = newMins
	
	def lastCheck(self):
		return self.__lastFeedDownload
	
	def title(self):
		return self.__title

	def setTitle(self, newTitle):
		self.__title = newTitle
	
	def uri(self):
		return self.__feedURI
	
	def summary(self):
		return self.__summary
	
	def episodes(self):
		return self.__episodes
	
	def logoURI(self):
		return self.__logoURI
	
	def numNewEpisodes(self):
		newCount = 0
		
		for episode in self.__episodes:
			if episode.isNew():
				newCount += 1
		
		return newCount
	
	def _dump(self, level=0):
		epiCount = 0
		encCount = 0
		
		for epi in self.episodes():
			epiCount += 1
			for enc in epi.enclosures():
				encCount += 1
		
		print "{Feed: %s" % self.__title
		print (" " * (level + 2)) + "%d episodes," % epiCount
		print (" " * (level + 2)) + "%d enclosures" % encCount
		print (" " * level) + "}"

class FeedCache:
	_feeds = None
	_feedCacheShelf = DataStore.DataStore(os.path.join(config.configRoot, 'feedcache.shelf'))
	_lock = utils.NamedLock("FeedCache lock")
	
	@classmethod
	def _dump(cls):
		print """
FeedCache dump
===========
"""
		for fK in cls.__feeds.keys():
			print "Feed:", cls.__feeds[fK].title(), "(", cls.__feeds[fK].uri()
		print """
===========

"""
	
	@classmethod
	def acquireLock(cls):
		cls._lock.acquire()
	
	@classmethod
	def releaseLock(cls):
		cls._lock.release()
	
	@classmethod
	def saveState(cls):
		cls._feedCacheShelf.acquireLock()
		try:
			feedsArgs = []
			
			for fK in cls.__feeds.keys():
				feedsArgs.append(cls.__feeds[fK].getKWArgsForConstruct())
			
			cls._feedCacheShelf.set('feedcache', feedsArgs)
		finally:
			cls._feedCacheShelf.releaseLock()
	
	@classmethod
	def loadState(cls):
		cls._feedCacheShelf.acquireLock()
		try:
			feedsArgs = cls._feedCacheShelf.getWithDefault('feedcache', {})
			cls.__feeds = {}
			for feedKWs in feedsArgs:
				feed = Feed.constructFromKWArgs(feedKWs)
				cls.__feeds[feedKWs[u'uri']] = feed
		finally:
			cls._feedCacheShelf.releaseLock()

	@classmethod
	def allFeeds(cls):
		for feedK in cls.__feeds.keys():
			yield cls.__feeds[feedK]
		raise StopIteration

	@classmethod
	def getFeedFromURINoLock(cls, feedURI):
		assert cls.__feeds is not None
		if not cls.__feeds.has_key(feedURI):
			cls.__feeds[feedURI] = Feed(feedURI)
		
		return cls.__feeds[feedURI]

	@classmethod
	def getEnclosureForDownloadURINoLock(cls, downloadURI):
		# FIXME: this is a hack right now, which
		# assumes a feed has been pre-cached if
		# items from it are being downloaded
		assert cls.__feeds is not None
		
		for feedK in cls.__feeds.keys():
			for episode in cls.__feeds[feedK].episodes():
				for enc in episode.enclosures():
					if enc._downloadURI() == downloadURI:
						return enc
		
		return None

	@classmethod
	def _dump(cls, level=0):
		print "{FeedCache:"
		for feedK in cls.__feeds.keys():
			print " " * (level + 2) + "%s =" % feedK, cls.__feeds[feedK]._dump(level + 4)
		print (" " * level) + "}"

	@classmethod
	def purgeFeedForURI(cls, uri):
		cls._lock.acquire()
		try:
			if cls.__feeds.has_key(uri):
				del cls.__feeds[uri]
		finally:
			cls._lock.release()
