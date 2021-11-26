class FrameGroupVisualizer:
    def __init__(self):
        self.fig, self.ax = plt.subplots(1, 3, figsize=(9, 3), dpi=120)
        self.ax[0].set_aspect('equal')
        self.ax[1].set_xlabel("Nuclear Size")
        self.ax[1].set_ylabel("Frequency")
        self.ax[0].set_xlabel("Stage X (um)")
        self.ax[0].set_ylabel("Stage Y (um)")
        self.frame_n = 1
        self.object_count = 0
        self.nuclear_size = []
        plt.tight_layout()
        plt.show(block=False)

    def update_map(self, frame):
        object_coords = [ob.xy for ob in frame._objects]
        self.object_count += len(object_coords)
        coords_x = [_[0] for _ in object_coords]
        coords_y = [_[1] for _ in object_coords]

        self.ax[0].set_title(f"N = {self.object_count} from {self.frame_n} frames")
        self.ax[0].scatter(coords_x, coords_y,  s=7)

    def update_nuclear_size(self, frame):
        self.nuclear_size.extend([ob.area for ob in frame._objects])
        self.ax[1].hist(self.nuclear_size)
        self.ax[1].cla()
        self.ax[1].set_xlabel("Nuclear Size")
        self.ax[1].set_ylabel("Frequency")
        self.ax[1].hist(self.nuclear_size)

    def update_intensities(self, frame):
        if len(frame.secondary_images) > 1:
            self.ax[2].set_xlabel(f"{frame.secondary_images[0].channel} mean")
            self.ax[2].set_ylabel(f"{frame.secondary_images[1].channel} mean")
            intensity_secondary = [ob.intensity_image.mean() for ob in frame.secondary_images[0]._objects]
            intensity_secondary_2 = [ob.intensity_image.mean() for ob in frame.secondary_images[1]._objects]
            self.ax[2].scatter(intensity_secondary, intensity_secondary_2,  s=7)
    
    def update(self, frame):
        self.update_map(frame)
        self.update_nuclear_size(frame)
        self.update_intensities(frame)
        self.frame_n += 1
        self.fig.canvas.draw()

def detect_from_frame(frame):
    image = frame.image
    model = frame.channel.model
    label = segment(image, **model)
    return self.label

class Coords:
    def __init__(self, xy):
        self.xy = xy

   
class FrameGroupProcessor:
    def __init__(self):
        pass

    def update(self, frame):
        self.segment(frame)

    def segment(self, frame):
        img = frame.image
        model = frame.channel.model
        frame.label = segment(img, **model)

    def anisotropy(self, frame):
        ...

class TimeGroup:
    def __init__(self):
        self.timesteps = []
    
    def add(self, group):
        self.timesteps.append(group)
        
    def __getitem__(self, item):
        return self.timesteps[item]

    def __len__(self):
        return len(self.timesteps)

class FrameGroup:
    def __init__(self):
        self.frames = []
        self._subscribers = []
    
    def add(self, frame):
        self.frames.append(frame)
        self.notify()
    
    def __getitem__(self, item):
        return self.frames[item]

    def subscribe(self, processor):
        if processor not in self._subscribers:
            self._subscribers.append(processor)

    def notify(self):
        for _ in self._subscribers:
            _.update(self.frames[-1])

    def dump(self, t):
        with open(f'filename_{t}.pickle', 'wb') as handle:
            pickle.dump(self, handle)


class Frame:
    def __init__(self, channel, image, coords):
        self.channel = channel
        self.image = image
        self.coords = coords

class Experiments:
    # pcna time series for 24h - 100+ cells
    # pcna time series with NCS low dose (0.1ug/ml)
    #   * 6h

    # h2b- control cells - 2h /every 5minutes
    #   * 1ug/ml NCS
    #   * anisotropy imaging


    # cumulitivate histogram of intensity vs frequency
    ...

