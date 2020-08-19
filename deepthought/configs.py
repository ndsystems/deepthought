from collections import OrderedDict 
import os

config = OrderedDict()

def abspath(path):
    return os.path.abspath(path)

if os.name == 'nt':
    config["mm_dir"] = abspath("C:\Program Files\Micro-Manager-2.0gamma")

elif os.name == "posix":
    config["mm_dir"] = abspath("/home/dna/lab/software/micromanager/lib/micro-manager")

config["mm_config"] = "./mmconfigs/Bright_Star.cfg"

mm_ip = "MM_IP"
if mm_ip in os.environ:
    mm_server_ip = os.environ[mm_ip]
else:
    mm_server_ip = "localhost"

config["mm_server"] = {"addr" : mm_server_ip, "port" : 18861}
