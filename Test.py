import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

HOST_NAME = ""
PORT = 8080
OK = 200
BAD_REQUEST = 400
INTERNAL_SERVER_ERROR = 500
ORDERS_NUM = 2
APPROVED = "approved"
REJECTED = "rejected"

# "all_orders" variable is right now global. Is that correct?
# And how could the variable "ORDERS_NUM" be changed? Should be by default 10
all_orders = []


class OrderList:
    """
    A list of orders: a simple wrapper for a list.
    In addition to the orders, it stores the boolean "executed",
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
    def __init__(self, price, order):
        self.price = price
        self.order = order
        self.status = None


class ExecutionSdk:
    @staticmethod
    def execute_orders(orders: list):
        orders = orders.copy()
        """
        The mock execution server approves the orders for odd-number prices.
        """
        for order in orders:
            order.status = APPROVED if int(order.price) % 2 else REJECTED
        return orders


class MyServer(BaseHTTPRequestHandler):
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
        If price or order are missing from POST, the operation should fail.
        Some error msg should/can be added?
        """
        if not price or not order:
            exit(BAD_REQUEST)

        current_order = Order(price, order)
        current_list = MyServer.get_current_list(current_order)

        """
        At this point, we got the order and the correspondent list.
        If the list is full, it can be sent to the execution server.
        Otherwise, we wait for the list to be full. 
        That is, until "executed" parameter becomes True in object current_list.
        """
        if len(current_list) == ORDERS_NUM:
            current_list.execute()

        while not current_list.was_executed():
            pass

        """
        At this point, we know the request was well formed.
        The response code is "OK" iff the execution server returned APPROVED.
        """
        self.exit(OK if current_order.status == APPROVED else INTERNAL_SERVER_ERROR)

        # how can we further check?
        # how can we remove all lists that are now garbage?

    @staticmethod
    def get_current_list(current_order):
        """
        Receives an order and returns the full list that will be eventually sent to execution.
        :param current_order: The order being processed.
        :return: The list in which the order will be executed.
        """
        global all_orders
        current_list_index = len(all_orders) - 1
        if current_list_index==-1 or len(all_orders[current_list_index]):
            current_list_index += 1
        current_list = next((lst for lst in all_orders if not lst.was_executed()), None)
        if not current_list:
            current_list = OrderList()
            all_orders.append(current_list)
        current_list.append(current_order)
        return current_list


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == "__main__":
    # webServer = HTTPServer((HOST_NAME, PORT), MyServer)

    webServer = ThreadedHTTPServer((HOST_NAME, PORT), MyServer)

    print("Server started http://%s:%s" % (HOST_NAME, PORT))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")
