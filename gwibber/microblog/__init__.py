
import operator, traceback, can
import twitter, jaiku, facebook, digg, flickr, pownce, identica

PROTOCOLS = {
  "jaiku": jaiku,
  "digg": digg,
  "twitter": twitter,
  "facebook": facebook,
  "flickr": flickr,
  "pownce": pownce,
  "identica": identica,
}

class Client:
  def __init__(self, accounts):
    self.accounts = accounts

  def handle_error(self, acct, err, msg = None):
    pass

  def post_process_message(self, message):
    return message

  def get_data(self, test, method, name, filter=PROTOCOLS.keys()):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if test(acct):
            for message in method(client):
              yield self.post_process_message(message)
        except: self.handle_error(acct, traceback.format_exc(), name)

  def perform_operation(self, test, method, name, filter=PROTOCOLS.keys()):
    data = list(self.get_data(test, method, name, filter))
    data.sort(key=operator.attrgetter("time"), reverse=True)
    return data

  def send(self, message, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["send_enabled"] and a.supports(can.SEND),
      lambda c: c.send(message), "send message", filter)

  def thread(self, query):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and a.supports(can.THREAD) and \
        a.id == query.account.id,
      lambda c: c.responses(query), "retrieve thread", filter)
  
  def responses(self, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and a.supports(can.RESPONSES),
      lambda c: c.responses(), "retrieve responses", filter)

  def receive(self, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and a.supports(can.RECEIVE),
      lambda c: c.receive(), "retrieve messages", filter)

  def search(self, query, filter=PROTOCOLS.keys()):
    return self.perform_operation(
      lambda a: a["receive_enabled"] and a.supports(can.SEARCH),
      lambda c: c.search(query), "perform search query", filter)

