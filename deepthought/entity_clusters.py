import numpy as np
from sklearn.cluster import KMeans
from operator import add


class Cluster():
	''' Represents a group of entities that are clustered together.'''
	
	def __init__(self, full_entity_list, cluster_centroid_list):
		self.EntityList = []
		self.Bbox = []
		self.scan_entities((full_entity_list, cluster_centroid_list)) #Call method
		self.Bbox = get_bbox()

	def scan_entities(self, full_entity_list, cluster_centroid_list):
		''' Takes in the complete entity list and selects and saves the entity objects in the cluster. '''

		# Do Object Scan based on list position index
		for entity_idx in cluster_centroid_list:
			self.EntityList.append(full_entity_list[entity_idx])


	def get_bbox(self):
		''' Returns a pair of *min* and *max* [x,x] and [y,y] coordinate sets of the rectangular bounding box of the cluster. This function assumes that the entities have a 2D-rectangular bounding box. '''

		#(min_row, min_col, max_row, max_col)
		x_min_list = [entity.properties.regionprops.bbox[0] for entity in self.EntityList]
		x_max_list = [entity.properties.regionprops.bbox[2] for entity in self.EntityList]

		y_min_list = [entity.properties.regionprops.bbox[1] for entity in self.EntityList]
		y_max_list = [entity.properties.regionprops.bbox[3] for entity in self.EntityList]

		x_left = min(x_min_list)
		x_right = max(x_max_list)
		y_top = min(y_min_list)
		y_down = max(y_max_list)

		return [[x_left, x_right], [y_top, y_down]]

	def get_bbox_centre(self):
		''' Returns the fov centre coordinates for the cluster. Effectively - it is the centre of the bounding box of the cluster. '''

		median_x = float(self.Bbox[0][1] + self.Bbox[0][0]) / 2.0
		median_y = float(self.Bbox[1][1] + self.Bbox[1][0]) / 2.0

		return [median_x, median_y]


	def imaging_optimality(self, fov_lb):
		''' Returns an optimality score of the cluster based on the size of the field of view. Returns '0' if the cluster is bigger than the FoV, and normalised score, if the image has empty area.  0 <= Score <= 1: More is better.'''

		fov_area = fov_lb[0] * fov_lb[1]
		abs_error = fov_area - self.bbox_area()
		
		if abs_error < 0: # The cluster image signal will be clipped
			return 0.0
		else: # More error → less score
			return 1.0 - (float(abs_error) / float(fov_area))

	def get_bbox_area(self):
		''' Returns the bounding box area. Attention: Uses the memoed value of Bbox.'''
		
		length, breadth = self.bbox_dimensions()
		bbox_area = length * breadth
		return bbox_area

	def get_bbox_dimensions(self):
		''' Returns the dimensions of the cluster bounding box. '''
		
		length = abs(self.Bbox[0][1] - self.Bbox[0][0])
		breadth = abs(self.Bbox[1][1] - self.Bbox[1][0])
		return [length, breadth]


class Cluster_Group():
	''' Stores a group of cluster objects that encompass a complete entity list.'''

	
	def __init__(self, requested_size = 2):
		''' Passed cluster parameters. '''
		
		self. ClusterList #List of Clusters
		self.Size #Number of clusters
		self.ReqSize #Requested Size
		self.Size = requested_size
		self.ReqSize = requested_size


	def calc_clusters(self, full_entity_list):
		'''Runs a clustering algorithm based on Cluster_Group parameters and populates the ClusterList '''

		all_centroids = np.array([entity.xy for entity in full_entity_list])

		kmeans = sklearn.cluster.KMeans(n_clusters = self.ReqSize, init = 'k-means++', random_state = 0).fit(all_centroids)
		
		# Read Clustering outputs
		labels = kmeans.labels_
		self.ClusterCenters = kmeans.cluster_centers_
		self.Size = len(self.ClusterCenters)

		#Create Centroid Groups
		centroid_groups = []
		for i in range(self.Size):
			centroid_groups.append(labels.where(labels == i))

		# Populate ClusterList
		for i in range(len(centroid_groups)):
			new_cluster = Cluster(full_entity_list, centroid_groups[i])
			self.ClusterList.append(new_cluster)

	def avg_xy_dimensions(self):
		''' Returns the average bounding box dimesnions based on average axes ranges of the clusters in the cluster group. [[Depreciated]] [[Probably not correct way to do it]]'''

		x_left, x_right, y_top, y_down = 0.0 
		for i in range(self.Size):
			xx, yy = self.ClusterList[i].get_bbox()
			x_l,x_b = xx
			y_t, y_d = yy
			
			x_left = x_left + x_l
			x_right = x_right + x_r
			y_top = y_top + y_t
			y_down = y_right + y_d

		return [abs(x_right - x_left)/self.Size, abs(y_top - y_down)/self.Size]

	def avg_bbox_dimensions(self):
		''' Returns the average bounding box dimesnsions of the clusters in the cluster group.'''

		counter = [0.0,0.0]
		for i in range(self.Size):
			map(add, counter, self.ClusterList.get_bbox_dimensions())

		return [abs(x_right - x_left)/self.Size, abs(y_top - y_down)/self.Size]


	def get_fov_list(self):
		''' Returns the Centroids of the Clusters that were obtained via k-means clustering. Two ways to do it. ↓'''
		
		return self.ClusterCenters
		#return [cluster.get_bbox_centre() for cluster in self.ClusterList]

	def imaging_optimality(self, fov_lb):
		''' Returns an optimality score of the cluster based on the size of the field of view. Returns '0' if the cluster is bigger than the FoV, and normalised score, if the image has empty area.  0 <= Score <= 1: More is better.'''

		fov_area = fov_lb[0] * fov_lb[1]
		abs_error = fov_area - self.bbox_area()
		
		if abs_error < 0: # The cluster image signal will be clipped
			return 0.0
		else: # More error → less score
			return 1.0 - (float(abs_error) / float(fov_area))

