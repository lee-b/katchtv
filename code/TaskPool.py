#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email lee.b@digitalunleashed.com) for a copy.
#
import sys
import os
import traceback

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path.append(os.path.join(appRoot, 'code'))
import Media
import utils
import config

import threading

sys.path.append(os.path.join(appRoot, 'code/thirdparty'))
import ThreadPool

class AbortTask:
	pass

class Task:
	class Callback:
		def __init__(self, obj):
			self.__obj = obj
		
		def __call__(self, data):
			self.__obj.finished()

	def __init__(self):
		self.__aborted = False
	
	def abort(self):
		self.__aborted = True
	
	def _wasAborted(self):
		return self.__aborted

	def finished(self):
		self.__pool.finishTask(self)
	
	def __call__(self, **kwArgs):
		pass

	def queueInPool(self, taskPool):
		cb = Task.Callback(self)
		self.__pool = taskPool
		self.__pool.queueTask(self, cb)

class Pool(ThreadPool.ThreadPool):
	def __init__(self, numThreads):
		ThreadPool.ThreadPool.__init__(self, numThreads)
		self.__tasksCompleted = []

	def tasksInProgress(self):
		return self.getTasks()

	def tasksCompleted(self):
		return self.__tasksCompleted

	def finishTask(self, task):
		self.__tasksCompleted.append(task)
	
	def stop(self):
		self.joinAll(waitForTasks=False, waitForThreads=False)
