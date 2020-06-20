"""To keep track of changes in MMCore"""
import pymmcore


class PyMMEventCallBack(pymmcore.MMEventCallback):
    @classmethod
    def onPropertiesChanged():
        print("Property changed")

    def onStagePositionChanged(self, *args):
        print("stage position changed ", args)

    def onExposureChanged(self, *args):
        print("exposure changed ", args)
