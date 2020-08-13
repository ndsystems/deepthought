deepthought (dt) is a microscope acquisition library that aims to provide an easy to use API for higher order tasks performed by a microscope user.

# Architecture Overview
dt uses the micromanager MMCore hardware abstraction layer to communicate with the hardware. The hardware abstraction layer is run separately, and accesibly by RPC like a microservice. (`mm_server`)

In a higher level of abstraction, the devices are `ophyd` objects that makes them compatible with `bluesky` for experiment orchestration and data management.

Future plans include live spatial mapping of sample.
