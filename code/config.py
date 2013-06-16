#
# Copyright (c) 2005-2006 by Lee Braiden.  Released under the GNU General
# Public License, version 2 or later.  Please see the included LICENSE.txt
# file for details.  Legally, that file should have been included with this
# one.  If not, please contact Lee Braiden (email lee.b@digitalunleashed.com)
# for a copy.
#
"""Defines some basic variables, such as pathnames, and includes functions for loading and saving configuration variables."""

import os
import sys
import shelve
import datetime
import threading

appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))
sys.path.append(os.path.join(appRoot, u'code'))

import revno

debug = True

appName = u"KatchTV"
appCopyright = u"Copyright &copy; 2006 Lee Braiden. Released under the GNU General Public License version 2.0."
appVersion = u"0." + unicode(revno.BzrRevisionNumber)

appBlurb = u""
appHomepage = u"http://www.digitalunleashed.com/giving.php"
appBugEmailAddr = u"bugs+katchtv@digitalunleashed.com"

appFullVersion = appName + u" v" + unicode(appVersion)
userAgent = appFullVersion

appCopyright = u"""
This software is licensed to you under the terms
of the GNU General Public License, version 2.
Please see the included LICENSE.txt file for
details, or refer to the official GNU site: 
http://www.gnu.org"""

# not a config var; just something to make this all work; don't mess with it :)
appRoot = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])))

# throttling for normal (http, ftp, etc; non-bt) downloads
maxBytesPerSecPerDownload = None
maxBytesPerSecThrottleFactor = 1.0

configRoot = os.path.expandvars(u'$HOME/.KatchTV')
mediaStoreRoot = os.path.expandvars(u'$HOME/.KatchTV/mediastore')

downloadsNewFile = os.path.join(configRoot, u"mediaitems.shelf")

numDownloadThreads = 4
downloadRetrySecs = 1

# bittorrent ports to listen on.
# NOTE: changed from defaults, since the
# defaults are likely to be blocked
btMinPort = 9571
btMaxPort = 9579

# Interface to bind to (listen on) for Bittorrent
btBindIP = ''

btMaxUploadKBytesPerSec = 12

# regetmode for http, ftp, etc. (non-bt) downloads
# probably shouldn't change this :)
regetMode = 'simple'

# maximum number of seconds to wait for a
# feed to download and parse
maxFeedParseSeconds = 14

# 12 hours should be more than enough,
# since most podcasts are daily or weekly
defaultChannelUpdateMins = 60 * 12

updateChannelsTimerMillisecs = 500
updateDownloadsTimerMillisecs = 500

numFeedThreads = 2						# be gentle with this thread count, since feeds are small anyhow.
feedUpdateCheckSeconds = 1		# wait time for each check of feed update taskpool (seconds; fractions OK)

helpContents = "file://localhost" + os.path.join(appRoot, 'Docs/Manual/index.html')
progressBarImageURI = 'file://localhost' + os.path.join(appRoot, 'webstyle/progressbar.png')

nameColumnWidth = 200
numNewColumnWidth = 40
updateMinsColumnWidth = 60

maxFeedEntries = 120

dawnOfTime = datetime.datetime(year=datetime.MINYEAR, month=1, day=1)

defaultFeedSummary = u"""(no summary supplied)"""
defaultFeedLogoURI = u"file://" + os.path.join(appRoot, "Docs/Manual/images/Logo.png")
defaultEpisodeBody = u"""<p>(no description supplied)</p>"""


defaultBookmarks = {
	u'http://dev.digitalunleashed.com/katchtv/KatchTV_Updates_rssfeed.xml': {
		u'name':					u"KatchTV Updates",
		u'updateMins':		60 * 24,	# daily
	},
	u'http://radio.kde.org/konqcast.rss': {
		u'name':					u"KDE Radio (Ogg)",
		u'updateMins':		60 * 24,	# daily
	},
	u'http://www.lugradio.org/episodes.ogg.rss': {
		u'name':					u'LUG Radio',
		u'updateMins':		60 * 24	# daily
	},
	u'http://revision3.com/diggnation/feed/theora-large': {
		u'name':					u'Diggnation (HQ, Theora)',
		u'updateMins':		60 * 24	# daily
	},
	u'http://www.podshow.com/feeds/hd.xml': {
		u'name':					u'Geek Brief TV (HQ)',
		u'updateMins':		60 * 24	# daily
	},
	u'http://feeds.feedburner.com/hyman/': {
		u'name':					u'Izzy Video: Editing Tutorials',
		u'updateMins':		60 * 24	# daily
	},
	u'http://feeds.feedburner.com/tikibartv/': {
		u'name':					u'Tiki Bar TV',
		u'updateMins':		60 * 24	# daily
	},
	u'http://radio.linuxquestions.org/syndicate/lqpodcast.php': {
		u'name':					u'LQ Podcast',
		u'updateMins':		60 * 24	# daily
	},
	u'http://radio.linuxquestions.org/syndicate/lqradio.php': {
		u'name':					u'LQ Radio',
		u'updateMins':		60 * 24	# daily
	},
}

