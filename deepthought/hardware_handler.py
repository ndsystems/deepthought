"handler for hardware abstraction layer"
from comms import get_object, serve_object


class BaseScope:
    # safety thresholds
    exposure_lower = 0.01  # ms
    exposure_higher = 2000  # ms

    z_higher = 5000

    mmc = get_object("tcp://127.0.0.1:12345")

    def device_properties(self, device):
        """get property names and values for the given device"""
        property_names = self.mmc.getDevicePropertyNames(device)
        device_props = {}
        for property_name in property_names:
            value = self.mmc.getProperty(device, property_name)
            device_props[property_name] = value
        return device_props

    def properties(self):
        """get property names and values for all loaded devices in scope"""
        list_of_devices = self.mmc.getLoadedDevices()
        all_device_props = {}

        for device in list_of_devices:
            device_props = self.device_properties(device)
            all_device_props[device] = device_props
        return all_device_props


class Scope(BaseScope):
    def __init__(self):
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
        # escape the objective lens here, if not done by MMCore
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
        # stage limits here
        self.mmc.setXYPosition(*value)
        self.__xy = value

    @property
    def z(self):
        return self.__z

    @z.setter
    def z(self, value):
        if value >= self.z_higher:
            raise ValueError("Z higher limit reached")

        self.mmc.setPosition(value)
        self.__z = value


class ImagingScope(Scope):
    def __init__(self):
        super().__init__()
        self.camera = "Camera"

    @property
    def camera(self):
        return self.__camera

    @camera.setter
    def camera(self, label):
        self.mmc.setCameraDevice(label)
        self.__camera = label

    # @visualize
    def image(self):
        self.mmc.snapImage()
        img = self.mmc.getImage()
        return img


if __name__ == "__main__":
    scope = ImagingScope()
