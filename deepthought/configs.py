import configparser


def get_default():
    default = configparser.ConfigParser()
    default.read('default.ini')
    return default


if __name__ == "__main__":
    default = get_default()
    print(default.sections())
