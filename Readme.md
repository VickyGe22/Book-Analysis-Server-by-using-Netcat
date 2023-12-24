# Book Analysis Server


# Introduction
This Python script implements a server application that receives text data from clients, processes it, and performs pattern analysis on it. 
It is designed to work with data from different books, identify patterns, and maintain a list of books sorted by the frequency of these patterns.


# Requirements
This project requires us to establish a local server and multiple clients by using Netcat tools and the NIO method for implementation. The server is responsible for receiving the command requirements and information sent from the client and output according to the client's requirements. The specific task is: the project needs to be able to accept and process commands sent by more than 10 clients at the same time, to achieve the concurrent running of threaded jobs. The client will send different books' data and meeting interval requirements. After receiving the client's instructions, the server takes turns accepting the book data sent by different clients according to the reading interval requirements, records the content of each book and the different book reading sequences with a linked list data structure, and prints out each read and write on the screen for inspection. Once the client sends the instruction, the server needs to start the operation immediately, and after the client ends and exits, the server needs to put the read content into a newly created text file. In addition, it is also necessary to establish two analysis threads, one of which is mainly to search for the pattern specified from the server port and output the detection content within a specified interval, and the output content format is the title and search frequency after the search frequency.


# Usage
## A. To start the server, run the script from the command line with the desired port and pattern as arguments. For example: ./assignment3.py -l 12345 -p "e"
## Arguments
-l or --listen: The port number on which the server will listen for incoming connections.
-p or --pattern: The pattern to search for in the text data.

## B. To start the client by using Netcat, run the script from the command line with the desired port and pattern as arguments. For example: nc localhost 12345 -i 5 < pg71873.txt
## Arguments
- localhost: the IP address or hostname of the machine
- 1234: port number on which NC will attempt to establish a connection; the server should be listening on port 1234 to accept incoming data
- -i <delay>: the -i option specifies the interval between sending and receiving data rows. If -1 is used, there will be a 1-second delay between each row
- > file.txt: redirection operation; This means that the contents of file.txt will be sent as input to the nc command. The contents of file.txt will be transmitted over a network connection to the specified address and port


# Functionality
## The script includes Three key components:
## First parts: Data structure [Node class and SharedList class]
Node and SharedList classes are used to store, manage, and search the text data/pattern in a linked list structure.
In the Node class, the input for a node is data and book_id received from client-server. Each data links with one book_id which ensure to figure out different data contents from various book and easily to printout and create a text file when the client terminates. Besides, we set three-pointers which are used to follow the next book node, the next node in the same book, and the next node used to find search frequency.
In the SharedList class, we create four main methods: add node, print book, and search function achieved by (adding book title, search pattern count, updating book frequency, and getting book sorted by frequency). Besides, we created three dictionaries to store book heads, the frequency of search patterns in each book, and the title of each book in order to link the title with frequency and easy for the analysis thread to do the printout function.

All the above code created is mainly used to power the below threading operation to achieve the function of tracking each line data from various books, creating a txt file for the content that the server read, searching the pattern frequency linked with each book title, and sorting by frequency.

## Second parts: Socket and Netcat [Main & Server class:initiate + listen]
In this script, we built up a simple Netcat to achieve the basic function of listening and connecting.
In the main, we use **argparse lib**(The argparse library is the Python standard library for handling command line arguments. By passing different parameters, we can control the program to perform different operations) to parse the command from the shell and figure out the listen and port information from the command initiated from clients.
Then **create nc** to call server class and started listening.
The main method is created to achieve socket and threading in the Server class: listen (used to listen to data from the client).
In the initiation stage, the input from Serverclass receives the arg from the **argparse**. Then, we initialize a NetCat object with the command-line arguments passed in from the main code block and then create a socket object. Besides, two locks are created in order to achieve synchronization.

In the listen method, the **bind** function is used to listen to data from command-line arguments. And for code **listen(n)**: the value passed in, where n represents the maximum number of connections the operating system can suspend before the server rejects (more than the limit).
Then we use a loop function about a **loop listens** for new connections and pass the connected socket object to the handle function to perform the task. We set a **running flag to control** the running of the server in order to ensure secure running for each stage and avoid errors. After that, **accept()** function will wait for an incoming connection and return the new socket representing the connection and the address of the client. We use client_socket to store the address. 
    Then, we set a lock here to record the number of clients and give an id for each client to easily the later data record and ensure the count number is accurate.
    After that, we create a separate thread for each client to manage by using **Tread function** (Python's threading.Thread class) which is used to handle tasks in the handle_client method and with two args that are required by handle_client) and store in client_thread. Then, use **start()** to start the thread, causing it to begin execution. Similarly with the analysis thread, adding a **daemon thread** due to reason that it is convenient for tasks and ensures that the pattern_analysis threads do not keep running and block the program from exiting after the handle_client thread has finished its execution. **Appending analysis threads to a list** in order to keep track of the created threads to make sure only one thread is used to do the tasks and the program can easily access the thread later. Therefore, the daemon nature ensures they don't prevent the program from exiting and appending them to a list allows for easy management of these threads.

    Then, we check the status of the client_thread by using the running flag. Once it is terminated, we close the socket by using **close()**. And checking their status by using **is_alive()** and waiting for all threads to complete using methods **join()** function to ensure the server can be terminated beautifully.


## Third parts: Multi-threading and Pattern analysis [Server class: handle_client + pattern analysis]

Two main methods created to achieve multi-threading and pattern analysis functions are: handle_client (used to execute client thread tasks) and pattern analysis(used to execute analysis thread tasks).
In the initialization, we **create three lists**: shared_list(used to store the data from the client book), pattern_queue(created a queue to record the book data in order to easy searching analysis operation), and book_titlelist(in order to track book title and achieve function to stdout the book title with frequency)

**Handle_client method**: the input is client socket and client_id, one id mapping one socket. We set a buffered_data to store the data. Then, the while True loop continuously receives data by using **recv()** up to 1024 bytes of data from the client_socket. If no data is received, the loop breaks, ending the data reception. Then we decode the entire buffered data to ensure the right format of data. After that, we set a lock to ensure each thread achieves concurrency. Only one thread can get the key and go into the critical section to do the data analysis. After the data is added to the node, the thread will release the key and the buffer will be cleared to let other threads store data. The data is written into a new file after the thread gets out of the critical section. Besides, we set two exceptions to detect and avoid decoding fails and socket_related errors.
Therefore, If a command is to be executed, the handle function passes the command to the thread in the listen function. Each time a command is received, it is executed with the handle_client function and the output back through the socket. In addition, the reason we use **buffer** is to process data in chunks (rather than byte-by-byte) more efficiently. The buffer allows for accumulating a  significant amount of data, which can then be processed at once, ensuring that network data is received, and accumulated, handling partial data, and multibyte characters, and improving overall efficiency.

**pattern_analysis method**: Similarily to the handle_client function, it is designed to periodically process and analyze book data from a queue (self.pattern_queue). And setting the timer to ensure the analysis_thread printout result periodically(**time.time() and interval**) Then, it updates shared data structures in a thread-safe manner using locks, signals other parts of the analysis thread when data is updated, and periodically outputs sorted book data based on the pattern frequency, ensuring multiple threads are processing and analyzing data concurrently. The use of locks and conditional checks(**self.data_updated.set()**) ensures that data is accessed and modified safely across multiple threads.
