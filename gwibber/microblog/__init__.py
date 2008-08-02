#!/usr/bin/env python

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

  def get_messages(self, filter=PROTOCOLS.keys()):
    data = list(self.get_message_data(filter))
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
