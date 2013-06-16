#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General Public
# License, version 2 or later.  Please see the included LICENSE.txt file for details.
# Legally, that file should have been included with this one.  If not, please contact
# Lee Braiden (email leebraid@gmail.com) for a copy.
#

import sys
import os
import shelve

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

sys.path = [ os.path.join(appRoot, 'code') ] + sys.path
import config
import utils

class DataStore:
	_masterLock = utils.NamedLock("DataStore master lock")
	_dataFileLocks = { }

	def __makeConfigDirs(self):
		try:
			os.mkdir(config.configRoot)
			os.mkdir(config.mediaStoreRoot)
		except:
			pass
	
	def __init__(self, dataFile):
		self.__makeConfigDirs()
		self._dataFile = dataFile
		if not self.__class__._dataFileLocks.has_key(os.path.realpath(dataFile)):
			self.__class__._dataFileLocks[dataFile] = utils.NamedLock("Lock for Data file '%s'" % dataFile)

	@utils.synchronized(_masterLock)
	def acquireLock(self):
		self.__class__._dataFileLocks[self._dataFile].acquire()

	@utils.synchronized(_masterLock)
	def releaseLock(self):
		self.__class__._dataFileLocks[self._dataFile].release()
	
	def set(self, varName, val):
		"""Saves a configuration variable into a file."""
		shv = shelve.open(self._dataFile, protocol=2)
		shv[str(varName)] = val
		shv.close()

	def get(self, varName):
		"""Loads a configuration variable from the filename.  If
		oldFileName and/or oldVarName are supplied, then those files
		and/or variables will be checked, should loading the by the
		other file/name fail.  This allows for easy upgrades from
		previous versions.  If no data can be loaded at all, then the
		default value is returned."""
		shv = shelve.open(self._dataFile)
		val = shv[str(varName)]
		shv.close()
		return val

	def getWithDefault(self, varName, defaultVal):
		try:
			return self.get(varName)
		except (KeyError, IOError):
			return defaultVal
