"""Patterns for communication protocol between microservices or modules to interact with different objects"""
import rpyc
from rpyc.utils.server import ThreadedServer


def server(object_, port, *args, **kwargs):
    """serving an object in a port.
    
    parameters
    --
        object_ : object
            any python object that needs to be network enabled.
        port : int
            defines the port where the server is listening for requests.

    
    """
    s = ThreadedServer(object_, hostname="", port=port, auto_register=None,
                         protocol_config={"allow_all_attrs": True, 
                                          "allow_pickle" : True,
                                        }
                      )
    print(f"Starting server in: {port}")
    return s

def client(addr, port, *args, **kwargs):
    """generic function to connect to a rpyc server.
    
    parameters
    --
        addr : str
            ip address/url of the server
        port : int
            port
    """
    obj = rpyc.connect(addr, port, config={
        "allow_all_attrs": True, "allow_pickle" : True
    })
    
    print(f"Connected to server in {addr}:{port}")
    return obj.root

