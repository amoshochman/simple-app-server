import json
import time
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from collections import defaultdict
import threading

HOST_NAME = ""
PORT = 8080
OK = 200
BAD_REQUEST = 400
INTERNAL_SERVER_ERROR = 500
APPROVED = "approved"
REJECTED = "rejected"


class OrdersBatch:
    """
    A batch of orders: a simple wrapper for a list of orders.
    It stores the orders and the boolean "executed",
    which is true iff the list was already sent to the execution server.
    """

    def __init__(self):
        self.__orders = []
        self.__executed = False
        self.__finished_orders_num = 0

    def __len__(self):
        return len(self.__orders)

    def increase_ended(self):
        with lock:
            self.__finished_orders_num += 1

    def all_orders_ended(self):
        """
        Returns True if all the orders "finished".
        :return: True iff all the threads stored the values returned by the
        execution server.
        """
        return self.__finished_orders_num == EXECUTION_BATCH_SIZE

    def append(self, order):
        self.__orders.append(order)

    def get_orders(self):
        return self.__orders

    def set_orders(self, orders):
        self.__orders = orders

    def was_executed(self):
        return self.__executed

    def execute(self):
        """
        Sents the orders to execution and sets the boolean "executed" to True.
        That boolean is used by the other threads to know that the orders were processed.
        :return: The orders after the update.
        """
        self.__orders = ExecutionSdk.execute_orders(self.__orders)
        self.__executed = True


lock = threading.Lock()
global_index = -1
all_batches = defaultdict(OrdersBatch)

"""
all_batches is a dictionary of OrdersBatch which uses as key the number of batch.
Every new order increases global_index by 1 and it's appended
to batch number floor(global_index/EXECUTION_BATCH_SIZE).
When all the information from a batch of orders is used, the batch is deleted.
We lock two critical sections. When we're retrieving the number of the
relevant batch, and when the number of ended orders within a batch is updated.
"""


class Order:
    """
    An order. It's instantiated by the App Server,
    which sends them in batches to the Execution Server.
    """

    def __init__(self, price, order):
        self.price = price
        self.order = order
        self.status = None


class ExecutionSdk:
    """
    A mock of the Execution Server.
    Receives a batch of orders, updates them and returns them.
    """

    @staticmethod
    def execute_orders(orders: list, index=None):
        """
        Execute orders received from the App Server. "index" parameter not being used,
        added just to illustrate how it should really work.
        That is, the execution server would in an asynchronous way.
        :param orders: The orders.
        :param index: The index for the list of orders.
        :return: The updated orders.
        """
        orders = orders.copy()
        """
        An almost-trivial mocking: the server approves the orders for odd-number prices.
        """
        for order in orders:
            order.status = APPROVED if int(order.price) % 2 else REJECTED
        return orders, index


class MyServer(BaseHTTPRequestHandler):
    """
    The Application Server.
    """

    def exit(self, code):
        self.send_response(code)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        content = self.rfile.read(content_length)
        content = json.loads(content)

        price_input = content.get('price')
        order_input = content.get('order')

        """
        If price or order are missing from POST request, the operation fails.
        """
        if not price_input or not order_input:
            exit(BAD_REQUEST)

        order = Order(price_input, order_input)

        with lock:
            batch, batch_index, index_in_batch = MyServer.get_batch(order)

        """
        At this point, we have the batch and the relevant indices:
        The batch index and the order index within the batch.
        If the batch is not full, the server waits. 
        If the batch is full, it's sent to the execution server.
        That happens when "was_executed()" returns True.
        """

        if index_in_batch < EXECUTION_BATCH_SIZE - 1:
            while not batch.was_executed():
                time.sleep(1)
            exit_code = MyServer.get_exit_code(batch, order)

        else:
            batch.execute()
            exit_code = MyServer.get_exit_code(batch, order)
            while not batch.all_orders_ended():
                time.sleep(1)
            """
            After the calling to "get_exit_code", the number of finished threads within the
            batch was increased by one and the relevant information from the execution server
            was stored. Therefore, in case this was the last order in the batch, 
            the batch can be safely removed.
            """
            all_batches.pop(batch_index)

        """
        At this point, we know the request was well formed.
        The response code is "OK" iff the execution server returned APPROVED.
        """
        self.exit(exit_code)

    @staticmethod
    def get_exit_code(batch, order):
        """
        Given a batch and an order, it increases the number of "finished orders"
        in the batch, and returns the relevant exit code.
        :param batch: A batch of orders.
        :param order: The relevant order.
        :return: The relevant exit code.
        """
        batch.increase_ended()
        return OK if order.status == APPROVED else INTERNAL_SERVER_ERROR

    @staticmethod
    def get_batch(order):
        """
        Receives an order and returns the relevant batch.
        :param order: The order being processed.
        :return: The batch that the order will belong to, the index of the relevant batch
        and the index of the order within the batch.
        """
        global all_batches, global_index
        global_index += 1
        """
        The global index defines both the index of the batch and the index 
        within the batch.
        """
        batch_index = int(global_index / EXECUTION_BATCH_SIZE)
        index_in_batch = global_index % EXECUTION_BATCH_SIZE
        """
        A collections.defaultdict is used. If all_batches[batch_index] doesn't exist,
        a new OrdersBatch it's created.
        """
        batch = all_batches[batch_index]
        batch.append(order)
        return batch, batch_index, index_in_batch


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == "__main__":
    """
    If parameters are provided and the first one is an integer,
    it's taken as the EXECUTION_BATCH_SIZE.
    """
    try:
        EXECUTION_BATCH_SIZE = int(sys.argv[1])
    except (ValueError, IndexError):
        EXECUTION_BATCH_SIZE = 10
    webServer = ThreadedHTTPServer((HOST_NAME, PORT), MyServer)
    print("Server started http://%s:%s" % (HOST_NAME, PORT))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")
