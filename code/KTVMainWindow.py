#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email lee.b@digitalunleashed.com) for a copy.
#
import sys
import os

from kdeui import KPopupMenu, KInputDialog
from kparts import KParts
from qt import	QObject, QHBox, QVBox, QSplitter, QPushButton, \
							QString, SIGNAL, SLOT, QPixmap, QTimer

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import KTVHTMLPart
import KTVBookmarksListView
import Media
import utils
import config
import Feed

class KTVMainWindow(KParts.MainWindow):
	"""Implements the main KatchTV application window."""

	def __init__(self, title):
		"""Initialises a new window object."""
		self._stopped = True
		
		KParts.MainWindow.__init__(self, None, str(title))
		self.setCaption(config.appFullVersion)
		
		self._initWidgets()
		
		self.__mediaManager = Media.Manager()
		
		self.__downloadTimer = QTimer()
		self.__downloadTimer.connect(self.__downloadTimer,SIGNAL(str(u"timeout()")), self.__updateDownloads)
		
		self.browser.goToURL(u'katchtv:welcome:')

	def saveAll(self):
		self.__mediaManager._saveItems()
	
	def __updateDownloads(self):
		self.__mediaManager.beginNewDownloads()
	
	def enableThreads(self):
		# start everything, and mark as running
		self.__downloadTimer.start(config.updateDownloadsTimerMillisecs)
		self.bmarksList.enableThreads()
		self._stopped = False
	
	def disableThreads(self):
		# stop in the order of slowest to fastest, hoping it'll
		# all finish around the same time
		self.bmarksList.disableThreads()
		self.__mediaManager.stop()
		self.__downloadTimer.stop()
		self._stopped = True
	
	def getMediaManager(self):
		return self.__mediaManager
	
	def isStopped(self):
		"""Returns True if the application should not run yet (ie, if
		it has not been fully initialised)."""
		return self._stopped

	def _initWidgets(self):
		"""Initialises all of the main widgets in the window."""
		global appRoot
		
		appIconPath = os.path.join(appRoot, "images/miniicon.png")
		self.setIcon(QPixmap(appIconPath))
		
		self.mainBox = QHBox(self)
		self.mainSplitter = QSplitter(self.mainBox)
		
		self.bmarksListBox = QVBox(self.mainSplitter)
		self.bmarksListBox.setMaximumWidth(250)
		
		self.bmarksList = KTVBookmarksListView.KTVBookmarksListView(self.bmarksListBox, self)
		QObject.connect(self.bmarksList, SIGNAL(str(u'doubleClicked(QListViewItem *)')), self._bookmarkChosen)
		
		self.browserBox = QVBox(self.mainSplitter)
		self.browser = KTVHTMLPart.KTVHTMLPart(self.browserBox, self)
		
		self.setCentralWidget(self.mainBox)
		
		self._buttonBox = QHBox(self.bmarksListBox)
		self._addButton = QPushButton(u"&Add", self._buttonBox, str(u""))
		QObject.connect(self._addButton, SIGNAL(str(u'clicked()')), self._addItem)
		
		self._deleteButton = QPushButton(u"&Delete", self._buttonBox, str(u""))
		QObject.connect(self._deleteButton, SIGNAL(str(u'clicked()')), self._deleteItem)
		
		self._backButton = QPushButton(u"&Back", self.bmarksListBox, str(u""))
		QObject.connect(self._backButton, SIGNAL(str(u'clicked()')), self._back)
		
		self._helpButton = QPushButton(u"&Help", self.bmarksListBox, str(u""))
		QObject.connect(self._helpButton, SIGNAL(str(u'clicked()')), self._help)
		
		self.statusBar().message(u"KatchTV is now ready for use.")

	def _help(self):
		"""A hook (a Qt signal slot, actually) which is called when the user
		clicks the "Help" button.  Loads the manual into the browser."""
		self.browser.goToURL(u'katchtv:help:')
	
	def _back(self):
		"""A hook (a Qt signal slot) which is called when the user clicks the
		"Back" button.  Navigates one step back through the browser history."""
		self.browser.loadPreviousPage()
	
	def _addItem(self):
		"""A hook (Qt signal slot) which is called when the user clicks
		the "Add" button.  Presents a dialog, asking the user for the
		feed URI to add."""
		validURI = False
		firstTry = True
		while not validURI:
			if firstTry:
				uri, confirmed = KInputDialog.text(u"Add Feed Bookmark", QString(u"Please enter the channel's feed URI (or URL) here."))
				uri = unicode(uri)
			else:
				uri, confirmed = KInputDialog.text(u"Add Feed Bookmark", u"The URI you entered was invalid.  Please try again, or cancel.", QString(uri))
				uri = unicode(uri)
			firstTry = False
			if confirmed:
				validURI = utils.isAFeed(uri)
			else:
				# user cancelled the input
				return
		feed = Feed.FeedCache.getFeedFromURINoLock(uri)
		self.bmarksList.addChannel(feed)
	
	def _deleteItem(self):
		"""A hook (Qt signal slot) which is called when the user
		clicks the Delete button.  Deletes the selected item,
		if that item is a subscribed channel.  Otherwise, informs
		the user that they cannot delete the item."""
		self.bmarksList.delCurrentItem()

	def _bookmarkChosen(self, item):
		"""A hook (Qt signal slot) which is called when the user double-clicks
		on an item in the listview.  Checks if the item has a URI column entry,
		and if so, navigates to it."""
		title = item.text(KTVBookmarksListView.COL_NAME)
		uri = item.text(KTVBookmarksListView.COL_URI)
		if title != u'' and uri != u'':
			self.browser.goToURL(uri)

	def getBookmarksList(self):
		return self.bmarksList
