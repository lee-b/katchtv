#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email lee.b@digitalunleashed.com) for a copy.
#
import sys
import os
import utils
import pickle
import threading

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import config
import DLTasks
import Feed
import DataStore

sys.path.append(os.path.join(appRoot, 'code/TaskPool'))
import TaskPool

class Item:
	# FIXME: this pickles and unpickles on each access!  Don't know what
	# I was thinking when I did that :D
	
	# Available Statistics
	URI = 'URI'
	TITLE = 'Title'
	DESCRIPTION = 'Description'
	TOTAL_BYTES = 'Total size in bytes'
	TOTAL_BYTES_DOWNLOADED = 'Total bytes downloaded'
	TOTAL_BYTES_UPLOADED = 'Total bytes uploaded'
	PERCENT_COMPLETE = 'Percent downloaded'
	DOWNLOAD_STATUS = 'Download status'
	LOCAL_PATH = 'Local path'
	DOWNLOAD_BPS_AVERAGE = 'Download speed (bits per second)'
	UPLOAD_BPS_AVERAGE = 'Upload speed (bits per second)'
	TIME_ELAPSED = 'Time taken so Far'
	TIME_REMAINING = 'Time remaining'
	TIME_ESTIMATED = 'ETA'
	MIMETYPE = 'Mimetype'
	PRETTY_TYPE = 'Type'
	ERRORMSG = 'Error'
	MEDIA_FILES = 'Media files'
	DOWNLOAD_METHOD = 'Download Method'
	SOURCE_FEED_URI = 'Source Feed URI'
	
	# Possible values for the DOWNLOAD_STATUS statistic
	DLSTATUS__QUEUED = 'Queued for download; please wait.'
	DLSTATUS__INITIALISING = 'initialising'
	DLSTATUS__DOWNLOADING = 'downloading'
	DLSTATUS__COMPLETE = 'complete'
	
	# Possible values for DOWNLOAD_METHOD
	DLMETHOD__DIRECT = 'Direct Download (HTTP, FTP, etc.)'
	DLMETHOD__BITTORRENT = 'P2P (Bittorrent)'
	
	_requiredStats = [
		URI,
		TITLE,
		DESCRIPTION,
		SOURCE_FEED_URI,
	]
	
	_statDefaults = {
		DOWNLOAD_STATUS: DLSTATUS__QUEUED,
		MIMETYPE: 'application/octet-stream',
	}

	def acquireLock(self):
		pass
	
	def releaseLock(self):
		pass
	
	def __init__(self, kwArgs):
		self.__lock = utils.NamedLock("Lock for (unknown) MediaItem")
		self.__lock.acquire()
		try:
			self.__task = None
			self.__statistics = {}
			
			for itemK in Item._statDefaults.keys():
				self.setStatisticNoLock(itemK, Item._statDefaults[itemK])
				
			for itemK in kwArgs.keys():
				self.setStatisticNoLock(itemK, kwArgs[itemK])
			
			# make sure, at this stage, that all required arguments are available
			for statK in Item._requiredStats:
				if not self.hasStatisticNoLock(statK):
					raise AttributeError, "Keyword argument %s was not supplied to Media.Item.__init__()" % statK
			
			self.__localPath = None
			
			enclosure = Feed.FeedCache.getEnclosureForDownloadURINoLock(kwArgs[Item.URI])
			if enclosure:
				enclosure._attachMediaItem(self)
		finally:
			self.__lock.release()
	
	def hasTask(self):
		self.__lock.acquire()
		res = self.__task is not None
		self.__lock.release()
		return res

	def setTaskNoLock(self, task):
		self.__task = task
	
	def hasStatisticNoLock(self, name):
		return name in self.__statistics.keys()
	
	def getStatisticNoLock(self, name):
		return pickle.loads(self.__statistics[name])
	
	def getStatisticNoLockDefault(self, name, defaultVal=None):
		try:
			self.getStatisticNoLock(name)
		except KeyError:
			return defaultVal
	
	def getStatistic(self, name):
		self.__lock.acquire()
		res = self.getStatisticNoLock(name)
		self.__lock.release()
		return res
	
	def getStatisticDefault(self, name, default):
		self.__lock.acquire()
		res = self.getStatisticNoLockDefault(name, default)
		self.__lock.release()
		return res
	
	def setStatisticNoLock(self, name, val):
		self.__statistics[name] = pickle.dumps(val)

	def setStatistic(self, name, val):
		self.__lock.acquire()
		self.setStatisticNoLock(name, val)
		self.__lock.release()
	
	def eachStatistic(self):
		"""Generates all statistics available for the media item, in (key, value) tuples.  Does so in a thread-safe way."""
		self.__lock.acquire()
		res = {}
		for rK in self.__statistics:
			res[rK] = self.__statistics[rK]
		self.__lock.release()
		
		for rK in res.keys():
			yield (rK, pickle.loads(res[rK]))
		raise StopIteration
	
	def getChosenStatistics(self, chosenStats):
		"""Returns the chosen statistics, as a dictionary, in a thread-safe way.  Silently ignores unavailable statistics."""
		self.__lock.acquire()
		
		res = {}
		for k in chosenStats:
			if self.__statistics.has_key(k):
				res[k] = pickle.loads(self.__statistics[k])
		
		self.__lock.release()
		
		return res
	
	def isDownloaded(self):
		#fixme: re-enable these locks
		self.__lock.acquire()
		return self.isDownloadedNoLock()
		self.__lock.release()
		return res
	
	def isDownloadedNoLock(self):
		return self.getStatisticNoLock(Item.DOWNLOAD_STATUS) == Item.DLSTATUS__COMPLETE
	
	def encodeForURIFindNoLock(self):
		"""Encodes the item so that it can later be refound during the
		program session, from the returned string.  The returned string
		is suitable for appending to an HTTP GET URL."""
		args = {
			"URI": self.getStatisticNoLock(Item.URI)
		}
		return utils.argsToURI(args)
	
	def __unpickleAllStats(self):
		stats = {}
		for sK in self.__statistics.keys():
			stats[sK] = pickle.loads(self.__statistics[sK])
		return stats
	
	def encodeForURIConstruct(self):
		"""Encodes the item so that it can later be rebuilt entirely from
		the returned string. The returned string is suitable for appending
		to an HTTP GET URL."""
		stats = self.__unpickleAllStats()
		return Item.encodeValuesForURIConstruct(stats)
	
	def purge(self):
		"""Removes the file from the local media store, if it has already been downloaded."""
		self.__lock.acquire()
		
		if self.__task:
			self.__task.abort()
		
		try:
			try:
				localPath = self.getStatistic(Item.LOCAL_PATH)
				if localPath is not None:
					if os.path.isdir(localPath):
						# fixme: just using rm for now
						os.system('rm -rf "%s"' % localPath)
					else:
						try:
							os.unlink(localPath)
						except OSError:
							# if it's already gone for some reason, that's OK, just print a warning
							print u"Warning: tried to delete '%s', but it was already gone." % self.__localPath
				
				utils.pruneSubPaths(config.mediaStoreRoot)
			except KeyError:
				pass
		finally:
			enclosure = Feed.FeedCache.getEnclosureForDownloadURINoLock(self.getStatisticNoLock(Item.URI))
			if enclosure:
				enclosure._detachMediaItem()
			
			self.__lock.release()

	def __str__(self):
		uri = self.getStatisticNoLock(Item.URI)
		return "{ MediaItem: %s }" % uri
	
	def encodeValuesForURIConstruct(cls, kwArgs):
		"""Does the same this as encodeForURIConstruct, except that this is a class method, and requires
		no Item to currently exist.  Instead, appropriate values are supplied as arguments."""
		for stat in cls._requiredStats:
			if not stat in kwArgs.keys():
				raise AttributeError, "The statistic %s must be supplied for a reconstructable Media Item URI." % stat
		
		return utils.argsToURI(kwArgs)
	encodeValuesForURIConstruct = classmethod(encodeValuesForURIConstruct)

