# deepthought

This is the client side application which can connect to
[`hard-link`](https://github.com/ndsystems/hard-link) to get live-data from the
microscope.

## How to install

1. You could optionally use a virtual environment.

```cmd
$ python -m pip install virtualenv
$ python -m virtualenv deepthought
$ source deepthought/bin/activate
$ python -m pip install -U pip
``````

2. Install with:
   ```cmd
   $ python -m pip install -e .
   ```

## How to run

```cmd 
$ python run.py
```

## Troubleshooting

1. If you have `llvm11`, you might get an error while installing `llvmlite`, which is required by `numba`. Go back to `llvm10`.

## How to access data

databroker manages access to data for us. To get started with the experimental data stored in deepthought/db_data/\*.msgpack,

set-up a yml configuration file for a catalog, where databroker looks for it.

1. Find out where databroker looks for it with `python3 -c "import databroker; print(databroker.catalog_search_path())"`
2. make a copy of `./catalog.yml` and edit it to point to `db_data/*.msgpack` correctly, and move the file to one of the catalog search paths.

to test if you have been succesfull,

1. open terminal from the context of `deepthought/deepthought`,
2. if this runs without error, you're good to go. `python3 -c "from data import db"`

accessing data programmatically

```python
from data import db

# returns the databroker.Header object which can give you the data in many forms
header = db[-1]

# access data as pandas.DataFrame
df = header.table()

```
