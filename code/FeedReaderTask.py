#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email lee.b@digitalunleashed.com) for a copy.
#
import os
import sys
import threading

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import Feed
import TaskPool
import utils

class FeedReaderTask(TaskPool.Task):
	def __init__(self, feed):
		assert isinstance(feed, Feed.Feed)
		self.__feed = feed
	
	def feed(self):
		return self.__feed
	
	def __call__(self, **kwArgs):
		TaskPool.Task.__call__(self, **kwArgs)
		
		# FIXME: are we using the __parsedFeed result somewhere else,
		# or is it not implemented yet?
		self.__feed.doUpdate()
	
	def __str__(self):
		return "FeedReaderTask(" + str(self.__feed) + ")"

class FeedTaskPool(TaskPool.Pool):
	def __init__(self, numThreads):
		TaskPool.Pool.__init__(self, numThreads)
		self.__masterFeedLock = threading.Lock()
		self.__feedURIs = {}

	def attemptToAcquireDownloadLock(self, feed):
		self.__masterFeedLock.acquire(False)
		try:
			feedURI = feed.uri()
			if not self.__feedURIs.has_key(feedURI):
				self.__feedURIs[feedURI] = utils.NamedLock("Lock for Feed URI '%s'" % feedURI)
			return self.__feedURIs[feedURI].acquire(False)
		finally:
			self.__masterFeedLock.release()

	def releaseDownloadLock(self, feed):
		self.__masterFeedLock.acquire()
		try:
			self.__feedURIs[feed.uri()].release()
		finally:
			self.__masterFeedLock.release()
