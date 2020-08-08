import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from collections import defaultdict

HOST_NAME = ""
PORT = 8080
OK = 200
BAD_REQUEST = 400
INTERNAL_SERVER_ERROR = 500
EXECUTION_BATCH_SIZE = 2
APPROVED = "approved"
REJECTED = "rejected"
"""
all_batches is a list of OrdersBatch.
All the batches are all the time full, maybe except for the last one.
Every new order is appended to the last batch, if not full.
Otherwise, a new batch is created and the order appended to it.
"""

global_index = 0


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
        self.__finished_orders_num += 1

    def all_orders_ended(self):
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
        :return: The orders after the update.
        """
        self.__orders = ExecutionSdk.execute_orders(self.__orders)
        self.__executed = True


all_batches = defaultdict(OrdersBatch)


class Order:
    """
    An order. They are instantiated by the App Server,
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
        added just to illustrate how it could be in reality.
        (That is, the execution server wouldn't work like in the mocking
        but in a asynchronous way.)
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

        # critic part!!
        index = MyServer.get_order_index()
        # !!!!!!!!!!!!!!!!!!!!!

        global all_batches
        batch = all_batches[MyServer.get_batch_index(index)]
        batch.append(order)

        """
        At this point, we have the order and the correspondent batch.
        If the batch is full, it can be sent to the execution server.
        Otherwise, we wait for the batch to be full. 
        That is, until "was_executed()" returns True.
        """
        if len(batch) == EXECUTION_BATCH_SIZE:
            batch.execute()
            exit_code = MyServer.get_exit_code(index)#(batch, order)
            while not batch.all_orders_ended():
                pass
            all_batches.pop(int(index / EXECUTION_BATCH_SIZE))

        else:
            while not batch.was_executed():
                pass
            exit_code = MyServer.get_exit_code(index)#(batch, order)

        """
        At this point, we know the request was well formed.
        The response code is "OK" iff the execution server returned APPROVED.
        """
        self.exit(exit_code)

    @staticmethod
    def get_exit_code(order_index):
        batch_index = MyServer.get_batch_index(order_index)
        batch = all_batches[batch_index]

        order = all_batches[batch_index][]

        batch.increase_ended()

        return OK if current_order.status == APPROVED else INTERNAL_SERVER_ERROR

    @staticmethod
    def get_order_index():
        global global_index
        global_index += 1
        return global_index - 1

    @staticmethod
    def get_batch_index(order_index):
        return int(order_index / EXECUTION_BATCH_SIZE)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == "__main__":
    webServer = ThreadedHTTPServer((HOST_NAME, PORT), MyServer)
    print("Server started http://%s:%s" % (HOST_NAME, PORT))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")
