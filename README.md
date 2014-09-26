KatchTV
=======

Welcome to KatchTV.  Please refer to the HTML manual in the Docs directory,
or from inside the program, for usage instructions.


Screenshots
-----------

![Screenshot of KatchTV showing its video playback](https://raw.githubusercontent.com/lee-b/katchtv/master/Docs/screenshots/geekbrief.png?raw=true "Video playback in KaetchTV")

![Screenshot of KatchTV showing its multi-threaded, multi-protocol downloading](https://raw.githubusercontent.com/lee-b/katchtv/master/Docs/screenshots/downloads.png?raw=true "Multi-threaded, multi-protocol downloading in KatchTV")

![Screenshot of KatchTV showing directory browsing](https://raw.githubusercontent.com/lee-b/katchtv/master/Docs/screenshots/zencast.png?raw=true "Browsing a directory of webcasts in KatchTV")


Requirements
------------

This is a PyKDE app, so you'll need the following installed:

 * python (2.4+ advised)
 * PyKDE and PyQt.

You'll also need a KDE movie player, which is capable of embedding as a KPart
into KHTML-based browsers.  That generally means on of:

 * Kaffeine
 * KMPlayer
 * Mozplugger

Kaffeine seems to work best for me, although I haven't tried Mozplugger at all.

Note that you can individually choose which embedded player will be used,
from the file associations section of Konqueror's preferences.  Just go the
embedded tab for a media file type, and change the preferred KPart order.

IMPORTANT: when I say that kaffeine works best for me, I mean that KMPlayer
seems to be fond of crashing KatchTV.  That's not KatchTV's fault, as far as
I can tell.  Use kaffeine instead, as instructed above.


Consult your GNU/Linux/*BSD/HURD whatever distro's documentation for
details on how to get and install those packages.  On most distros,
it's pretty straightforward, and shouldn't be a problem.



Installation
------------

To actually install this, the easiest way is just to move the untarred directory
to some location like /usr/local/KatchTV, and then make a symlink from that
directory's KatchTV executable into /usr/local/bin or your personal ~/bin
directory.

So basically, from scratch, you can do:

   cd /usr/local
   tar xvjf /path/to/the_downloaded/KatchTVtarball.tar.bz2
   ln -s /usr/local/KatchTV/KatchTV /usr/local/bin/KatchTV

Then, just run KatchTV from the command line, or make a KDE icon for it :)

Let me know if you run into any problems -- just email:

 leebraid@gmail.com

Comments, suggestions, and improvements are also welcome, of course!


License
-------

This software is licensed under the GNU General Public License, version 2.
Consult the included LICENSE.txt file for specific details.

