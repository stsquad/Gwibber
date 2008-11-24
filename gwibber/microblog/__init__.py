
import operator, traceback, can
import twitter, jaiku, identica, laconica, pownce
import digg, flickr, brightkite, rss, pingfm, facebook

PROTOCOLS = {
  "jaiku": jaiku,
  "digg": digg,
  "twitter": twitter,
  "facebook": facebook,
  "flickr": flickr,
  "pownce": pownce,
  "identica": identica,
  "laconica": laconica,
  "rss": rss,
  "pingfm": pingfm,
  #"brightkite": brightkite,
}

def supports(a, feature):
  return feature in PROTOCOLS[a["protocol"]].PROTOCOL_INFO["features"]

class Client:
  def __init__(self, accounts):
    self.accounts = accounts

  def handle_error(self, acct, err, msg = None):
    pass

  def post_process_message(self, message):
    return message

  def get_data(self, test, method, name, filter=PROTOCOLS.keys(), return_value=True, first_only=False):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if test(acct):
            if return_value:
              for message in method(client):
                yield self.post_process_message(message)
            else:
              yield method(client)
              if first_only: break
        except: self.handle_error(acct, traceback.format_exc(), name)

  def perform_operation(self, test, method, name, filter=PROTOCOLS.keys()):
    data = list(self.get_data(test, method, name, filter))
    data.sort(key=operator.attrgetter("time"), reverse=True)
    return data

  def send(self, message, filter=PROTOCOLS.keys()):
    return list(self.get_data(
      lambda a: a["send_enabled"] and supports(a, can.SEND),
      lambda c: c.send(message), "send message", filter, False))

  def reply(self, message, filter=PROTOCOLS.keys()):
    return list(self.get_data(
      lambda a: supports(a, can.SEND),
      lambda c: c.send(message), "send message", filter, False, True))

  def thread(self, query, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and supports(a, can.THREAD) and \
        a.id == query.account.id,
      lambda c: c.get_thread(query), "retrieve thread", filter)
  
  def responses(self, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and supports(a, can.RESPONSES),
      lambda c: c.responses(), "retrieve responses", filter)

  def receive(self, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and supports(a, can.RECEIVE),
      lambda c: c.receive(), "retrieve messages", filter)

  def friend_positions(self, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and supports(a, can.GEO_FRIEND_POSITIONS),
      lambda c: c.friend_positions(), "retrieve positions", filter)

  def search(self, query, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["search_enabled"] and supports(a, can.SEARCH),
      lambda c: c.search(query), "perform search query", filter)

  def tag(self, query, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and supports(a, can.TAG),
      lambda c: c.tag(query.lower().replace("#", "")), "perform tag query", filter)


