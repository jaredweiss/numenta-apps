#!/usr/bin/env python

import json
from logging import getLogger

from nta.utils import amqp
from nta.utils.tools.set_rabbitmq_login_impl import setRabbitmqLoginScriptImpl



class Master(object):

  def __init__(self):
    self._log = getLogger(__name__)
    self._resultsExchange = "resExchange"


  def run(self):
    def configChannel(amqpClient):
      amqpClient.requestQoS(prefetchCount=1)

    # Open connection to rabbitmq
    with amqp.synchronous_amqp_client.SynchronousAmqpClient(
        amqp.connection.getRabbitmqConnectionParameters(),
        channelConfigCb=configChannel) as amqpClient:

      # Results
      amqpClient.declareExchange(self._resultsExchange,
                                 durable=True,
                                 exchangeType="topic")
      resQueue = amqpClient.declareQueue("res", durable=True)
      amqpClient.bindQueue(queue=resQueue.queue,
                           exchange=self._resultsExchange,
                           routingKey="res")


      # Start consuming messages
      amqpClient.createConsumer(resQueue.queue)

      for evt in amqpClient.readEvents():
        data = json.loads(evt.body)
        print ""
        if data["result"] == "Success":
          print ("Success: %s" % data["command"])
        else:
          print ("Failure: %s\n"
                 "Output: \n"
                 "%s" % (data["command"], data["body"]))
        evt.ack()




if __name__ == "__main__":
  setRabbitmqLoginScriptImpl()

  def configChannel(amqpClient):
    amqpClient.requestQoS(prefetchCount=1)

  # Open connection to rabbitmq
  with amqp.synchronous_amqp_client.SynchronousAmqpClient(
      amqp.connection.getRabbitmqConnectionParameters(),
      channelConfigCb=configChannel) as amqpClient:

    # Commands
    amqpClient.declareExchange("cmdExchange",
                               durable=True,
                               exchangeType="topic")
    result = amqpClient.declareQueue("cmds", durable=True)

    amqpClient.bindQueue(queue=result.queue,
                         exchange="cmdExchange",
                         routingKey="command")

    # Publish Commands
    with open('commandlist.json') as data:
      for cmd in json.load(data)["commands"]:
        msg = amqp.messages.Message(json.dumps({"command": cmd}))
        amqpClient.publish(msg, "cmdExchange", "command")

  Master().run()