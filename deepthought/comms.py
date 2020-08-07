"""Patterns for communication protocol between microservices or modules to interact with different objects"""
import rpyc
from rpyc.utils.server import ThreadedServer


def share_object(object_, port=18861):
    """expose an object in an address for get_object to connect to"""
    server = ThreadedServer(object_, port=port, protocol_config={
    "allow_all_attrs": True, "allow_pickle" : True,
    })
    print(f"starting server in port {port}")
    server.start()


def get_object(addr="localhost", port=18861):
    """connect to an object served by serve_object"""
    obj = rpyc.connect(addr, port, config={"allow_all_attrs": True, "allow_pickle" : True })
    print(f"connected to {port}")
    return obj.root