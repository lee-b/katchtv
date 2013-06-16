#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email leebraid@gmail.com) for a copy.
#
import os
import sys
import datetime
import time

from qt import QObject, QListView, QListViewItem, QTimer, QString, SIGNAL, SLOT

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import config
import FeedReaderTask
import Feed
import utils

# make this global for now, just to implement it quickly
bmarksLock = utils.NamedLock("Bookmarks Lock")

sys.path.append(os.path.join(appRoot, 'code/TaskPool'))
import TaskPool

# Define better (and more robust) ways to refer to
# individual columns.
COL_NAME = 0
COL_NUMNEW = 1
COL_UPDATE_MINUTES = 2
COL_URI = 3
COL_LAST_CHECK_TIMESTAMP = 4

class FeedUpdaterTask(FeedReaderTask.FeedReaderTask):
	def __init__(self, feed, bookmarksView):
		assert isinstance(feed, Feed.Feed)
		FeedReaderTask.FeedReaderTask.__init__(self, feed)
		self.__bookmarksView = bookmarksView
	
	def _numNewEpisodes(self):
		"""Retrieves the number of new episodes since a feed (subscribed
		channel) item was last checked."""
		return 
	
	@utils.synchronized(bmarksLock)
	def finished(self):
		"""Finishes feed update, by checking for new entries, and updating the UI"""
		
		FeedReaderTask.FeedReaderTask.finished(self)
		
		feed = self.feed()
		
		# set up a variable which specifies whether we should save
		changed = False
		
		# if it's a newly added feed, then use the channel
		# title we just (hopefully) retrieved.
		feedTitle = feed.title()
		listviewitem = self.__bookmarksView.getItemForFeed(feed)
		if not listviewitem:
			# feed has been deleted since we began updating
			return
			
		if feedTitle != unicode(listviewitem.text(COL_NAME)):
			changed = True
		
		# get the number of new episodes and 
		numNew = feed.numNewEpisodes()
		if numNew > 0:
			changed = True
		
		# save if necessary
		if changed:
			self.__bookmarksView.updateItemForFeed(feed)
			self.__bookmarksView._saveBookmarks('New channel information received')

