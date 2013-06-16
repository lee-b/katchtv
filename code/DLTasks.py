#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email leebraid@gmail.com) for a copy.
#
import os
import sys
import threading


appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import Media
import utils
import config
import TaskPool

sys.path.append(os.path.join(appRoot, u'code/thirdparty/urlgrabber-2.9.9'))
import urlgrabber
from urlgrabber.progress import RateEstimator

sys.path.append(os.path.join(appRoot, u'code/thirdparty'))
import timeoutsocket
from ptvbittorrent import download as BTDownload

class MediaItemDownloadTask(TaskPool.Task):
	def _notifyError(self, msg):
		self.acquireLock()
		try:
			self.__mediaItem.setStatisticNoLock(Media.Item.ERRORMSG, unicode(msg))
		finally:
			self.releaseLock()
	
	def __init__(self, mediaItem):
		assert mediaItem is not None
		
		TaskPool.Task.__init__(self)
		self.acquireLock()
		try:
			self.__mediaItem = mediaItem
			mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, Media.Item.DLSTATUS__QUEUED)
		finally:
			self.releaseLock()

	def acquireLock(self):
		pass
	
	def releaseLock(self):
		pass
	
	def getMediaItemNoLock(self):
		self.acquireLock()
		try:
			return self.__mediaItem
		finally:
			self.releaseLock()
	
	def getMediaItem(self):
		self.acquireLock()
		try:
			return self.getMediaItemNoLock()
		finally:
			self.releaseLock()

	def finished(self):
		self.acquireLock()
		try:
			TaskPool.Task.finished(self)
			self.__mediaItem.setTaskNoLock(None)
		finally:
			self.releaseLock()

class MediaItemURIDownloadTask(MediaItemDownloadTask):
	class Updater(RateEstimator):
		def __init__(self, mediaItemTask):
			RateEstimator.__init__(self)
			self.__task = mediaItemTask
		
		def start(self, filename, url, path, size, text=None):
			RateEstimator.start(self, total=size)
			self.__task.getMediaItem().setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, Media.Item.DLSTATUS__INITIALISING)
		
		def end(self, amountRead):
			mediaItem = self.__task.getMediaItem()
			mediaItem.acquireLock()
			try:
				mediaItem.setStatisticNoLock(Media.Item.PERCENT_COMPLETE, 100.0)
				mediaItem.setStatisticNoLock(Media.Item.TOTAL_BYTES_DOWNLOADED, amountRead)
				mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, Media.Item.DLSTATUS__COMPLETE)
			finally:
				mediaItem.releaseLock()
		
		def update(self, amountRead, now=None):
			RateEstimator.update(self, amountRead, now)
			
			# fixme: urlgrabber doesn't seem to like locking?!!
			mediaItem = self.__task.getMediaItem()
			mediaItem.acquireLock()
			try:
				mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, Media.Item.DLSTATUS__DOWNLOADING)
				mediaItem.setStatisticNoLock(Media.Item.TOTAL_BYTES_DOWNLOADED, amountRead)
				
				mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_BPS_AVERAGE, self.average_rate())
				mediaItem.setStatisticNoLock(Media.Item.TIME_ELAPSED, self.elapsed_time())
				mediaItem.setStatisticNoLock(Media.Item.TIME_REMAINING, self.remaining_time())
				
				frac = self.fraction_read()
				if frac == None:
					frac = 0.0
				
				percent = 100.0 * frac
				mediaItem.setStatisticNoLock(Media.Item.PERCENT_COMPLETE, percent)
			finally:
				mediaItem.releaseLock()

	def __init__(self, mediaItem):
		MediaItemDownloadTask.__init__(self, mediaItem)
		
		self.__grabber = urlgrabber.grabber.URLGrabber()
		self.__updater = MediaItemURIDownloadTask.Updater(self)
		
		mediaItem.acquireLock()
		try:
