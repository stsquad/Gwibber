
import operator, traceback
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

  def get_message_data(self, filter=PROTOCOLS.keys()):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if client.receive_enabled():
            for message in client.get_messages():
              yield self.post_process_message(message)
        except: self.handle_error(acct, traceback.format_exc(),
          "Failed to retrieve messages")

  def get_reply_data(self, filter=PROTOCOLS.keys()):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if client.receive_enabled() and hasattr(client, "can_get_replies"):
            for message in client.get_replies():
              yield self.post_process_message(message)
        except: self.handle_error(acct, traceback.format_exc(),
          "Failed to retrieve messages")

  def get_search_data(self, query, filter=PROTOCOLS.keys()):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if client.receive_enabled() and hasattr(client, "can_search"):
            for message in client.get_search_results(query):
              yield self.post_process_message(message)
        except: self.handle_error(acct, traceback.format_exc(),
          "Failed to retrieve messages")

  def get_message_reply_data(self, query):
    for acct in self.accounts:
      print acct, query.account
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct.id == query.account.id:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if client.receive_enabled() and hasattr(client, "can_reply"):
            print "starting..."
            for message in client.get_replies(query):
              yield self.post_process_message(message)
        except: self.handle_error(acct, traceback.format_exc(),
          "Failed to retrieve messages")
  
  def get_reply_thread(self, query):
    data = list(self.get_message_reply_data(query))
    data.sort(key=operator.attrgetter("time"), reverse=True)

    return data
  
  def get_replies(self, filter=PROTOCOLS.keys()):
    data = list(self.get_reply_data(filter))
    data.sort(key=operator.attrgetter("time"), reverse=True)

    return data

  def get_messages(self, filter=PROTOCOLS.keys()):
    data = list(self.get_message_data(filter))
    data.sort(key=operator.attrgetter("time"), reverse=True)

    return data

  def get_search_results(self, query, filter=PROTOCOLS.keys()):
    data = list(self.get_search_data(query, filter))
    data.sort(key=operator.attrgetter("time"), reverse=True)

    return data

  def transmit_status(self, message, filter=PROTOCOLS.keys()):
    for acct in self.accounts:
      if acct["protocol"] in PROTOCOLS.keys() and \
         acct["protocol"] in filter:
        try:
          client = PROTOCOLS[acct["protocol"]].Client(acct)
          if client.can_send() and client.send_enabled():
            client.transmit_status(message)
        except: self.handle_error(acct, traceback.format_exc(),
          "Failed to send messages")
