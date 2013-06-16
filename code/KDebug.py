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
import config

def dumptrace():
	trace = ""
	exception = ""
	if sys.__dict__.has_key('exc_value'):
		exc_list = traceback.format_exception_only (sys.exc_type, sys.exc_value)
	else:
		exc_list = traceback.format_exception_only (sys.exc_type, '')
	for entry in exc_list:
		exception += entry
	tb_list = traceback.format_tb(sys.exc_info()[2])
	for entry in tb_list:
		trace += entry
	print "Exception and trace: %s\n%s" % (exception, trace)

def traced(func):
	_name = func.func_name
	_func = func
	__doc__ = func.__doc__

	def wrap(*args, **kwargs):
		print "Calling", _name, args, kwargs
		result = _func(*args, **kwargs)
		print "Called", _name, args, kwargs, "returned", repr(result)
		return result
	
	return wrap

if __name__ == "__main__":
	@traced
	def testfunc():
		pass

	class testclass:
		@traced
		def __init__(self, x):
			self.__x = x
		
		@traced
		def testmethod(self, x, y):
			pass

	testfunc()
	
	tc = testclass(1)
	tc.testmethod(1, '2')
