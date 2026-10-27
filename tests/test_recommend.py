import pytest

from modeldock.catalog import recommend


def test_low_memory_refuses_instead_of_overpromising():
    assert recommend(4, 1.5, 0, 200).model is None


def test_low_disk_refuses():
    assert recommend(32, 25, 12, .8).model is None


def test_cpu_balanced_caps_model_size():
    result = recommend(64, 50, 0, 200)
    assert result.model.tag == "qwen3:4b"
    assert "CPU" in result.mode


def test_gpu_reserves_vram_for_desktop():
    result = recommend(32, 20, 8, 200)
    assert result.model.tag == "qwen3:4b"


def test_ram_and_vram_are_not_added():
    result = recommend(128, 110, 6, 200, preference="质量优先")
    assert result.model.memory <= 5


def test_gpu_still_requires_host_memory():
    assert recommend(4, 1.5, 24, 200).model is None


def test_code_usage_selects_code_model():
    assert recommend(32, 20, 12, 200, "代码开发").model.specialty == "代码开发"


def test_speed_preference_chooses_smaller_model():
    args = (32, 20, 16, 200)
    assert recommend(*args, preference="速度优先").model.size < recommend(*args).model.size


@pytest.mark.parametrize("ram,available,vram,disk", [(8, 4, 0, 10), (16, 10, 8, 20), (64, 50, 24, 100)])
def test_selected_model_fits_memory_and_disk(ram, available, vram, disk):
    result = recommend(ram, available, vram, disk)
    assert result.model
    assert result.model.size * 1.15 + 1 <= disk
    assert result.model.memory <= max(vram - max(1, vram * .12), min(ram - max(3, ram * .2), available - 1))
