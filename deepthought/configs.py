from collections import OrderedDict 
import os

config = OrderedDict()

def abspath(path):
    return os.path.abspath(path)

if os.name == 'nt':
    config["mm_dir"] = abspath("C:\Program Files\Micro-Manager-2.0gamma")

elif os.name == "posix":
    config["mm_dir"] = abspath("/home/dna/lab/software/micromanager/lib/micro-manager")

config["mm_config"] = abspath("./mmconfigs/Bright_Star.cfg")
config["mm_server"] = {"addr" : "localhost", "port" : 18861}