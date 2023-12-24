#!/usr/bin/env python3

import argparse
import socket
import threading
import time
import queue

INTERVAL = 5  # Time interval for analysis output
analysis_lock = threading.Lock()


class Node:
    
    def __init__(self, data, book_id):
        self.data = data # The text data
        self.book_id = book_id # Identifier for the book
        self.next = None  # Pointer to the next node in the linked list
        self.book_next = None # Pointer to the next node in the same book
        self.next_frequent_search = None # Unused pointer for future use

class SharedList:

    def __init__(self):
        self.head = None # Head of the linked list
        self.book_heads = {}  # Dictionary of book heads
        self.last_node = None  # Last node in the list
        self.last_search_node = None  # Keep track of last node to add at the end
        self.book_frequency = {} # Stores the frequency of the search pattern in each book
        self.book_titles = {} # Stores the title of each book


    def add_node(self, data, book_id):
        
        new_node = Node(data, book_id)
        # Adding to the end of the shared list
        if self.last_node:
            self.last_node.next = new_node
        else:
            self.head = new_node

        # Setting the book_next link
        if book_id in self.book_heads:
            book_last_node = self.book_heads[book_id]
            while book_last_node.book_next:
                book_last_node = book_last_node.book_next
            book_last_node.book_next = new_node
        else:
            self.book_heads[book_id] = new_node

        self.last_node = new_node
        print(f"Added node with data from book_{book_id}: {data}")

    def print_book(self, book_id):
        if book_id in self.book_heads:
            current = self.book_heads[book_id]
            while current:
                print(current.data)
                current = current.book_next

    def add_book_title(self, book_id, book_title):
        self.book_titles[book_id] = book_title

    def search_pattern_count(self, book_title, pattern):
        count = 0
        current = self.book_heads.get(book_title)
        while current:
            count += current.data.count(pattern)
            current = current.book_next
        return count
    
    def update_book_frequency(self, book_title, pattern):
        count = self.search_pattern_count(book_title, pattern)
        if count:
            self.book_frequency[book_title] = count
        elif book_title in self.book_frequency:
            del self.book_frequency[book_title]

    def get_books_sorted_by_frequency(self):
        return sorted(self.book_frequency.items(), key=lambda x: x[1], reverse=True)



class ServerClass:

    def __init__(self, args):
        # using main to input arg，initialize a netcat then socket
        self.args = args
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create an INET, STREAMing socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # allow reuse of addresses
        self.pattern = args.pattern # storing the searching pattern

        self.shared_list = SharedList() # storing all data
        self.client_counter = 0 # every client with an unique ID
        self.client_counter_lock = threading.Lock()
        self.shared_list_lock = threading.Lock()

        self.analysis_threads = []  # List to keep track of analysis threads
        self.book_titlelist = SharedList() # storing all book titles
        self.pattern_queue = queue.Queue()  # Queue for pattern analysis
        self.data_updated = threading.Event()  # Flag to indicate new data has been received
        self.last_time_output = time.time()  # Keep track of last time output was printed

        self.running = True  # Flag to control the running of server


    # listen data from client
    def listen(self):
        self.socket.bind(('localhost', args.listen))
        print(f"Server listening on port {args.listen}....")
        # listen(n) the value passed in, n, represents the maximum number of connections that the operating system can suspend before the server rejects (more than the limit).
        self.socket.listen(5)
        
        # A loop listens for new connections and passes the connected socket object to the handle function to perform the task
        try:
            while self.running:
                # accept()wait for connect,return client socket and address
                client_socket, addr = self.socket.accept() 
                # create a thread to manage client
                with self.client_counter_lock:
                    self.client_counter += 1
                    client_id = self.client_counter
                print(f"Accepted connection from {addr}, assigned ID: {client_id}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_id))
                client_thread.start()

                # Start the analysis threads
                for _ in range(2):  # Start two analysis threads, for example
                    analysis_thread = threading.Thread(target=self.pattern_analysis) # create a thread to manage analysis
                    analysis_thread.daemon = True # Set the analysis subthread parameters so that when the main thread ends, the subthread ends
                    analysis_thread.start() # start analyzing thread
                    self.analysis_threads.append(analysis_thread)
        except KeyboardInterrupt:
            print("Shutting down server...")
            self.running = False
            self.socket.close()
            for thread in self.analysis_threads:
                if thread.is_alive():
                    thread.join()
            # Handle other cleanup if necessary
        


    # executive thread tasks
    def handle_client(self, client_socket, client_id):
        
        buffered_data = bytearray()
        book_title = None  # Initialize book_title to None

        while True:
            chunk = client_socket.recv(1024)
            if not chunk:
                break

            buffered_data.extend(chunk)

            try:
                # Try to decode the entire buffered data
                data = buffered_data.decode('utf-8')
                # Process data if decoding is successful
                if data:
                    # Synchronize access to the shared list
                    with self.shared_list_lock:
                        for line in data.splitlines():
                            if line.startswith("Title"):
                                _,book_title = line.split(':', 1)
                                self.book_titlelist.add_book_title(client_id, book_title.strip())
                            self.shared_list.add_node(line, client_id)
                            self.pattern_queue.put(client_id)  # Add book_id to the pattern queue
                    buffered_data.clear()  # Clear the buffer once data is processed
            except UnicodeDecodeError:
                # If decoding fails, wait for more data (continue the loop)
                continue
            except socket.error as e:
            # Handle socket-related errors
                print(f"Socket error: {e}")
                break

        filename = f"book_{str(client_id).zfill(2)}.txt"
        with open(filename, 'w') as file:
            current = self.shared_list.book_heads[client_id]
            while current:
                file.write(current.data + "\n")
                current = current.book_next

        client_socket.close()

    #execute analysis thread tasks
    def pattern_analysis(self):
        while self.running:
            try:
                # Get the next book_id to analyze
                book_id = self.pattern_queue.get(timeout=INTERVAL)
                with self.shared_list_lock:
                    self.shared_list.update_book_frequency(book_id, self.pattern)
                self.data_updated.set()  # Signal that new data has been analyzed
            except queue.Empty:
                pass  # If the queue is empty, simply pass

            # Output the sorted books by frequency
            current_time = time.time()
            if current_time - self.last_time_output >= INTERVAL:
                with analysis_lock:
                    # Check again to ensure that no other thread has printed in the meantime
                    if current_time - self.last_time_output >= INTERVAL:
                        sorted_books = self.shared_list.get_books_sorted_by_frequency()
                        if sorted_books:
                            print("Sorted frequency:")
                            for book_id, count in sorted_books:
                                book_title = self.book_titlelist.book_titles.get(book_id, "Unknown Book")
                                print(f"{book_title}: {count}")
                        self.last_time_output = current_time  # Update the last output time
            
            # # The event is cleared after the output check
            # self.data_updated.clear()

                    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Network client to send lines of a book.')
    parser.add_argument('-l', '--listen', type=int, help='Port number to listen on.')
    parser.add_argument('-p', '--pattern', type=str, help='Search pattern to count.')
    args = parser.parse_args()

    try:
        nc = ServerClass(args)
        nc.listen()
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("Server terminated.")


