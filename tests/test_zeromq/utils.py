from threading import Thread

def run_poller_for(medium, timeout):
    thread = Thread(target=medium.loop, args=(timeout,))
    thread.start()