# simple-app-server
A simple server that listens for POST requests in parallel.

The client is a simple web client application that sends a request to buy or sell USD through
HTTP POST request. The application server waits for enough requests (default 10) and sends
them to the execution server (the execution server is already mocked). The execution server
decides what buy/sell orders are approved (or rejected) and returns the response. The
application server then responds to the clients if their buy/sell orders succeeded.

The Flow:
- Each client calls the application server with buy/sell order (HTTP POST).
- The application server waits until enough requests arrive (default 10).
- The application server calls the execution server to execute the orders (all the 10 in
the same call).
- The execution server responds with approval/rejection to each order (in the same
response).
- The application server response and closes the original client requests.
- The application server should be available for new calls during the process

