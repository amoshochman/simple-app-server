import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

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
all_batches = []


class OrdersBatch:
    """
    A batch of orders: a simple wrapper for a list of orders.
    It stores the orders and the boolean "executed",
    which is true iff the list was already sent to the execution server.
    """

    def __init__(self):
        self.__orders = []
        self.__executed = False

    def __len__(self):
        return len(self.__orders)

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
    def execute_orders(orders: list):
        orders = orders.copy()
        """
        An almost-trivial mocking: the server approves the orders for odd-number prices.
        """
        for order in orders:
            order.status = APPROVED if int(order.price) % 2 else REJECTED
        return orders


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

        price = content.get('price')
        order = content.get('order')

        """
        If price or order are missing from POST request, the operation fails.
        """
        if not price or not order:
            exit(BAD_REQUEST)

        current_order = Order(price, order)
        current_batch = MyServer.get_current_batch(current_order)

        """
        At this point, we have the order and the correspondent batch.
        If the batch is full, it can be sent to the execution server.
        Otherwise, we wait for the batch to be full. 
        That is, until "was_executed()" returns True.
        """
        if len(current_batch) == EXECUTION_BATCH_SIZE:
            current_batch.execute()

        while not current_batch.was_executed():
            pass

        """
        At this point, we know the request was well formed.
        The response code is "OK" iff the execution server returned APPROVED.
        """
        self.exit(OK if current_order.status == APPROVED else INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_current_batch(current_order):
        """
        Receives an order and returns the relevant batch.
        :param current_order: The order being processed.
        :return: The batch that the order will belong to.
        """
        global all_batches
        """
        We create a new batch if the last one is full or if there are no batches yet.
        """
        if not all_batches or len(all_batches[-1]) == EXECUTION_BATCH_SIZE:
            current_batch = OrdersBatch()
            all_batches.append(current_batch)
        else:
            current_batch = all_batches[-1]
        """
        The batch is defined; the order can be appended to it.
        """
        current_batch.append(current_order)
        return current_batch


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