class Manager(TaskPool.Pool):
	def __init__(self, numThreads=config.numDownloadThreads):
		TaskPool.Pool.__init__(self, numThreads)
		self.__mediaItems = {}
		self._loadItems()
	
	def _loadItems(self):
		downloadsDS = DataStore.DataStore(config.downloadsNewFile)
		try:
			itemPack = downloadsDS.get('mediaitems')
			for packedItem in itemPack:
				# construct the item.  No need to remember the
				# result, since constructing it automatically
				# registers it with self
				self.constructFromURI(packedItem)
		except KeyError:
			# doesn't exist; that's OK
			pass

	def _saveItems(self):
		itemDS = DataStore.DataStore(config.downloadsNewFile)
		itemDS.acquireLock()
		try:
			itemPack = []
			
			for itemK in self.__mediaItems.keys():
				uri = self.__mediaItems[itemK].encodeForURIConstruct()
				itemPack.append(uri)
			
			itemDS.set('mediaitems', itemPack)
		finally:
			itemDS.releaseLock()
	
	def purgeItem(self, mediaItem):
		miURI = mediaItem.getStatistic(Item.URI)
		assert self.__mediaItems.has_key(miURI)
		mediaItem.purge()
		del self.__mediaItems[miURI]
		self._saveItems()
	
	def itemForURI(self, uri):
		return self.__mediaItems[uri]
	
	def numItems(self):
		return len(self.__mediaItems.keys())
	
	def eachDownloaded(self):
		for miURI in self.__mediaItems:
			if self.__mediaItems[miURI].isDownloaded():
				yield self.__mediaItems[miURI]
	
	def numDownloaded(self):
		count = 0
		for miURI in self.__mediaItems:
			if self.__mediaItems[miURI].isDownloaded():
				count += 1
		return count
	
	def eachInProgress(self):
		for miURI in self.__mediaItems:
			if not self.__mediaItems[miURI].isDownloaded():
				yield self.__mediaItems[miURI]
	
	def numInProgress(self):
		count = 0
		for miURI in self.__mediaItems:
			if not self.__mediaItems[miURI].isDownloaded():
				count += 1
		return count
	
	def findFromURI(self, uri):
		"""Class method; finds a Media Item from a URI-encoded string which refers to it."""
		kwArgs = utils.uriToArgs(uri)
		assert kwArgs.has_key(Item.URI)
		
		realURI = kwArgs[Item.URI]
		
		res = self.__mediaItems[realURI]
		return res
	
	def constructFromURI(self, uri):
		res = utils.uriToArgs(uri)
		for stat in Item._requiredStats:
			if not res.has_key(stat):
				raise AttributeError, "The statistic %s must be supplied for a reconstructable Media Item URI." % stat
		
		mediaItem = Item(res)
		assert isinstance(mediaItem, Item)
		
		realURI = mediaItem.getStatistic(Item.URI)
		try:
			self.__mediaItems[realURI] = mediaItem
		except KeyError:
			print "mediaItem ", realURI, " (for", uri, ") is missing"
			return None
		
		self._saveItems()
		
		return mediaItem
	
	def beginNewDownloads(self):
		"""Scans the list of managed media items, and begins a
		download task for any which aren't complete, but don't
		have a download task yet either."""
		for miURI in self.__mediaItems:
			mediaItem = self.__mediaItems[miURI]
			
			#fixme: re-enable this locking wrapper,
			# now that we're using rlocks again.
			#mediaItem.acquireLock()
			try:
				dlStatus = mediaItem.getStatisticNoLock(Item.DOWNLOAD_STATUS)
				if dlStatus == Item.DLSTATUS__COMPLETE:
					continue
				
				if not mediaItem.hasTask():
					task = DLTasks.dlTaskForMediaItem(mediaItem)
					mediaItem.setTaskNoLock(task)
					task.queueInPool(self)
					self._saveItems()
			finally:
				#mediaItem.releaseLock()
				pass
