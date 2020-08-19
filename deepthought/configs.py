from collections import OrderedDict 
import os

config = OrderedDict()

def abspath(path):
    return os.path.abspath(path)


name = "MM_DIR"
if name in os.environ:
    value = os.environ[name]
else:
    value = "C:\Program Files\Micro-Manager-2.0gamma"

config["mm_dir"] = abspath(value)


name = "MM_CONFIG"
if name in os.environ:
    value = os.environ[name]
else:
    value = "Bright_Star.cfg"

config["mm_config"] = abspath(f"./mmconfigs/{value}")


name = "MM_IP"
if name in os.environ:
    value = os.environ[name]
else:
    value = "localhost"

config["mm_server"] = {"addr" : value, "port" : 18861}
