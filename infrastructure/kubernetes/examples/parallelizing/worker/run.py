#!/usr/bin/env python

import json
from logging import getLogger
import subprocess

from nta.utils import amqp
from nta.utils.tools.set_rabbitmq_login_impl import setRabbitmqLoginScriptImpl



class Worker(object):

  def __init__(self):
    self._log = getLogger(__name__)
    self._cmdExchange = "cmdExchange"
    self._resultsExchange = "resExchange"


  def commandHandler(self, message):
    """
    :return: (out, err, rc) of the command
    """
    cmd = json.loads(message.body)["command"]
    message.ack()
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    rc = proc.returncode
    return (out, err, rc)


  def run(self):
    def configChannel(amqpClient):
      amqpClient.requestQoS(prefetchCount=1)

    # Open connection to rabbitmq
    with amqp.synchronous_amqp_client.SynchronousAmqpClient(
        amqp.connection.getRabbitmqConnectionParameters(),
        channelConfigCb=configChannel) as amqpClient:

      # Commands
      amqpClient.declareExchange(self._cmdExchange,
                                 durable=True,
                                 exchangeType="topic")
      cmdQueue = amqpClient.declareQueue("cmds", durable=True)
      amqpClient.bindQueue(queue=cmdQueue.queue,
                           exchange=self._cmdExchange,
                           routingKey="command")

      # Results
      amqpClient.declareExchange(self._resultsExchange,
                                 durable=True,
                                 exchangeType="topic")
      resQueue = amqpClient.declareQueue("res", durable=True)
      amqpClient.bindQueue(queue=resQueue.queue,
                           exchange=self._resultsExchange,
                           routingKey="res")


      # Start consuming messages
      consumer = amqpClient.createConsumer(cmdQueue.queue)

      for evt in amqpClient.readEvents():
        if isinstance(evt, amqp.messages.ConsumerMessage):
          (out, err, rc) = self.commandHandler(evt)

          if not rc:
            #success
            msg = amqp.messages.Message(json.dumps(
                {"command": json.loads(evt.body)["command"],
                 "result": "Success",
                 "body": out}))
            amqpClient.publish(msg, self._resultsExchange, "res")
          else:
            #failure
            msg = amqp.messages.Message(json.dumps(
                {"command": json.loads(evt.body)["command"],
                 "result": "Failure",
                 "body": out}))
            amqpClient.publish(msg, self._resultsExchange, "res")

        elif isinstance(evt, amqp.consumer.ConsumerCancellation):
          # Bad news: this likely means that our queue was deleted externally
          msg = "Consumer cancelled by broker: %r (%r)" % (evt, consumer)
          self._log.critical(msg)
          raise Exception(msg)

        else:
          self._log.warning("Unexpected amqp event=%r", evt)



if __name__ == "__main__":
  setRabbitmqLoginScriptImpl()

  Worker().run()
