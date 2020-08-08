# simple-app-server

## A simple server that listens for POST requests in parallel.

### 1. The Task:

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

### 2. Implementation details:

- Every order is created within a new thread, as the response can be available only after the last order from the batch is filled.

- Every batch is added to a map as they need to be safely removed once the execution server returns the updated values. That is, a contiguous data structure like a list would be very non efficient.

- Every batch, besides the list of orders, includes two variables:
<br/>1. "executed": a boolean. Becomes true once the batch was sent to execution. All the threads in the batch except _the last one_ use it to know when the response became available.
<br/>2. "finished_orders_num": an integer. The number of orders in a batch that already stored the values returned by the execution server. Used by the _last order_ from the batch to know when the batch can be safely deleted.

- If an integer is passed as the first parameter to the main function, then it's used as the size of the batches. Otherwise, the default is used (10).