#			mediaItem.setStatisticNoLock(Media.Item.TOTAL_BYTES_DOWNLOADED, 0)
#			mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_BPS_AVERAGE, 0)
#			mediaItem.setStatisticNoLock(Media.Item.TIME_ELAPSED, 0)
#			mediaItem.setStatisticNoLock(Media.Item.TIME_REMAINING, 0)
#			mediaItem.setStatisticNoLock(Media.Item.PERCENT_COMPLETE, 0.0)
			
			localPath = utils.destPathFromURI(mediaItem.getStatisticNoLock(Media.Item.URI))
			utils.ensureDirExistsForFile(localPath)
			mediaItem.setStatisticNoLock(Media.Item.LOCAL_PATH, localPath)
			mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_METHOD, Media.Item.DLMETHOD__DIRECT)
		finally:
			mediaItem.releaseLock()

	def __interrupted(self, obj):
		# fixme: what is this method for?  urlgrabber docs are pretty vague
		pass
	
	def __call__(self, **kwArgs):
		# fixme: doesn't handle retries within a single program session
		MediaItemDownloadTask.__call__(self, **kwArgs)
		
		mediaItem = self.getMediaItem()
		assert mediaItem is not None
		
		mediaItem.acquireLock()
		try:
			miURI = mediaItem.getStatisticNoLock(Media.Item.URI)
			miLocalPath = mediaItem.getStatisticNoLock(Media.Item.LOCAL_PATH)
			
			# fixme: TaskPool.AbortTask doesn't work; remove it and try something else
			try:
				self.__grabber.urlgrab(\
					miURI, \
					filename=miLocalPath, \
					progress_obj=self.__updater, \
					reget=config.regetMode, \
					interrupt_callback=self.__interrupted, \
					user_agent=config.userAgent \
					#bandwidth = config.maxBytesPerSecPerDownload, \
					#throttle = config.maxBytesPerSecThrottleFactor \
				)
				
				# get the downloaded file's mimetype, and rename it accordingly
				mimetype = utils.getMimetype(miLocalPath)
				mediaItem.setStatisticNoLock(Media.Item.MIMETYPE, mimetype)
				
				newPath = utils.renameForMimetype(miLocalPath, mimetype)
				mediaItem.setStatisticNoLock(Media.Item.LOCAL_PATH, newPath)
				mediaItem.releaseLock()
			except urlgrabber.grabber.URLGrabError, e:
				self._notifyError(u"Couldn't download '%s' - %s" % (miURI, e))
				if os.path.exists(miLocalPath):
					os.unlink(miLocalPath)
				self.abort()
		finally:
			mediaItem.releaseLock()

