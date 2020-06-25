"handler for hardware abstraction layer"

from comms import get_object, serve_object
from configs import get_default

default = get_default()

hostname = default["mcu_server"]["hostname"]
port = int(default["mcu_server"]["port"])


class BaseScope:
    mmc = get_object(f"tcp://{hostname}:{port}")

    def device_properties(self, device):
        """get property names and values for the given device"""
        device_props = {}

        property_names = self.mmc.getDevicePropertyNames(device)

        for property_name in property_names:
            value = self.mmc.getProperty(device, property_name)
            device_props[property_name] = value

        return device_props

    def properties(self):
        """get property names and values for all loaded devices in scope"""
        all_device_props = {}

        list_of_devices = self.mmc.getLoadedDevices()

        for device in list_of_devices:
            device_props = self.device_properties(device)
            all_device_props[device] = device_props

        return all_device_props


class DefaultScope(BaseScope):
    """all default settings go here, including safety parameters"""
    # safety thresholds
    exposure_lower = 0.01  # ms
    exposure_higher = 2000  # ms

    z_higher = 5000  # um


class Scope(DefaultScope):
    def __init__(self):
        self.exposure = 10
        self.xy = [0, 0]
        self.z = 0
        self.channel = "FITC"
        self.objective = "10"
        self.shutter = "auto"
        super(Scope, self).__init__()

    @property
    def channel(self):
        return self.__channel

    @channel.setter
    def channel(self, label):
        self.mmc.setConfig("Channel", label)
        self.__channel = label

    @property
    def shutter(self):
        return self.__shutter

    @shutter.setter
    def shutter(self, label):
        self.__shutter = label

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


class BaseImaging(DefaultScope):
    def __init__(self):
        self.camera = "left_port"
        super(BaseImaging, self).__init__()

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


class pE4000(DefaultScope):
    __current_led = None
    __channel = None
    __intensity_label = None

    def set_led(self, value):
        led_channels = {
            "ChannelA": [365, 385, 405, 435],
            "ChannelB": [460, 470, 490, 500],
            "ChannelC": [525, 550, 580, 595],
            "ChannelD": [635, 660, 740, 770],
        }

        for channel, led_set in led_channels.items():
            if value in led_set:
                self.__current_led = value
                self.__channel = channel
                self.__intensity_label = "Intensity" + channel[-1]

        self.mmc.setProperty("pE4000", self.__channel, self.__current_led)
        return self.__current_led

    def set_intensity(self, value):
        self.mmc.setProperty("pE4000", self.__intensity_label, value)
        return value


class Illumination(pE4000):
    def __init__(self):
        self.led = 490
        self.led_intensity = 0
        super(Illumination, self).__init__()

    @property
    def led(self):
        return self.__led

    @led.setter
    def led(self, choice):
        self.__led = self.set_led(choice)

    @property
    def led_intensity(self):
        return self.__led_intensity

    @led_intensity.setter
    def led_intensity(self, choice):
        self.__led_intensity = self.set_intensity(choice)


def apply_settings(scope, settings):
    for key, value in settings.items():
        print("setting: ", key)
        setattr(scope, key, value)


class Acqusition(Scope, BaseImaging, Illumination):
    pass


if __name__ == "__main__":
    scope = Acqusition()
