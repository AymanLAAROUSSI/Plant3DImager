#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Path calculation functions for circular trajectories and others
"""

import math
import numpy as np
from scipy.spatial import cKDTree
from core.utils import config

def calculate_circle_positions(center=None, radius=None, num_positions=None):
    """
    Calculate positions on a circle in the XY plane
    
    Args:
        center: Tuple (x, y, z) of circle center (default: CENTER_POINT)
        radius: Circle radius (default: CIRCLE_RADIUS)
        num_positions: Number of positions on the circle (default: NUM_POSITIONS)
    
    Returns:
        List of tuples (x, y, z) representing positions on the circle
    """
    # Use default values if not specified
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    positions = []
    for i in range(num_positions):
        # Calculate angle in radians
        angle = 2 * math.pi * i / num_positions
        
        # Calculate x and y coordinates
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2]  # Keep same height
        
        positions.append((x, y, z))
    
    return positions

def find_closest_point_index(positions, reference_point):
    """
    Find the index of the point closest to the reference point
    
    Args:
        positions: List of tuples (x, y, z)
        reference_point: Reference point (x, y, z) or {"x": x, "y": y, "z": z}
    
    Returns:
        Index of the closest point
    """
    # Convert reference point if needed
    if isinstance(reference_point, dict):
        ref_point = (reference_point['x'], reference_point['y'], reference_point['z'])
    else:
        ref_point = reference_point
    
    # Use KDTree for efficient search
    tree = cKDTree(positions)
    _, index = tree.query(ref_point)
    
    return index

def reorder_positions(positions, start_index):
    """
    Reorder the positions list to start from the specified index
    
    Args:
        positions: List of positions
        start_index: Index to start from
    
    Returns:
        Reordered list of positions
    """
    reordered = positions[start_index:] + positions[:start_index]
    return reordered

def plan_circle_path(center=None, radius=None, num_positions=None, start_point=None):
    """
    Plan a complete circular path, starting from the point closest
    to the specified start point
    
    Args:
        center: Circle center (default: CENTER_POINT)
        radius: Circle radius (default: CIRCLE_RADIUS)
        num_positions: Number of positions (default: NUM_POSITIONS)
        start_point: Starting point (default: (0, 0, 0))
        
    Returns:
        List of dictionaries describing the trajectory
    """
    # Use default values if not specified
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    if start_point is None:
        start_point = (0, 0, 0)
    
    # Calculate positions on the circle
    positions = calculate_circle_positions(center, radius, num_positions)
    
    # Find the point closest to the start point
    closest_index = find_closest_point_index(positions, start_point)
    
    # Reorder positions to start from the closest point
    ordered_positions = reorder_positions(positions, closest_index)
    
    # Create trajectory
    path = []
    
    # Add starting point
    path.append({
        "position": start_point,
        "type": "start",
        "comment": "Starting position"
    })
    
    # Add entry point on the circle
    path.append({
        "position": ordered_positions[0],
        "type": "via_point",
        "comment": "Entry point on the circle"
    })
    
    # Add positions on the circle
    for i, pos in enumerate(ordered_positions[1:], 1):
        path.append({
            "position": pos,
            "type": "via_point",
            "comment": f"Position {i}/{num_positions} on the circle"
        })
    
    # Add return to starting point
    path.append({
        "position": start_point,
        "type": "end",
        "comment": "Return to starting position"
    })
    
    return path

def plan_multi_circle_path(center=None, radius=None, num_positions=None, num_circles=1, z_offset=None, start_point=None):
    """
    Plan a path on multiple circles at different heights
    
    Args:
        center: Circle center (default: CENTER_POINT)
        radius: Circle radius (default: CIRCLE_RADIUS)
        num_positions: Number of positions per circle (default: NUM_POSITIONS)
        num_circles: Number of circles (default: 1)
        z_offset: Z offset between circles (default: Z_OFFSET)
        start_point: Starting point (default: (0, 0, 0))
        
    Returns:
        List of dictionaries describing the trajectory
    """
    # Use default values if not specified
    if center is None:
        center = config.CENTER_POINT
    
    if radius is None:
        radius = config.CIRCLE_RADIUS
    
    if num_positions is None:
        num_positions = config.NUM_POSITIONS
    
    if z_offset is None:
        z_offset = config.Z_OFFSET
    
    if start_point is None:
        start_point = (0, 0, 0)
    
    # Create trajectory
    path = []
    
    # Add starting point
    path.append({
        "position": start_point,
        "type": "start",
        "comment": "Starting position"
    })
    
    # For each circle
    for circle_num in range(num_circles):
        # Adjust Z height for this circle
        circle_center = (center[0], center[1], center[2] + (circle_num * z_offset))
        
        # Calculate positions on the circle
        positions = calculate_circle_positions(circle_center, radius, num_positions)
        
        # For the first circle, start from the point closest to the start point
        if circle_num == 0:
            closest_index = find_closest_point_index(positions, start_point)
            positions = reorder_positions(positions, closest_index)
        
        # Add comment for circle start
        circle_height = circle_center[2]
        path.append({
            "position": positions[0],
            "type": "via_point",
            "comment": f"Start of circle {circle_num+1}/{num_circles} at height Z = {circle_height:.3f}"
        })
        
        # Add positions on this circle
        for i, pos in enumerate(positions[1:], 1):
            # Calculate global photo number
            photo_num = (circle_num * num_positions) + i
            
            path.append({
                "position": pos,
                "type": "via_point",
                "comment": f"Position {photo_num}/{num_positions*num_circles} on circle {circle_num+1}"
            })
    
    # Add return to starting point
    path.append({
        "position": start_point,
        "type": "end",
        "comment": "Return to starting position"
    })
    
    return path