class KTVBookmarksListView(QListView):
	"""Implements a QListView which understands and displays directories, and subscribed
	channels."""
	
	def __init__(self, parent, win):
		"""Initialises a new KTVBookmarksListView object.  Requires a parent widget, and the
		KTVMainWindow to which it will belong."""
		
		# initialise our parent class
		QListView.__init__(self, parent)
		self._window = win
		
		self._bmarksLock = utils.NamedLock("BookmarksListView lock")
		
		# enable item expanders ([+] boxes) and draw lines to indicate hierarchy
		self.setRootIsDecorated(True)
		
		# show the sort arrow in list column headers
		self.setShowSortIndicator(True)
		
		# setup the columns
		self.addColumn(u'Bookmark')
		self.setSorting(COL_NAME, True)
		self.setColumnWidthMode(COL_NAME, QListView.Manual)
		self.setColumnWidth(COL_NAME, config.nameColumnWidth)
		
		self.addColumn(u'New')
		self.setColumnWidthMode(COL_NUMNEW, QListView.Manual)
		self.setColumnWidth(COL_NUMNEW, config.numNewColumnWidth)
		
		self.addColumn(u'Update Mins')
		self.setColumnWidthMode(COL_UPDATE_MINUTES, QListView.Manual)
		self.setColumnWidth(COL_UPDATE_MINUTES, config.updateMinsColumnWidth)
		
		self.addColumn(u'URI')
		self.setColumnWidthMode(COL_URI, QListView.Maximum)
		
		self.addColumn(u'Last Check Timestamp')
		self.setColumnWidthMode(COL_LAST_CHECK_TIMESTAMP, QListView.Manual)
		self.setColumnWidth(COL_LAST_CHECK_TIMESTAMP, 0)
		
		# setup the feed updater threadpool here, so bookmark updates can be queued on it
		self.__feedTaskPool = FeedReaderTask.FeedTaskPool(config.numFeedThreads)
		
		# add the subscribed channel and the channel directory bookmarks
		self._initBookmarks()
		
		# hook some events that we're interested in
		QObject.connect(self, SIGNAL(str(u'itemRenamed(QListViewItem*,int,const QString&)')), self._renamed)
		
		# set a timer to check if channels need updating each minute
		self._updateTimer = QTimer()
		self._updateTimer.connect(self._updateTimer,SIGNAL(str(u"timeout()")), self._updateChannels)

	@utils.synchronized(bmarksLock)
	def enableThreads(self):
		self._updateTimer.start(config.updateChannelsTimerMillisecs)

	@utils.synchronized(bmarksLock)
	def disableThreads(self):
		self.__feedTaskPool.stop()
		self._updateTimer.stop()

	@utils.synchronized(bmarksLock)
	def _initBookmarks(self):
		"""Sets up an initial list of channel directories and subscribed
		channel bookmarks, along with the special entries like
		"Welcome", "Downloads in Progress", and "Ready to Watch". """
		
		# make the main headings
		self.welcomeBMark = self._makeItem(self, \
			name=u'1. Welcome', \
			uri=u'katchtv:welcome:')
		self.dloadsInProgressBMark = self._makeItem(self, \
			name=u'2. Downloads in Progress', \
			uri=u'katchtv:downloads:')
		self.readyToWatchBMark = self._makeItem(self, \
			name=u'3. Ready to Watch', \
			uri=u'katchtv:ready:')
		
		self.allChannelsBMark = self._makeItem(self, name=u'4. Subscribed Channels')
		self.allChannelsBMark.setDropEnabled(True)
		self.allChannelsBMark.setOpen(True)
		
		self.directoriesBMark = self._makeItem(self, name=u'5. Channel Directories')
		self.directoriesBMark.setOpen(True)
		
		self.__notRecommendedDirCat = self._makeItem(self.directoriesBMark, name=u'D. Not recommended')
		self.__dircats = {}
		for dircat in config.dirCats:
			if dircat in config.notRecommendedDirCats:
				self.__dircats[dircat] = self._makeItem(self.__notRecommendedDirCat, name=dircat)
			else:
				self.__dircats[dircat] = self._makeItem(self.directoriesBMark, name=dircat)
		
		self._loadDirectories()
		
		self.__dircats[config.DIRCAT_RECOMMENDED].setOpen(True)
		
		self._deleteQueue = []
		
		# Other, dynamically loaded bookmarks are handled separately
		self._loadBookmarks()

	@utils.synchronized(bmarksLock)
	def _loadDirectories(self):
		"""Loads the channel directories into the listview."""
		for k in config.defaultDirectories.keys():
			name = config.defaultDirectories[k][config.DIRECTORY_NAME]
			cat = config.defaultDirectories[k][config.DIRECTORY_CATEGORY]
			self.addDirectory(k, name, cat)

	@utils.synchronized(bmarksLock)
	def _loadBookmarks(self):
		"""Loads the subscribed channel bookmarks from a configuration file,
		or uses the defaults if necessary."""
		Feed.FeedCache.acquireLock()
		try:
			# clear the current bookmark list
			item = self.allChannelsBMark.firstChild()
			while item is not None:
				self.takeItem(item)
				nextItem = item.nextSibling()
				del(item)
				item = nextItem
			
			# load all saved feeds
			Feed.FeedCache.loadState()
			
			channelCount = 0
			for feed in Feed.FeedCache.allFeeds():
				self.addChannel(feed)
				channelCount += 1
			
			if channelCount == 0:
				# no channels loaded, so add defaults
				print "adding default feeds."
				for uri in config.defaultBookmarks.keys():
					name = config.defaultBookmarks[uri][u'name']
					updateMins = config.defaultBookmarks[uri][u'updateMins']
					feed = Feed.FeedCache.getFeedFromURINoLock(uri)
					assert isinstance(feed, Feed.Feed)
					feed.setTitle(name)
					feed.setUpdateMins(updateMins)
					self.addChannel(feed)
				
				# save the newly set defaults
				self._saveBookmarks()
		finally:
			Feed.FeedCache.releaseLock()
	
	@utils.synchronized(bmarksLock)
	def _saveBookmarks(self, reason=None):
		"""Saves the subscribed bookmarks."""
		Feed.FeedCache.acquireLock()
		try:
			Feed.FeedCache.saveState()
			
			# inform the user of what just happened, using the supplied
			# reason argument
			if reason:
				reason = u"Bookmarks saved; " + reason
			else:
				reason = u"Bookmarks saved"
			self._setStatus(reason)
		finally:
			Feed.FeedCache.releaseLock()


	@utils.synchronized(bmarksLock)
	def getItemForFeed(self, feed):
		"""Retrieves the listitem for the subscribed channel that corresponds
		to a given Feed."""
		assert isinstance(feed, Feed.Feed)
		return self.getItemForURI(feed.uri())
	
	@utils.synchronized(bmarksLock)
	def getItemForURI(self, feedURI):
		"""Retrieves the listitem for the subscribed channel that corresponds
		to a given URI."""
		item = self.allChannelsBMark.firstChild()
		while item is not None:
			listedURI = unicode(item.text(COL_URI))
			if listedURI == feedURI:
				return item
			item = item.nextSibling()
		return None

	@utils.synchronized(bmarksLock)
	def getFeedForItem(self, item):
		Feed.FeedCache.acquireLock()
		try:
			for f in Feed.FeedCache.allFeeds():
				if f.uri() == item.text(COL_URI):
					return f
			
			return None
		finally:
			Feed.FeedCache.releaseLock()
	
	@utils.synchronized(bmarksLock)
	def queueChannelUpdate(self, channel):
		"""Updates a subscribed channel listviewitem if necessary, by queuing a FeedReaderTask."""
		feedURI = unicode(channel.text(COL_URI))
		
		Feed.FeedCache.acquireLock()
		try:
			feed = Feed.FeedCache.getFeedFromURINoLock(feedURI)
			
			if self.__feedTaskPool.attemptToAcquireDownloadLock(feed):
				if feed.updateIsDue():
					feedTask = FeedUpdaterTask(feed, self)
					feedTask.queueInPool(self.__feedTaskPool)
				self.__feedTaskPool.releaseDownloadLock(feed)
		finally:
			Feed.FeedCache.releaseLock()
	
	@utils.synchronized(bmarksLock)
	def _updateChannels(self):
		"""Updates all subscribed channels items, by checking their feeds for
		new content."""
		# Queue anything else that needs updating.  Do this by
		# first building a list of channels in advance, and then
		# processing them later, so that we don't lock the UI
		# for too long
		channelList = []
		channel = self.allChannelsBMark.firstChild()
		while channel is not None:
			channelList.append(channel)
			channel = channel.nextSibling()
		
		# now update each channel in the list
		for ch in channelList:
			self.queueChannelUpdate(ch)

	@utils.synchronized(bmarksLock)
	def _makeItem(self, parent, name, numNew=u'', updateMinutes=u'', uri=u'', lastCheckTimestamp=u''):
		"""Creates a new listitem, performing various checks and doing other work
		depending on the parent of the item, etc."""
		# don't check for allChannelsBMark if this is a rootnode -- especially
		# since allChannels might *be* the rootnode ;)
		if parent != self:
			# set different defaults if this is a channel
			if parent == self.allChannelsBMark:
				if updateMinutes == u'':
					updateMinutes = config.defaultChannelUpdateMins
				if lastCheckTimestamp == u'':
					lastCheckTimestamp = config.dawnOfTime
		
		# don't show numNew if it's not a number (ie, it's a blank/missing string), or it's less than 1
		try:
			int(numNew)
			assert numNew > 0
		except (TypeError, ValueError, AssertionError):
			numNew = u""
		
		# set a user-friendly name if real name isn't
		# known yet
		if name is None or name == "None":
			name = "{please wait; retrieving details}"
		
		# actually create the item
		item = QListViewItem(parent, name, unicode(numNew), unicode(updateMinutes), uri, unicode(lastCheckTimestamp))
		
		# again, don't compare parents if they might not exist yet
		if parent != self:
			# configure item differently if this is a channel or a directory
			if parent == self.allChannelsBMark:
				item.setRenameEnabled(COL_UPDATE_MINUTES, True)
				item.setRenameEnabled(COL_URI, True)
			item.setRenameEnabled(COL_NAME, True)
		
		return item

	@utils.synchronized(bmarksLock)
	def haveChannel(self, uri):
		"""Simply returns true if the given URI has already been added to the
		list of subscribed channels."""
		return self.getItemForURI(uri) is not None

	@utils.synchronized(bmarksLock)
	def _setStatus(self, msg):
		"""Updates the window's status bar with a new message."""
		self._window.statusBar().message(msg)
	
	@utils.synchronized(bmarksLock)
	def getFeedTitleFromFeed(self, feed):
		"""Gets the name for a subscribed channel quickly, just by
		checking its name column in the list."""
		assert isinstance(feed, Feed.Feed)
		channel = self.getItemForURI(feed.uri())
		return unicode(channel.text(COL_NAME))
	
	@utils.synchronized(bmarksLock)
	def addChannel(self, feed):
		title = feed.title()
		uri = feed.uri()
		numNew = feed.numNewEpisodes()
		updateMins = feed.updateMins()
		lastCheck = feed.lastCheck()
		
		item = self._makeItem(self.allChannelsBMark, name=title, numNew=numNew, updateMinutes=updateMins, uri=uri, lastCheckTimestamp=lastCheck)
	
	@utils.synchronized(bmarksLock)
	def addDirectory(self, uri, title, cat):
		"""Adds a channel directory to the list."""
		if cat == None:
			parent = self.directoriesBMark
		else:
			parent = self.__dircats[cat]
		
		self._makeItem(parent, name=title, uri=uri)

	@utils.synchronized(bmarksLock)
	def _isEditableEntry(self, item):
		"""Returns True if a given item should be renamed.  Currently only allows
		renaming of subscribed channels, but should support renaming
		channel directories in future too."""
		if item is None:
			return False
		
		if item in (self.readyToWatchBMark, self.allChannelsBMark, self.dloadsInProgressBMark):
			return False
		else:
			return True
	
	@utils.synchronized(bmarksLock)
	def _renamed(self, item, col, text):
		"""A hook (a Qt signal slot, in fact) which is called when
		an item is renamed by the user."""
		if col == COL_NAME:
			f = self.getFeedForItem(item)
			f.setTitle(text)
		elif col == COL_UPDATE_MINUTES:
			f = self.getFeedForItem(item)
			try:
				f.setUpdateMins(int(text))
			except ValueError:
				# not a valid number; reset
				item.setText(COL_UPDATE_MINUTES, str(f.updateMins()))
		
		self._saveBookmarks()
	
	@utils.synchronized(bmarksLock)
	def getLastCheckDateForURI(self, uri):
		listviewitem = self.getItemForURI(uri)
		return self._decodeDateTime(unicode(listviewitem.text(COL_LAST_CHECK_TIMESTAMP)))

	@utils.synchronized(bmarksLock)
	def setLastCheckForFeed(self, feed, lastCheckDate):
		assert isinstance(feed, Feed.Feed)
		item = self.getItemForURI(feed.uri())
		item.setText(COL_LAST_CHECK_TIMESTAMP, self._encodeDateTime(lastCheckDate))
	
	@utils.synchronized(bmarksLock)
	def updateItemForFeed(self, feed):
		assert isinstance(feed, Feed.Feed)
		
		title = feed.title()
		uri = feed.uri()
		
		numNew = feed.numNewEpisodes()
		try:
			numNew = int(numNew)
			assert numNew > 0
		except (TypeError, ValueError, AssertionError):
			numNew = u''
		
		lastUpdate = feed.lastCheck()
		updateMins = feed.updateMins()
		
		item = self.getItemForURI(uri)
		item.setText(COL_NUMNEW, unicode(numNew))
		item.setText(COL_URI, uri)
		item.setText(COL_NAME, unicode(title))
		item.setText(COL_UPDATE_MINUTES, unicode(updateMins))
		item.setText(COL_LAST_CHECK_TIMESTAMP, unicode(lastUpdate))
		
		self._saveBookmarks()

	@utils.synchronized(bmarksLock)
	def delCurrentItem(self):
		"""Deletes the currently selected listview item"""
		item = self.currentItem()
		if item.parent() != self.allChannelsBMark:
			print "Can't delete", unicode(item.text(COL_NAME)), "; it's parent is", unicode(item.parent().text(COL_NAME))
			return
		
		itemURI = unicode(item.text(COL_URI))
		Feed.FeedCache.purgeFeedForURI(itemURI)
		
		self.allChannelsBMark.takeItem(item)
		del(item)
		self._saveBookmarks()
