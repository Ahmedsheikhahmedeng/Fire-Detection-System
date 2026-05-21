import pytest

from app.services.spatial_context_service import (
    haversine_km,
    spatial_context_service,
)


def test_haversine_same_point_is_zero():
    distance = haversine_km(38.4, 27.1, 38.4, 27.1)

    assert distance == pytest.approx(0.0, abs=0.001)


def test_haversine_nearby_point_is_small_distance():
    distance = haversine_km(38.4, 27.1, 38.401, 27.101)

    assert distance < 1.0


def test_spatial_context_excludes_same_hotspot_string_int_id():
    current = {
        "hotspot_id": 645,
        "latitude": 38.4,
        "longitude": 27.1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": "645",
            "latitude": 38.4,
            "longitude": 27.1,
            "acq_date": "2025-08-01",
            "acq_time": "1230",
            "frp": 100,
        }
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 0
    assert result["nearby_max_frp_2km_24h"] == 0.0
    assert result["nearby_mean_frp_2km_24h"] == 0.0


def test_spatial_context_counts_nearby_hotspot_in_2km_24h():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": 2,
            "latitude": 38.401,
            "longitude": 27.101,
            "acq_date": "2025-08-01",
            "acq_time": "1200",
            "frp": 80,
        }
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 1
    assert result["nearby_max_frp_2km_24h"] == 80.0
    assert result["nearby_mean_frp_2km_24h"] == 80.0

    assert result["nearby_count_5km_48h"] == 1
    assert result["nearby_count_10km_72h"] == 1


def test_spatial_context_ignores_old_hotspot_outside_time_window():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": 2,
            "latitude": 38.401,
            "longitude": 27.101,
            "acq_date": "2025-07-25",
            "acq_time": "1200",
            "frp": 80,
        }
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 0
    assert result["nearby_count_5km_48h"] == 0
    assert result["nearby_count_10km_72h"] == 0


def test_spatial_context_ignores_far_hotspot_outside_radius():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": 2,
            "latitude": 39.4,
            "longitude": 28.1,
            "acq_date": "2025-08-01",
            "acq_time": "1200",
            "frp": 80,
        }
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 0
    assert result["nearby_count_5km_48h"] == 0
    assert result["nearby_count_10km_72h"] == 0


def test_spatial_context_skips_broken_history_row_without_crashing():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": 2,
            "latitude": "bad-latitude",
            "longitude": 27.101,
            "acq_date": "2025-08-01",
            "acq_time": "1200",
            "frp": 80,
        },
        {
            "hotspot_id": 3,
            "latitude": 38.401,
            "longitude": 27.101,
            "acq_date": "2025-08-01",
            "acq_time": "1200",
            "frp": 60,
        },
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 1
    assert result["nearby_max_frp_2km_24h"] == 60.0


def test_spatial_context_accepts_hotspot_datetime_field():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
        "hotspot_datetime": "2025-08-01T12:30:00",
        "frp": 50,
    }

    history = [
        {
            "hotspot_id": 2,
            "latitude": 38.401,
            "longitude": 27.101,
            "hotspot_datetime": "2025-08-01T12:00:00",
            "frp": 80,
        }
    ]

    result = spatial_context_service.compute_nearby_context(
        current_hotspot=current,
        history_hotspots=history,
    )

    assert result["nearby_count_2km_24h"] == 1
    assert result["nearby_max_frp_2km_24h"] == 80.0


def test_spatial_context_missing_coordinates_raises_clear_error():
    current = {
        "hotspot_id": 1,
        "acq_date": "2025-08-01",
        "acq_time": "1230",
    }

    with pytest.raises(Exception):
        spatial_context_service.compute_nearby_context(
            current_hotspot=current,
            history_hotspots=[],
        )


def test_spatial_context_missing_datetime_raises_clear_error():
    current = {
        "hotspot_id": 1,
        "latitude": 38.4,
        "longitude": 27.1,
    }

    with pytest.raises(Exception):
        spatial_context_service.compute_nearby_context(
            current_hotspot=current,
            history_hotspots=[],
        )
