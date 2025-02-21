"""
Microscope control adapted to biological entity observation.

This module provides the technical implementation for observing biological
entities using microscopy hardware.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from .biology import BiologicalEntity, BiologicalSample, EntityType
from .observation import (
    EntityObservation,
    MicroscopyMethod,
    ObservationSet,
    QualityMetrics,
    TechnicalDetails,
    TechnicalParameters
)

from frames import (
    ExperimentContext, 
    AcquisitionFrame, 
    Position, 
    Channel, 
    MicroscopeState,
    AnalysisPipeline, 
    ObjectDetectionProcessor, 
    NuclearDetector
)
from ophyd import Signal
from .sample import ConfocalDish
from .perception import (
    PerceptionSpace,
    BiologicalEntity as PerceptionBiologicalEntity,
    BiologicalEntityType as PerceptionBiologicalEntityType,
    SpatialContext,
    TemporalContext
)
from .perception_adapters import (
    NuclearPerceptionMethod,
    CellPerceptionMethod
)

# Configure logging
logger = logging.getLogger(__name__)

# Hardware state constants
OBJECTIVE_STATES = {
    4: 100,  # 100x magnification
    3: 60,   # 60x magnification
    2: 40,   # 40x magnification
    1: 20,   # 20x magnification
    0: 10    # 10x magnification
}

class MicroscopyError(Exception):
    """Base class for microscopy-related errors."""
    pass

class HardwareError(MicroscopyError):
    """Error related to hardware operations."""
    pass

class FocusError(MicroscopyError):
    """Error related to focus operations."""
    pass

class AcquisitionError(MicroscopyError):
    """Error related to image acquisition."""
    pass

@asynccontextmanager
async def hardware_operation(hw, operation: str):
    """Context manager for safe hardware operations."""
    try:
        logger.debug(f"Starting {operation}")
        yield
    except Exception as e:
        logger.error(f"Error during {operation}: {str(e)}")
        raise HardwareError(f"Failed to {operation}: {str(e)}") from e
    finally:
        logger.debug(f"Completed {operation}")

class AdaptiveMicroscopyOperations:
    """Microscope operations organized around biological entities"""
    
    def __init__(self, hardware):
        self.hw = hardware
        self.current_sample: Optional[BiologicalSample] = None
        self.observation_method = MicroscopyMethod()
        self.perception_space = PerceptionSpace()
        
        # Initialize perception methods
        self.perception_space.add_perception_method(
            NuclearPerceptionMethod(self.hw.nuclear_detector)
        )
        self.perception_space.add_perception_method(
            CellPerceptionMethod(self.hw.cell_detector)
        )
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def load_sample(self, sample: BiologicalSample) -> None:
        """Load a biological sample for observation"""
        self.current_sample = sample
        
    async def configure_observation(self, parameters: TechnicalParameters) -> None:
        """Configure observation parameters"""
        self.observation_method.configure(parameters)
    
    async def observe_entities(self,
                             entity_types: Optional[List[EntityType]] = None
                             ) -> ObservationSet:
        """Observe entities in current sample"""
        if self.current_sample is None:
            raise ValueError("No sample loaded")
            
        # Create new observation set
        observation_set = ObservationSet(timestamp=datetime.now())
        
        # Get entities to observe
        entities = []
        if entity_types:
            for type_ in entity_types:
                entities.extend(self.current_sample.get_entities(type_))
        else:
            entities = self.current_sample.get_entities()
            
        # Observe each entity
        for entity in entities:
            observation = await self._observe_entity(entity)
            if observation:
                observation_set.add_observation(observation)
                
        return observation_set
    
    async def _observe_entity(self, 
                            entity: BiologicalEntity
                            ) -> Optional[EntityObservation]:
        """Make observation of specific entity"""
        # Get last known position
        if entity.observation_history:
            last_obs = entity.observation_history[-1]
            position = last_obs.position
        else:
            position = None
            
        if position is None:
            # Need to find entity first
            position = await self._find_entity(entity)
            if position is None:
                return None
                
        # Move to position
        await self._move_to_position(position)
        
        # Acquire images
        images = {}
        exposures = {}
        for channel, config in self.observation_method.parameters.channels.items():
            # Configure channel
            await self._configure_channel(channel, config)
            
            # Acquire image
            exposure = config['exposure_time']
            image = await self._acquire_image(exposure)
            
            images[channel] = image
            exposures[channel] = exposure
            
        # Calculate quality metrics
        quality = self._calculate_quality_metrics(images)
        
        # Create technical details
        technical_details = TechnicalDetails(
            raw_data=images,
            parameters=self.observation_method.parameters,
            quality=quality
        )
        
        # Extract morphology if possible
        morphology = self._extract_morphology(images)
        
        # Create observation
        observation = EntityObservation(
            entity_id=entity.entity_id,
            timestamp=datetime.now(),
            position=position,
            morphology=morphology,
            intensities={ch: np.mean(img) for ch, img in images.items()},
            exposures=exposures,
            quality_metrics=quality.__dict__,
            metadata={}
        )
        
        return observation
    
    async def _find_entity(self,
                          entity: BiologicalEntity
                          ) -> Optional[Tuple[float, float, float]]:
        """Find entity in sample"""
        # Implementation for entity search
        try:
            # Get current position and generate search grid
            current_pos = await plan_stubs.rd(self.hw.stage)
            grid = self.hw.generate_grid(*current_pos, num=3)
            
            best_position = None
            max_entity_count = 0
            
            # Setup observation parameters
            channel = Channel(
                name="brightfield",
                exposure=await plan_stubs.rd(self.hw.cam.exposure)
            )
            
            # Search grid points
            for point in grid.midpoints():
                position = Position(x=point['x'], y=point['y'], z=0)
                
                # Make observations
                entities = await self._observe_position(position, channel)
                
                # Filter by type and confidence
                relevant_entities = [
                    e for e in entities
                    if e.characteristics.entity_type == entity.entity_type
                    and e.confidence.detection_confidence >= 0.7
                ]
                
                if len(relevant_entities) > max_entity_count:
                    max_entity_count = len(relevant_entities)
                    best_position = position
            
            # Move to best position if criteria met
            if max_entity_count >= 5 and best_position:
                async with hardware_operation(self.hw, f"move to best position {best_position}"):
                    await plan_stubs.mv(self.hw.stage, best_position.x, best_position.y)
                return best_position
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding entity: {str(e)}")
            raise MicroscopyError("Failed to find entity") from e

    async def _move_to_position(self,
                               position: Tuple[float, float, float]
                               ) -> None:
        """Move microscope to position"""
        async with hardware_operation(self.hw, f"move to position {position}"):
            await plan_stubs.mv(self.hw.stage, position[0], position[1])
            await plan_stubs.mv(self.hw.z, position[2])
        
    async def _configure_channel(self,
                               channel: str,
                               config: Dict
                               ) -> None:
        """Configure microscope for channel"""
        async with hardware_operation(self.hw, f"configure channel {channel}"):
            await plan_stubs.mv(self.hw.ch, channel)
            await plan_stubs.mv(self.hw.cam.exposure, config['exposure_time'])
        
    async def _acquire_image(self, exposure_time: float) -> np.ndarray:
        """Acquire image with given exposure"""
        async with hardware_operation(self.hw, f"acquire image with exposure {exposure_time}"):
            await self.hw.snap_image_and_other_readings_too()
            return await plan_stubs.rd(self.hw.cam)
        
    def _calculate_quality_metrics(self,
                                 images: Dict[str, np.ndarray]
                                 ) -> QualityMetrics:
        """Calculate quality metrics for images"""
        # Simple implementation of quality metrics
        primary_image = list(images.values())[0]
        
        # Calculate SNR
        signal = np.mean(primary_image)
        noise = np.std(primary_image)
        snr = signal / noise if noise > 0 else 0
        
        # Calculate focus score using gradient
        grad_y = np.gradient(primary_image)[0]
        grad_x = np.gradient(primary_image)[1]
        focus = np.mean(np.sqrt(grad_x**2 + grad_y**2))
        
        # Estimate motion blur
        motion = np.mean(np.abs(grad_x)) / (np.mean(np.abs(grad_y)) + 1e-6)
        motion = abs(1 - motion)
        
        # Estimate bleaching
        bleaching = 0.0  # Would need temporal data
        
        return QualityMetrics(
            signal_to_noise=snr,
            focus_score=focus,
            motion_blur=motion,
            bleaching_estimate=bleaching
        )
        
    def _extract_morphology(self,
                          images: Dict[str, np.ndarray]
                          ) -> Optional[Morphology]:
        """Extract morphology from images"""
        # Implementation for morphology extraction
        pass

    async def _observe_position(self, 
                              position: Position,
                              channel: Channel) -> List[PerceptionBiologicalEntity]:
        """Make observations at a specific position."""
        async with hardware_operation(self.hw, f"observe position {position}"):
            # Acquire image
            await self.hw.snap_image_and_other_readings_too()
            image = await plan_stubs.rd(self.hw.cam)
            
            if image is None or image.size == 0:
                raise MicroscopyError("Failed to acquire valid image data")
            
            # Create perception context
            context = await self._create_perception_context(position, channel)
            context['image'] = image
            
            # Make observations
            return self.perception_space.observe(context)

    async def _create_perception_context(self, 
                                       position: Position,
                                       channel: Channel) -> Dict:
        """Create context for perception methods."""
        async with hardware_operation(self.hw, "get microscope state"):
            return {
                'pixel_size': self.hw.get_pixel_size(),
                'magnification': self.hw.get_magnification(),
                'binning': self.hw.get_binning(),
                'channel': channel.name,
                'exposure': channel.exposure,
                'x_position': position.x,
                'y_position': position.y,
                'z_position': position.z,
                'timestamp': datetime.now()
            }

class MicroscopyOperations:
    """Core microscopy operations implementing common workflows."""
    
    def __init__(self, hardware: MicroscopeHardware):
        self.hw = hardware
        self._focus_monitor = None
        self.experiment = ExperimentContext()
        
        # Setup analysis pipeline with nuclear detector
        self.pipeline = AnalysisPipeline()
        self.pipeline.add_processor(ObjectDetectionProcessor(NuclearDetector()))
        self.experiment.pipeline = self.pipeline
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def _create_microscope_state(self) -> MicroscopeState:
        """Create microscope state with current settings."""
        async with hardware_operation(self.hw, "get microscope state"):
            objective_state = int(self.hw._mmc.getProperty("Objective", "State"))
            magnification = OBJECTIVE_STATES.get(objective_state, 60)  # Default to 60x if unknown
            binning = int(self.hw._mmc.getProperty("left_port", "Binning")[0])
            
            return MicroscopeState(
                pixel_size=self.hw.get_pixel_size(),
                magnification=magnification,
                binning=binning
            )

    async def _acquire_frame_with_metadata(self, 
                                         position: Position,
                                         channel: Channel) -> AcquisitionFrame:
        """Acquire a frame with full metadata."""
        async with hardware_operation(self.hw, f"acquire frame at {position} in {channel.name}"):
            # Acquire image
            await self.hw.snap_image_and_other_readings_too()
            img = await plan_stubs.rd(self.hw.cam)
            
            if img is None or img.size == 0:
                raise AcquisitionError("Failed to acquire valid image data")
            
            # Create frame with metadata
            frame = AcquisitionFrame(
                image=img,
                position=position,
                channel=channel,
                microscope_settings=await self._create_microscope_state()
            )
            
            return frame

    async def _analyze_position(self, 
                              point: dict,
                              channel: Channel) -> Tuple[int, Position]:
        """Analyze a single position for objects of interest."""
        try:
            # Move to position and focus
            async with hardware_operation(self.hw, f"move to position {point}"):
                await plan_stubs.mv(self.hw.stage, point["x"], point["y"])
                await self.find_sample_plane()
                
                # Get Z position
                z = await plan_stubs.rd(self.hw.z)
                position = Position(x=point["x"], y=point["y"], z=z)
            
            # Acquire and analyze frame
            frame = await self._acquire_frame_with_metadata(position, channel)
            frame_id = await self.experiment.add_frame(frame)
            analysis = self.experiment.get_analysis(frame_id)
            
            return len(analysis.detected_objects) if analysis else 0, position
            
        except Exception as e:
            self.logger.error(f"Error analyzing position {point}: {str(e)}")
            return 0, Position(x=point["x"], y=point["y"], z=0)

    async def find_region_of_interest(self, threshold: float = 5) -> bool:
        """Find region of interest based on nuclear detection."""
        try:
            # Get current position and generate search grid
            current_pos = await plan_stubs.rd(self.hw.stage)
            grid = self.hw.generate_grid(*current_pos, num=3)
            
            max_count = 0
            best_pos = current_pos
            channel = Channel(
                name="brightfield",
                exposure=await plan_stubs.rd(self.hw.cam.exposure)
            )
            
            # Switch to brightfield for nuclear detection
            async with hardware_operation(self.hw, "switch to brightfield"):
                await plan_stubs.mv(self.hw.ch, channel.name)
            
            # Search grid points
            for point in grid.midpoints():
                count, pos = await self._analyze_position(point, channel)
                if count > max_count:
                    max_count = count
                    best_pos = (pos.x, pos.y)
            
            # Move to best position if threshold met
            if max_count > threshold:
                async with hardware_operation(self.hw, f"move to best position {best_pos}"):
                    await plan_stubs.mv(self.hw.stage, *best_pos)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error finding region of interest: {str(e)}")
            raise MicroscopyError("Failed to find region of interest") from e

    async def acquire_frame(self, 
                          coords: Tuple[float, float], 
                          channel_name: str) -> AcquisitionFrame:
        """Acquire a single frame with proper metadata."""
        try:
            # Create channel configuration
            channel = Channel(
                name=channel_name,
                exposure=await plan_stubs.rd(self.hw.cam.exposure)
            )
            
            # Create position
            z = await plan_stubs.rd(self.hw.z)
            position = Position(x=coords[0], y=coords[1], z=z)
            
            # Acquire frame
            frame = await self._acquire_frame_with_metadata(position, channel)
            frame_id = await self.experiment.add_frame(frame)
            
            return self.experiment.get_frame(frame_id)
            
        except Exception as e:
            self.logger.error(f"Error acquiring frame at {coords}: {str(e)}")
            raise AcquisitionError(f"Failed to acquire frame at {coords}") from e

    async def find_sample_plane(self):
        """Find the sample plane using coarse then fine focus."""
        try:
            # Initial coarse focus using brightfield
            async with hardware_operation(self.hw, "switch to brightfield"):
                await plan_stubs.mv(self.hw.ch, "brightfield")
            
            # Perform focus sweeps
            async with hardware_operation(self.hw, "focus sweep"):
                await self._coarse_focus_sweep()
                await self._fine_focus_sweep()
                
        except Exception as e:
            self.logger.error(f"Error finding sample plane: {str(e)}")
            raise FocusError("Failed to find sample plane") from e

    async def _coarse_focus_sweep(self, range_um: float = 100, 
                                 steps: int = 10):
        """Perform coarse focus sweep."""
        current_z = await plan_stubs.rd(self.hw.z)
        z_positions = np.linspace(current_z - range_um/2, 
                                current_z + range_um/2, 
                                steps)
        
        best_score = -np.inf
        best_z = current_z
        
        for z in z_positions:
            async with hardware_operation(self.hw, f"move to z position {z}"):
                await plan_stubs.mv(self.hw.z, z)
            score = await self._calculate_focus_score()
            if score > best_score:
                best_score = score
                best_z = z
                
        async with hardware_operation(self.hw, f"move to best z position {best_z}"):
            await plan_stubs.mv(self.hw.z, best_z)
        return best_z

    async def _fine_focus_sweep(self, range_um: float = 10, 
                               steps: int = 20):
        """Perform fine focus sweep around current position."""
        current_z = await plan_stubs.rd(self.hw.z)
        z_positions = np.linspace(current_z - range_um/2, 
                                current_z + range_um/2, 
                                steps)
        
        scores = []
        for z in z_positions:
            async with hardware_operation(self.hw, f"move to z position {z}"):
                await plan_stubs.mv(self.hw.z, z)
            score = await self._calculate_focus_score()
            scores.append((z, score))
            
        best_z = max(scores, key=lambda x: x[1])[0]
        async with hardware_operation(self.hw, f"move to best z position {best_z}"):
            await plan_stubs.mv(self.hw.z, best_z)
        return best_z

    async def _calculate_focus_score(self) -> float:
        """Calculate focus score using Shannon entropy of DCT."""
        async with hardware_operation(self.hw, "acquire image for focus score"):
            await self.hw.snap_image_and_other_readings_too()
            img = await plan_stubs.rd(self.hw.cam)
            return float(shannon_dct(img))

    async def create_focus_map(self, positions: List[Tuple[float, float]]):
        """Create focus map for multiple positions."""
        focus_map = {}
        for x, y in positions:
            async with hardware_operation(self.hw, f"move to position ({x}, {y})"):
                await plan_stubs.mv(self.hw.stage, x, y)
            await self.find_sample_plane()
            z = await plan_stubs.rd(self.hw.z)
            focus_map[(x, y)] = z
        return focus_map

    async def mark_position(self, label: str = None) -> Dict:
        """Mark current position for later revisiting."""
        x, y = await plan_stubs.rd(self.hw.stage)
        z = await plan_stubs.rd(self.hw.z)
        position = {
            'x': x, 'y': y, 'z': z,
            'label': label,
            'timestamp': utils.time.time()
        }
        return position

    async def revisit_position(self, position: Dict):
        """Move to a previously marked position."""
        async with hardware_operation(self.hw, f"move to position {position}"):
            await plan_stubs.mv(
                self.hw.stage, position['x'], position['y']
            )
            await plan_stubs.mv(self.hw.z, position['z'])

    async def tile_region(self, center: Tuple[float, float], 
                         size: Tuple[float, float], 
                         overlap: float = 0.1):
        """Create tiled acquisition of a region."""
        fov_width = self.hw.estimate_axial_length()
        tile_width = fov_width * (1 - overlap)
        
        nx = int(np.ceil(size[0] / tile_width))
        ny = int(np.ceil(size[1] / tile_width))
        
        x_start = center[0] - size[0]/2
        y_start = center[1] - size[1]/2
        
        positions = []
        for i in range(nx):
            for j in range(ny):
                x = x_start + i * tile_width
                y = y_start + j * tile_width
                positions.append((x, y))
        
        return positions

    async def optimize_exposure(self, target_intensity: float = 0.5):
        """Optimize exposure time for current channel."""
        async with hardware_operation(self.hw, "optimize exposure"):
            await self.hw.auto_exposure()

    async def create_illumination_correction(self, channel: str):
        """Create flat-field correction for a channel."""
        # Store current position
        orig_pos = await self.mark_position()
        
        # Move to multiple positions and collect background
        positions = await self.tile_region(
            (orig_pos['x'], orig_pos['y']), 
            (100, 100)
        )
        
        backgrounds = []
        for pos in positions:
            async with hardware_operation(self.hw, f"move to position {pos}"):
                await plan_stubs.mv(self.hw.stage, *pos)
            await self.hw.snap_image_and_other_readings_too(channel)
            img = await plan_stubs.rd(self.hw.cam)
            backgrounds.append(img)
            
        correction = np.median(backgrounds, axis=0)
        
        # Return to original position
        async with hardware_operation(self.hw, f"move to original position {orig_pos}"):
            await self.revisit_position(orig_pos)
        return correction

    async def _analyze_roi_score(self) -> float:
        """Calculate region of interest score."""
        async with hardware_operation(self.hw, "acquire image for ROI score"):
            await self.hw.snap_image_and_other_readings_too()
            img = await plan_stubs.rd(self.hw.cam)
            # Simple variance-based scoring
            return float(np.var(img))

class Microscope:
    """Main microscope interface combining hardware and operations."""
    
    def __init__(self, mmc):
        self.hardware = MicroscopeHardware(mmc)
        self.operations = MicroscopyOperations(self.hardware)
        self.adaptive_operations = AdaptiveMicroscopyOperations(self.hardware)
        
    # Convenience methods
    async def find_sample(self):
        """Quick helper to find and focus on sample."""
        async with hardware_operation(self.hardware, "find sample"):
            await self.operations.find_sample_plane()
            await self.operations.find_region_of_interest()
        
    async def start_timelapse(self, channels: List[str], 
                             duration_minutes: float, 
                             interval_seconds: float):
        """Start a multi-channel timelapse acquisition."""
        num_timepoints = int(duration_minutes * 60 / interval_seconds)
        await self.operations.time_series_acquisition(
            channels, num_timepoints, interval_seconds
        )

    async def scan_region(self, size_um: Tuple[float, float]):
        """Scan a region around current position."""
        current_pos = await plan_stubs.rd(self.hardware.stage)
        positions = await self.operations.tile_region(
            current_pos, size_um
        )
        focus_map = await self.operations.create_focus_map(positions)
        
        for pos in positions:
            async with hardware_operation(self.hardware, f"move to position {pos}"):
                await self.operations.revisit_position({
                    'x': pos[0], 'y': pos[1], 
                    'z': focus_map[pos]
                })
            await self.hardware.snap_image_and_other_readings_too()

    async def multi_channel_acquisition(self, channels: List[str], 
                                      auto_expose: bool = True):
        """Acquire images from multiple channels."""
        results = {}
        for channel in channels:
            async with hardware_operation(self.hardware, f"acquire image in {channel}"):
                await plan_stubs.mv(self.hardware.ch, channel)
                if auto_expose:
                    await self.hardware.auto_exposure()
                await self.hardware.snap_image_and_other_readings_too()
                img = await plan_stubs.rd(self.hardware.cam)
                results[channel] = img
        return results

    async def time_series_acquisition(self, channels: List[str], 
                                    num_timepoints: int, 
                                    interval: float):
        """Acquire time series data across multiple channels."""
        results = []
        for t in range(num_timepoints):
            timepoint_data = {
                'timestamp': utils.time.time(),
                'channels': await self.multi_channel_acquisition(channels)
            }
            results.append(timepoint_data)
            
            if t < num_timepoints - 1:
                await plan_stubs.sleep(interval)
        return results

    async def find_and_track_entities(self,
                                    entity_type: BiologicalEntityType,
                                    duration_minutes: float) -> List[BiologicalEntity]:
        """Find and track specific biological entities."""
        # First find a good region
        found = await self.adaptive_operations.find_region_of_interest(
            target_type=entity_type,
            min_confidence=0.7
        )
        
        if not found:
            raise MicroscopyError(f"Could not find region with {entity_type}")
            
        # Track entities
        return await self.adaptive_operations.track_entities(
            entity_type=entity_type,
            duration_minutes=duration_minutes
        )
        
    async def analyze_tissue_structure(self,
                                     region_size: Tuple[float, float]
                                     ) -> Dict[str, List[BiologicalEntity]]:
        """Analyze tissue structure by observing multiple entity types."""
        return await self.adaptive_operations.analyze_spatial_relationships(
            region_size=region_size,
            entity_types=[
                BiologicalEntityType.CELL,
                BiologicalEntityType.NUCLEUS,
                BiologicalEntityType.ORGANELLE
            ]
        )
