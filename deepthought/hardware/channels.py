class ChannelConfig:
    def __init__(self, name):
        self.name = name
        self.detector = None
        self.exposure = None
        self.marker = None
        self.detect_with = None

    def __repr__(self):
        return f"{self.name}, {self.marker}"
