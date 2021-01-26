# deepthought

This is the client side application which can connect to
[`hard-link`](https://github.com/ndsystems/hard-link) to get live-data from the
microscope.

## How to install

1. You could optionally use a virtual environment.
```
$ python -m pip install virtualenv
$ python -m virtualenv deepthought
$ source deepthought/bin/activate
$ python -m pip install -U pip
```
2. Install with:
`$ python -m pip install -e .`

## How to run

`$ python run.py`

## Troubleshooting

1. If you have `llvm11`, you might get error. Go back to `llvm10`.
