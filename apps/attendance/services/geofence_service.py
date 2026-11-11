"""Geofence calculation service using Haversine great-circle distance."""

import math
from decimal import Decimal


def haversine_distance_meters(
    lat1: float | Decimal,
    lon1: float | Decimal,
    lat2: float | Decimal,
    lon2: float | Decimal,
) -> float:
    """Calculate the great circle distance in meters between two points on the Earth."""
    r = 6371000.0  # Earth radius in meters

    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return r * c


def validate_geofence(
    user_lat: float | Decimal,
    user_lon: float | Decimal,
    center_lat: float | Decimal | None,
    center_lon: float | Decimal | None,
    allowed_radius_meters: int = 100,
) -> tuple[bool, float]:
    """Validate whether user coordinates are within allowable campus geofence.

    Returns:
        tuple of (is_within_geofence, distance_in_meters)
    """
    if center_lat is None or center_lon is None:
        # If no geofence perimeter configured, allow by default with 0m distance
        return True, 0.0

    distance = haversine_distance_meters(user_lat, user_lon, center_lat, center_lon)
    is_valid = distance <= allowed_radius_meters
    return is_valid, round(distance, 2)
