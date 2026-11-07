"""Smoke test for the T0.2 skeleton: every layer package is importable."""

import importlib

import pytest

LAYER_PACKAGES = [
    "tmc_attendance",
    "tmc_attendance.domain",
    "tmc_attendance.application",
    "tmc_attendance.adapters.inbound.http",
    "tmc_attendance.adapters.outbound.persistence",
    "tmc_attendance.bootstrap",
]


@pytest.mark.parametrize("name", LAYER_PACKAGES)
def test_layer_package_is_importable(name: str) -> None:
    assert importlib.import_module(name).__name__ == name
