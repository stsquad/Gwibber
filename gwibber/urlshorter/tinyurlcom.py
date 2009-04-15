
"""

TinyURL.com interface for Gwibber
macno (Michele Azzolari) - 02/13/2008

"""

import urllib2

PROTOCOL_INFO = {

  "name": "tinyurl.com",
  "version": 0.1,
  "fqdn" : "http://tinyurl.com",
  
}

class URLShorter:

  def short(self, text):
    short = urllib2.urlopen("http://tinyurl.com/api-create.php?url=%s" % urllib2.quote(text)).read()
    return short

