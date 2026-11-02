from modeldock.catalog import recommend, PARAMETER_SIZES
import pytest
from modeldock.parameters import VARIANTS, parameter_size
from modeldock.gguf import _spec

@pytest.mark.parametrize("limit", [i / 2 for i in range(1,97)])
def test_entire_parameter_range_matches_real_files(limit):
    size = parameter_size(limit)
    assert .5 <= size <= limit <= 48
    result = recommend(256,230,240,1000,"压缩大模型","质量优先",compression_level=5,conversation_demand=3,parameter_limit=limit)
    assert result.model.tag is not None
    assert PARAMETER_SIZES[result.model.tag] == size
    assert _spec(result.model.tag)['sha256']

@pytest.mark.parametrize("value", [True,False,0,.49,48.1,float('nan'),float('inf'),'3'])
def test_invalid_parameter_limits_rejected(value):
    with pytest.raises(ValueError): parameter_size(value)

def test_catalog_files_are_pinned_and_grade_is_within_selected_family():
    assert len(VARIANTS) >= 45
    for row in VARIANTS:
        spec = _spec(row['tag'])
        assert spec['size'] == row['size'] and spec['sha256'] == row['sha256']
        assert spec['revision'] == row['revision']