DIRECTORY_NAME = 0
DIRECTORY_CATEGORY = 1

DIRCAT_RECOMMENDED = 'A. Recommended'
DIRCAT_CONFUSING = 'B. Confusing'
DIRCAT_POOR = 'C. Poor quality'

DIRCAT_NONCOMPLIANT = 'a) Non-compliant'
DIRCAT_UNTESTED = 'b) Untested'
DIRCAT_COMMERCIALISED = 'c) Over-Commercialised and non-compliant'
DIRCAT_DYSFUNCTIONAL = 'd) Non-functional'

dirCats = [ DIRCAT_RECOMMENDED, DIRCAT_CONFUSING, DIRCAT_POOR, DIRCAT_NONCOMPLIANT, DIRCAT_UNTESTED, DIRCAT_COMMERCIALISED, DIRCAT_DYSFUNCTIONAL ]
notRecommendedDirCats = [ DIRCAT_NONCOMPLIANT, DIRCAT_UNTESTED, DIRCAT_COMMERCIALISED, DIRCAT_DYSFUNCTIONAL ]

defaultDirectories = {
	u'https://channelguide.participatoryculture.org/':	(u'Democracy TV', DIRCAT_RECOMMENDED),
	u'http://zencast.com/channels/videochannels.asp':	(u'ZENCast', DIRCAT_RECOMMENDED),
	u'http://www.vodstock.com':							(u'VOD Stock', DIRCAT_RECOMMENDED),
	u'http://www.podcast.net/':							(u'PODCast.net', DIRCAT_RECOMMENDED),
	u'http://www.digitalpodcast.com':					(u'Digital Podcast', DIRCAT_RECOMMENDED),

	# special interest stuff; should have another category for this, but haven't yet
	u'http://www.religious-podcasts.net/':				(u'Religious Podcasts', DIRCAT_RECOMMENDED),

	# confusing (sites that provide feeds, but use their own terms
	# that might confuse KatchTV users into clicking the wrong
	# thing)
	u'http://fireant.tv/directory?':					(u'Fireant', DIRCAT_CONFUSING),
	u'http://azureus.aelitis.com/wiki/index.php/Legal_torrent_sites': (u'Azureus Legal Torrents (avoid non-media torrents)', DIRCAT_CONFUSING),
	u'http://www.podcastingnews.com/forum/links.php':	(u'Podcasting News Directory', DIRCAT_CONFUSING),

#	# adult content
#	u'http://www.forbiddenpodcasts.tv/':				(u'Forbidden Podcasts (adults only)', DIRCAT_RECOMMENDED),
	
	# poor-quality sites
	u'http://vlogdir.com':								(u'VLogDir', DIRCAT_POOR),
	
	# non-compliant video sites (ie, sites that don't use feeds)
	u'http://video.google.com/':						(u'Google Video', DIRCAT_NONCOMPLIANT),
	u'http://www.youtube.com/':							(u'YouTube', DIRCAT_NONCOMPLIANT),

	# mostly untested
	u'http://vloglist.com/':							(u'VLogList', DIRCAT_UNTESTED),
	u'http://www.vlogmap.org/':							(u'VLogMap', DIRCAT_UNTESTED),
	u'http://mefeedia.com/feeds/':						(u'Mefeedia', DIRCAT_UNTESTED),
	u'http://www.realpeoplenetwork.com/':				(u'RealPeopleNetwork', DIRCAT_UNTESTED),
	u'http://www.vodcasts.tv/':							(u'VODCasts.tv', DIRCAT_UNTESTED),
	
	# totally untested
	u'http://www.blinkx.tv/':							(u'BlinkX TV', DIRCAT_UNTESTED),
	u'http://www.newgrounds.net/':						(u'NewGrounds', DIRCAT_UNTESTED),
	u'http://www.publicdomaintorrents.net/':			(u'Public Domain Torrents', DIRCAT_UNTESTED),
	u'http://www.revver.com/':							(u'Revver', DIRCAT_UNTESTED),
	u'http://www.submedia.tv/':							(u'subMedia', DIRCAT_UNTESTED),
	u'http://www.undergroundfilm.org':					(u'Underground Film', DIRCAT_UNTESTED),
	u'http://www.machinima.com/':						(u'Machinima', DIRCAT_UNTESTED),
	u'http://www.castwiki.com/index.php/Directories':	(u'CastWiki: Other Directories', DIRCAT_UNTESTED),
	
	# over-commercial to the point of being non-compliant or not fitting in with the app, or (imho)
	# misusing copyright to restrict the tech instead of opening it up.
	u'http://www.mobi.tv/':								(u'Mobi TV', DIRCAT_COMMERCIALISED),
	
	# (currently) dysfunctional (for our purposes, at least)
	u'http://kedora.org':								(u'Kedora', DIRCAT_DYSFUNCTIONAL), # used to work, but now holding page
	u'http://video.search.yahoo.com/':					(u'Yahoo Video', DIRCAT_DYSFUNCTIONAL), # scripted player
	u'http://www.podcast.tv/index2.php?tnd=29':			(u'PODCast TV', DIRCAT_DYSFUNCTIONAL), # over-scripted
	u'http://www.podcastalley.com':						(u'PODCast Alley', DIRCAT_DYSFUNCTIONAL), # over-scripted
	u'http://www.podshow.com/':							(u'PodShow', DIRCAT_DYSFUNCTIONAL), # over-scripted, just like its partner in crime, podcast alley
	u'http://www.ifilm.com/':							(u'iFilm', DIRCAT_DYSFUNCTIONAL), # over-scripted (commercialised and non-compliant too)
}

