import pytest

from modeldock.catalog import CATALOG, deployment_disk, fits_model, recommend


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


@pytest.mark.parametrize("voice", ["off", "0.6B", "1.7B"])
def test_capacity_modes_reserve_context_and_voice(voice):
    large=recommend(32,25,16,100,preference="质量优先",profile="large",voice=voice)
    long=recommend(32,25,16,100,preference="质量优先",profile="context",voice=voice)
    assert large.model and long.model
    assert large.context==4096 and long.context==16384
    assert long.model.size < large.model.size
    reserve={"off":0,"0.6B":4,"1.7B":7}[voice]
    assert long.model.memory+4+reserve<=16-16*.12


def test_voice_cannot_be_promised_without_gpu_budget():
    assert recommend(32,25,0,100,voice="1.7B").model is None


def test_compressed_catalog_retains_one_27b_family_and_exact_non_mtp_files():
    models = [m for m in CATALOG if m.method == "GSQ + RCO"]
    assert len(models) == 4
    assert {m.family for m in models} == {"Qwen3.8-27B"}
    assert {m.method for m in models} == {"GSQ + RCO"}
    assert {m.quant for m in models} == {"IQ2_XS", "IQ2_S", "IQ3_XXS", "IQ3_S"}
    assert all(m.tag.endswith("-" + m.quant + ".gguf") and "mtp" not in m.tag.casefold() for m in models)
    assert all(m.size < m.memory for m in models)


def test_insufficient_compressed_budget_never_falls_back_to_small_model():
    plan = recommend(8, 6, 0, 100, usage="压缩大模型", preference="质量优先")
    assert plan.model is None
    assert "压缩大模型方案" in plan.reason and "不会自动改成小参数模型" in plan.reason


def test_cpu_compressed_model_requires_deliberate_quality_preference():
    assert recommend(32, 25, 0, 100, usage="压缩大模型").model is None
    plan = recommend(32, 25, 0, 100, usage="压缩大模型", preference="质量优先")
    assert plan.model.family == "Qwen3.8-27B"
    assert "CPU 大模型推理可能很慢" in plan.reason


def test_compressed_speed_selects_lower_bit_variant_of_same_model():
    args = (32, 25, 24, 100)
    quality = recommend(*args, usage="压缩大模型", preference="质量优先")
    speed = recommend(*args, usage="压缩大模型", preference="速度优先")
    assert speed.model.family == quality.model.family
    assert speed.model.memory < quality.model.memory


def test_compressed_choice_does_not_depend_on_catalog_order(monkeypatch):
    import modeldock.catalog as catalog
    before = recommend(32, 25, 16, 100, usage="压缩大模型", preference="质量优先")
    monkeypatch.setattr(catalog, "CATALOG", list(reversed(CATALOG)))
    after = recommend(32, 25, 16, 100, usage="压缩大模型", preference="质量优先")
    assert before.model == after.model


def test_compressed_context_and_voice_joint_budget():
    large = recommend(32, 25, 24, 100, usage="压缩大模型", preference="质量优先", voice="1.7B")
    long = recommend(32, 25, 24, 100, usage="压缩大模型", preference="质量优先", profile="context", voice="1.7B")
    assert large.model.quant == "IQ3_S" and long.model.quant == "IQ2_XS"
    assert long.model.memory + 4 + 7 <= 24 - 24 * .12


def test_compressed_speech_is_not_promised_on_16gb_gpu():
    assert recommend(32, 25, 16, 100, usage="压缩大模型", voice="1.7B").model is None


def test_manual_deployment_budget_includes_context_and_voice():
    model = next(m for m in CATALOG if m.quant == "IQ3_S")
    assert fits_model(model, 32, 25, 16, 100)
    assert not fits_model(model, 32, 25, 16, 100, context=16384)
    assert not fits_model(model, 32, 25, 16, 100, voice="0.6B")
    assert not fits_model(model, 32, 25, 16, 5)


def test_original_default_chat_does_not_silently_change_to_compressed_family():
    assert recommend(64, 50, 24, 100).model.specialty == "通用对话"


def test_compressed_download_and_double_copy_disk_budget():
    models = [m for m in CATALOG if m.method == "GSQ + RCO"]
    assert [m.size for m in models] == [7.9, 8.7, 9.5, 11.0]
    model = models[0]
    enough_for_one = model.size * 1.15 + 1
    assert deployment_disk(model) == model.size * 2.15 + 1
    assert not fits_model(model, 32, 25, 24, enough_for_one)
    assert recommend(32, 25, 24, enough_for_one, usage="压缩大模型").model is None
    assert fits_model(model, 32, 25, 24, deployment_disk(model))


def test_regular_models_keep_existing_disk_budget():
    model = next(m for m in CATALOG if m.tag == "qwen3:0.6b")
    assert deployment_disk(model) == model.size * 1.15 + 1
