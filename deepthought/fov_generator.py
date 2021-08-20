# Modules
import numpy as np
from entity_clusters import Cluster, Cluster_Group


def optimal_cluster_1(Cluster_Group, fov_lb):
	'''Given a list of Cluster groups, it returns the most optimal cluster group based the comparision scheme  → difference between fov and cluster bounding box dimensions must be minimum. Score = length_difference + breadth_difference. Lesser score is better. '''
	
	#Get averaged cluster bounding box dimensions
	bbox_list = np.array([cluster_group.avg_bbox_dimensions() for cluster_group in Cluster_Group])

	# Unpack
	np_bbox_list = np.array(bbox_list)
	XYs = np_bbox_list.reshape(2,3)
	x_vals, y_vals = np.split(XYs, 2, axis = 0)

	# Take difference
	x_vals = x_vals - float(fov_lb[0])
	y_vals = y_vals - float(fov_lb[1])

	#Get Total residue !!!Attention → Dimensional Reduction
	residue = x_vals + y_vals

	optimal_clustgrp_idx = np.argmin(residue)
	
	return cluster_grouplist[optimal_clustgrp_idx]


def optimal_cluster_2(Cluster_Group, fov_lb, threshold = 0):
	'''Given a list of Cluster groups, it returns the most optimal cluster group based on imaging_optimality() criteria for each cluster in a particular cluster group.

	* threshold - Minimum optimality score for Imaging. '''
	
	count = [] # Number of thresholded optimal clusters in the group
	sum_  = [] # Sum of thresholded optimality scores
	
	thresholder = lambda t: t > threshold 
	
	for i in range(len(Cluster_Group)):
		optimality_scores = np.array([cluster.imaging_optimality(fov_lb) for cluster in Cluster_Group[i].ClusterList])
		optimal_clusters = optimality_scores[thresholder(optimality_scores)]
		count.append(optimal_clusters.size())
		sum.append(np.sum(optimal_clusters))

	weight_count = 1.0
	weight_sum = 1.0

	score = (weight_sum * sum_) + (weight_count * count)
	optimal_clustgrp_idx = np.argmax(score)

	return Cluster_Group[optimal_clustgrp_idx]


def form_cluster_group_sets(full_entity_list, min_size, max_size):
	''' Returns a list of Cluster_Group objects that that are populated with clusters. '''

	#Convert into 'approximate number of clusters' from the passed param 'cluster sizes'
	entity_size = len(entitly_list)
	max_ = entity_size / min_size
	min_ = entity_size / max_size

	cluster_groups = []
	for i in range(min_, max_):
		cluster_groups.append(Cluster_Group(i))
		cluster_group[-1].calc_clusters(full_entity_list)

	return cluster_groups



# Highest Abstraction Functions

def optimal_fov_centres(full_entity_list, min, max, fov_lb):
	''' Generates many clusters groups and returns the FoVs for the "most optimal cluster set".'''
	
	cluster_groups = form_cluster_group_set(full_entitly_list, min, max) #Make 2 to 8 clusters
	optimal_cluster_group = optimal_cluster_1(cluster_groups, fov_lb)
	fov_list = optimal_cluster_group.get_fov_list()
	return fov_list

def fixed_fov_centres(full_entity_list, no_fov, fov_lb):
	''' Returns fixed number of FoV centres. '''

	cluster_group = Cluster_Group(no_fov)
	cluster_group.calc_clusters(full_entity_list)
	fov_list = cluster_group.get_fov_list()
	return fov_list


