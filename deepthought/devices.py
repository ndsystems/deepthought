"abstraction of devices"

class BaseScope:
    def __init__(self, mmc):
        self.mmc = mmc

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


class pE4000(BaseScope):
    __current_led = None
    __channel = None
    __intensity_label = None

    def set_led(self, value):
        led_channels = {
            "A": [365, 385, 405, 435],
            "B": [460, 470, 490, 500],
            "C": [525, 550, 580, 595],
            "D": [635, 660, 740, 770],
        }

        for channel, led_set in led_channels.items():
            if value in led_set:
                self.__current_led = value
                self.__channel = "Channel" + channel
                self.__intensity_label = "Intensity" + channel

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
