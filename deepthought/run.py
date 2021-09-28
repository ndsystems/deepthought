from microscope import Microscope, ChannelConfig, RE


if __name__ == "__main__":
    tritc = ChannelConfig("TRITC")
    tritc.exposure = 500
    tritc.model = {"kind": "nuclei",
                  "diameter": 100}

    dapi = ChannelConfig("DAPI")
    dapi.exposure = 30
    dapi.model = {"kind": "nuclei",
                  "diameter": 100}

    fitc = ChannelConfig("FITC")
    fitc.exposure = 300
    fitc.model = {"kind": "nuclei",
                  "diameter": 100}

    m = Microscope()
    m.mmc.setXYPosition(-32808.46, -1314.0)

    plan = m.scan(channel=dapi, secondary_channel=fitc, num=10000)
    uid, = RE(plan)
