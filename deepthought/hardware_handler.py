"handler for hardware abstraction layer"
from comms import get_object, serve_object


class Default:
    exposure_lower = 0.01  # ms
    exposure_higher = 2000  # ms


class Scope(Default):
    def __init__(self):
        self.mmc = get_object("tcp://127.0.0.1:12345")
        self.exposure = 10
        self.xy = [0, 0]
        self.z = 0
        self.channel = "FITC"
        self.objective = "10X"

    @property
    def channel(self):
        return self.__channel

    @channel.setter
    def channel(self, label):
        self.mmc.setConfig("Channel", label)
        self.__channel = label

    @property
    def objective(self):
        return self.__objective

    @objective.setter
    def objective(self, label):
        self.mmc.setConfig("Objective", label)
        self.__objective = label

    @property
    def exposure(self):
        return self.__exposure

    @exposure.setter
    def exposure(self, value):
        if value < self.exposure_lower:
            value = self.exposure_lower

        elif value > self.exposure_higher:
            value = self.exposure_higher

        self.mmc.setExposure(value)
        self.__exposure = value

    @property
    def xy(self):
        return self.__xy

    @xy.setter
    def xy(self, value):
        self.mmc.setXYPosition(*value)
        self.__xy = value

    @property
    def z(self):
        return self.__z

    @z.setter
    def z(self, value):
        self.mmc.setPosition(value)
        self.__z = value

    # @visualize
    def get_image(self):
        self.mmc.snapImage()
        img = self.mmc.getImage()
        return img

    def get_all_properties(self):
        list_of_devices = self.mmc.getLoadedDevices()
        all_device_props = {}

        for device in list_of_devices:
            list_of_properties = self.mmc.getDevicePropertyNames(device)

            device_props = {}
            for property_ in list_of_properties:
                value = self.mmc.getProperty(device, property_)
                device_props[property_] = value

            all_device_props[device] = device_props
        return all_device_props


if __name__ == "__main__":
    scope = Scope()
    serve_object(scope, "tcp://127.0.0.1:12346")
