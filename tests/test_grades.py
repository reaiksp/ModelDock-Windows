"""Two local recommendation sliders preserve demand, intent and user data."""
import pytest
from modeldock.catalog import (CATALOG, COMPRESSION_LEVELS, CONVERSATION_LEVELS,
    context_reserve, deployment_disk, fits_model, recommend)


def plan(level=5, demand=2, vram=96, voice="off", disk=500, preference="质量优先"):
    return recommend(128, 110, vram, disk, "压缩大模型", preference,
                     voice=voice, compression_level=level, conversation_demand=demand)


@pytest.mark.parametrize("level,quant", [(1,"IQ2_XS"),(2,"IQ3_XXS"),(3,"Q4_K_M"),(4,"Q8_0"),(5,"BF16")])
def test_each_precision_level_uses_same_27b_family_and_exact_grade(level, quant):
    result = plan(level)
    assert result.model.quant == quant and result.model.family == "Qwen3.8-27B"
    assert result.compression_level == result.effective_compression_level == level
    assert not result.fallback
    assert result.model.tag.endswith("-" + quant + ".gguf")


def test_legacy_intermediate_quants_are_manual_only_with_new_slider():
    legacy = [m for m in CATALOG if m.quant in {"IQ2_S", "IQ3_S"}]
    assert len(legacy) == 2 and all(m.compression_level == 0 for m in legacy)
    assert recommend(128, 110, 96, 500, "压缩大模型").model.quant == "IQ3_S"
    assert plan(5).model.quant == "BF16"


@pytest.mark.parametrize("demand,context,reserve", [(1,2048,0),(2,4096,0),(3,6144,.75),(4,8192,1.5),(5,10240,2.125)])
def test_conversation_demand_keeps_requested_context(demand, context, reserve):
    result = plan(5, demand)
    assert result.context == context and result.conversation_demand == demand
    assert result.context_reserve == reserve


def test_higher_target_never_recommends_lower_grade_when_resources_unchanged():
    selected = [plan(level, vram=24).effective_compression_level for level in range(1,6)]
    assert selected == [1,2,3,3,3]


def test_less_vram_or_more_context_cannot_raise_grade():
    grades = [plan(vram=v).effective_compression_level or 0 for v in [96,48,32,24,16,12,8]]
    assert grades == sorted(grades, reverse=True)
    grades = [plan(demand=d, vram=24).effective_compression_level or 0 for d in range(1,6)]
    assert grades == sorted(grades, reverse=True)


def test_fallback_is_explicit_and_never_shrinks_context():
    result = plan(5, demand=4, vram=24, voice="1.7B")
    assert result.model.quant == "IQ3_XXS"
    assert result.compression_level == 5 and result.effective_compression_level == 2 and result.fallback
    assert result.context == 8192 and "目标 5 档，推荐 2 档" in result.reason
    assert "对话需求不变" in result.reason
    result = plan(5, demand=5, vram=12)
    assert result.model is None and result.context == 10240 and result.effective_compression_level is None


@pytest.mark.parametrize("voice,reserve", [("off",0),("0.6B",4),("1.7B",7)])
def test_grade_selection_reserves_voice_and_context(voice, reserve):
    result = plan(5, demand=3, vram=48, voice=voice)
    assert result.model.memory + result.context_reserve + reserve <= 48 - 48 * .12


def test_full_precision_requires_real_runtime_and_double_copy_disk_budget():
    full = next(m for m in CATALOG if m.compression_level == 5)
    assert full.quant == "BF16" and full.memory == 54 and full.size == 50.2
    assert plan(5, disk=deployment_disk(full)).effective_compression_level == 5
    assert plan(5, disk=deployment_disk(full)-.01).effective_compression_level == 4
    assert not fits_model(full, 128, 110, 48, 500)
    assert not fits_model(full, 128, 110, 96, 100)


def test_host_ram_voice_and_cpu_preference_are_still_hard_constraints():
    assert recommend(4,1.5,96,500,"压缩大模型",compression_level=5).model is None
    assert recommend(32,6,96,500,"压缩大模型",voice="1.7B",compression_level=5).model is None
    assert plan(vram=0, preference="均衡").model is None
    assert plan(vram=0, preference="质量优先").model.quant == "BF16"


def test_generic_use_ignores_precision_but_applies_conversation_demand():
    result = recommend(128,110,96,500,"代码开发",compression_level=5,conversation_demand=3)
    assert result.model.specialty == "代码开发" and result.context == 6144
    assert result.compression_level is None and result.effective_compression_level is None


@pytest.mark.parametrize("key,value", [("compression_level",0),("compression_level",6),("compression_level",True),("conversation_demand",1.5),("conversation_demand","5")])
def test_invalid_levels_are_not_silently_interpreted(key, value):
    with pytest.raises(ValueError):
        recommend(128,110,96,500,"压缩大模型",**{key:value})
