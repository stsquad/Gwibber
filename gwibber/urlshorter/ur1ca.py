
"""

ur1.ca interface for Gwibber
macno (Michele Azzolari) - 02/13/2008

"""

from sgmllib import SGMLParser
import urllib, urllib2

PROTOCOL_INFO = {

  "name": "ur1.ca",
  "version": 0.1,
  "fqdn" : "http://ur1.ca",
  
}

class URLShorter:

  def short(self, text):
    url="http://ur1.ca"
    values = {'submit' : 'Make it an ur1!',
              'longurl' : text }
    data = urllib.urlencode(values)
    page = urllib2.urlopen(url,data).read()
    controlstring="<p class=\"success\">Your ur1 is: <a href=\"http://ur1.ca/"
    controlstringend="</a></p>"
    iposstart = page.index(controlstring)
    iposend = page.index(controlstringend,iposstart)
    short = page[iposstart:iposend]
    iposstart = short.rindex(">")
    short = short[iposstart+1:]

    return short


