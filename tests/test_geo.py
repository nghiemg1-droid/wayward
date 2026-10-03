import pytest

from app.services.geo import distance_m


def test_same_point_is_zero():
    assert distance_m(37.77, -122.41, 37.77, -122.41) == 0


def test_one_degree_of_latitude_is_about_111_km():
    assert distance_m(0, 0, 1, 0) == pytest.approx(111_195, rel=0.001)


def test_new_york_to_los_angeles():
    distance = distance_m(40.7128, -74.0060, 34.0522, -118.2437)
    assert distance == pytest.approx(3_936_000, rel=0.01)


def test_distance_is_symmetric():
    forward = distance_m(37.77, -122.41, 40.71, -74.00)
    backward = distance_m(40.71, -74.00, 37.77, -122.41)
    assert forward == pytest.approx(backward)