# FIXME: this should use regex's, for more reliability/flexibility
knownHTMLMimetypes = [
	u'text/html',
	u'text/plain',
	u'application/xhtml+xml'
]

knownPlayableExtens = [
	u'.mpeg',
	u'.mpeg2',
	u'.mpeg4',
	u'.mpg',
	u'.mpg2',
	u'.mpg4',
	u'.mp2',
	u'.mp3',
	u'.mp4',
	u'.divx',
	u'.vidx',
	u'.mov',
	u'.avi',
	u'.wmv',
	u'.asf',
	u'.flv',
	u'.mkv',
	u'.ogm',
	u'.ogg',
	u'.asx',
	u'.dv',
	u'.fli',
	u'.flx',
	u'.dxr',
	u'.dvr-ms',
	u'.fla',
	u'.ifo',
	u'.ivf',
	u'.ivs',
	u'.m1v',
	u'.m4e',
	u'.m4u',
	u'.moov',
	u'.movie',
	u'.mpe',
	u'.mpv2',
	u'.omf',
	u'.prx',
	u'.qt',
	u'.qtch',
	u'.rm',
	u'.rp',
	u'.rts',
	u'.scm',
	u'.smil',
	u'.smv',
	u'.svi',
	u'.swf',
	u'.vfw',
	u'.vid',
	u'.viv',
	u'.vivo',
	u'.vob',
	u'.wm',
	u'.wmv',
	u'.wmx',
	u'.wvx',
	u'.png',
]

# FIXME: this should use regex's, for more reliability/flexibility
feedGiveaways = [
	# fairly reliable extensions
	'.rss',
	'/rss.php',
	'.rdf',
	'.atom',
	
	# some possible naming conventions (guessed, rather than seen)
	'.rss0.99',
	'.rss2.0',
	'.rss2',
	
	# handle some fairly reliable GET arguments which specify RSS
	'feed=', # I forget where this was needed, but it's probably common
	'mode=rss',					# tvrss.net
	
	# site-specific hacks
	'http://feeds.feedburner.com/',
	'videobomb.com/rss',
	'.libsyn.com/rss',
	'fleshbot.com/index.xml',
	'G4_TV',
	'/rss2.php',					# Channel 102
	'http://www.reinvented.net/rss/formosa.xml',	# Live from the formosa teahouse
	'episodes/rss20',				# Kedora.org
	'/pfbrss',					# "Pillow Fight Bloodbath"
	'/vodcast.xml',					# NASA's "Destination Tomorrow" (and others?)
	'diggnation/feed',				# Diggnation's feeds
]

# FIXME: this should use regex's, for more reliability/flexibility
feedMimetypes = [
	'application/atom+xml',
	'application/rdf+xml',
	'application/rss+xml',
	'application/x-netcdf',
	'application/xml',
	'text/xml'
]

# This is just a list of characters where it's acceptable to insert
# a linebreak in extreme cases, such as a really long filename that
# would otherwise make the browser-based UI scroll horizontally.

# FIXME: regex's might be useful here in the short-term.  Long-term,
# we should be checking based on unicode's/locale's knowledge of the
# current (actually webpage's) language.
textToForceBreaksOn = [
	u'/',
	u'-',
	u':',
	u'.',
	u',',
	u'A',
	u'B',
	u'C',
	u'D',
	u'E',
	u'F',
	u'G',
	u'H',
	u'I',
	u'J',
	u'K',
	u'L',
	u'M',
	u'N',
	u'O',
	u'P',
	u'Q',
	u'R',
	u'S',
	u'T',
	u'U',
	u'V',
	u'W',
	u'X',
	u'Y',
	u'Z',
]

defaultChannelTitle = "{retrieving title}"

def removeOldFiles(*files):
	"""Simply deletes a list of files, if present.  Useful for removing old configuration files,
	after saving with new names."""
	for f in files:
		if os.path.exists(f) and os.path.is_file(f):
			os.unlink(f)
