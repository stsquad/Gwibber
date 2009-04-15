
"""

snipurl.com interface for Gwibber
macno (Michele Azzolari) - 02/13/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "snipurl.com",
  "version": 0.1,
  "fqdn" : "http://snipr.com",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://snipr.com/site/snip?r=simple&link=%s" % urllib2.quote(text)).read()
    return short

