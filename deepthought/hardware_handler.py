"handler for hardware abstraction layer"
from comms import get_object


class Control:
    def __init__(self):
        self.mmc = get_object("tcp://127.0.0.1:12345")

    def set_channel(self, channel_label):
        self.mmc.setConfig("channel", channel_label)
        return channel_label

    def set_objective(self, objective_label):
        self.mmc.setConfig("objective", objective_label)
        return objective_label

    def set_exposure(self, exposure):
        self.mmc.setExposure(exposure)
        return self.get_exposure()

    def get_exposure(self):
        return self.mmc.getExposure()

    def set_xyz(self, xyz):
        x, y, z = xyz
        self.mmc.setXYPosition(x, y)
        self.mmc.setPosition(z)
        return self.get_xyz()

    def get_xyz(self):
        x, y = self.mmc.getXYPosition()
        z = self.mmc.getPosition()
        return (x, y, z)

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
    scope = Control()