class MediaItemBTDownloadTask(MediaItemDownloadTask):
	def __init__(self, mediaItem):
		MediaItemDownloadTask.__init__(self, mediaItem)
		
		self.__btDoneFlag = threading.Event()
		
		mediaItem.acquireLock()
		try:
			miURI = mediaItem.getStatisticNoLock(Media.Item.URI)
			
			miLocalPath = utils.destPathFromURI(mediaItem.getStatisticNoLock(Media.Item.URI))
			try:
				os.makedirs(miLocalPath)
			except OSError:
				pass
			
			mediaItem.setStatisticNoLock(Media.Item.LOCAL_PATH, miLocalPath)
			mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_METHOD, Media.Item.DLMETHOD__BITTORRENT)
			
			self.__btArgs = [
				u'--minport',					config.btMinPort,
				u'--minport',					config.btMinPort,
				u'--maxport',					config.btMaxPort,
				u'--saveas',					miLocalPath,
				u'--bind',						config.btBindIP,
				u'--url',							miURI,
				
				# only update every 1 seconds (default is .5), since that's how
				# often we refresh the display anyhow.
				u'--display_interval',	1,
				
				u'--max_upload_rate',	config.btMaxUploadKBytesPerSec,
			]
		finally:
			mediaItem.releaseLock()

	def _convertBTSize(self, size):
		"""Converts Bittorent-supplied current download units (GB, as a float) back to bytes."""
		res = int(float(size) * 1024.0 * 1024.0)
		return res
	
	def _btChooseFile(self, default, size, saveas_unused, dir_unused):
		mediaItem = self.getMediaItem()
		mediaItem.acquireLock()
		try:
			mediaItem.setStatistic(Media.Item.TOTAL_BYTES, size)
			miLocalPath = mediaItem.getStatisticNoLock(Media.Item.LOCAL_PATH)
			
			filePath = os.path.join(miLocalPath, unicode(default))
			
			return filePath
		finally:
			mediaItem.releaseLock()

	def _btDownloadComplete(self):
		# hmm... what is this callback for??  Doesn't seem to get called when
		# the download completes, as might be expected.  Bittorrent API docs
		# might be nice :)
		pass

	def _btUpdateProgress(self, dict):
		mediaItem = self.getMediaItem()
		mediaItem.acquireLock()
		try:
			if dict.has_key('activity'):
				mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, dict['activity'])
			
			if dict.has_key('upTotal'): #check to see if we should stop
				mediaItem.setStatisticNoLock(Media.Item.TOTAL_BYTES_UPLOADED, self._convertBTSize(dict['upTotal']))
			
			if dict.has_key('downTotal'):
				mediaItem.setStatisticNoLock(Media.Item.TOTAL_BYTES_DOWNLOADED, self._convertBTSize(dict['downTotal']))
			
			if dict.has_key('upRate'):
				mediaItem.setStatisticNoLock(Media.Item.UPLOAD_BPS_AVERAGE, dict['upRate'])
			
			if dict.has_key('downRate'):
				mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_BPS_AVERAGE, float(dict['downRate']))
			
			if dict.has_key('fractionDone'):
				mediaItem.setStatisticNoLock(Media.Item.PERCENT_COMPLETE, 100.0 * float(dict['fractionDone']))
				
			if dict.has_key('timeEst'):
				mediaItem.setStatisticNoLock(Media.Item.TIME_ESTIMATED, utils.btFormatETA(dict['timeEst']))
			
			if self._btDownloadComplete():
					try:
						miBytesDownloaded = mediaItem.getStatisticNoLock(Media.Item.TOTAL_BYTES)
					except KeyError:
						miBytesDownloaded = 0
					
					if dict['upTotal'] >= miBytesDownloaded: #if ratio is one, quit
						self.__btDoneFlag.set()
					if time.time() - 60*60 >= self.start_time: #if it's been an hour, quit
						self.__btDoneFlag.set()
		finally:
			mediaItem.releaseLock()

	def _btFinished(self):
		mediaItem = self.getMediaItem()
		mediaItem.acquireLock()
		try:
			mediaItem.setStatisticNoLock(Media.Item.PERCENT_COMPLETE, 100.0)
			mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, Media.Item.DLSTATUS__COMPLETE)
			
			downloadDir = mediaItem.getStatisticNoLock(Media.Item.LOCAL_PATH)
			mediaFiles = utils.allMediaInDir(downloadDir)
			mediaItem.setStatisticNoLock(Media.Item.MEDIA_FILES, mediaFiles)
		finally:
			mediaItem.releaseLock()

	def _btError(self, errormsg):
		#for some reason this isn't a fatal error
		if errormsg == 'rejected by tracker - This tracker requires new tracker protocol. Please use our Easy Downloader or check blogtorrent.com for updates.':
			print "getting (bogus?) blogtorrent 'rejected by tracker' error, ignoring"
		else:
			self._notifyError(errormsg)
			self.__btDoneFlag.set()

	def _btNewpath(self, path):
		print "btNewPath:", path

	def __call__(self, **kwArgs_unused):
		# do bittorrent download here
		mediaItem = self.getMediaItem()
		mediaItem.setStatisticNoLock(Media.Item.DOWNLOAD_STATUS, 'Downloading via Bittorrent')
		
		try:
			BTDownload.download(
				self.__btArgs,
				self._btChooseFile,
				self._btUpdateProgress,
				self._btFinished,
				self._btError,
				self.__btDoneFlag,
				80,
				self._btNewpath)
		except timeoutsocket.Timeout, e:
			print "BT Exception raised:", e.__class__.__name__, e
			dumptrace()
			self._notifyError(e)
			
			self.__btDoneFlag.set()
			self.abort()
		except Exception, e:
			print "BT Exception raised:", e.__class__.__name__, e
			dumptrace()
			self._notifyError(e)
			
			self.__btDoneFlag.set()
			self.abort()

def dlTaskForMediaItem(mediaItem):
	# todo: check the mediaitem's mimetype,
	# and return MediaItemURIDownloadTask or
	# MediaItemBTDownloadTask, depending on which it is.
	miMimetype = mediaItem.getStatistic(Media.Item.MIMETYPE)
	if miMimetype.startswith('application/x-bittorrent'):
		return MediaItemBTDownloadTask(mediaItem)
	else:
		return MediaItemURIDownloadTask(mediaItem)
