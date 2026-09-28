from copy import deepcopy
import pytest
from clean_product.config import load_config
from clean_product.validation import validate_baseline, validate_registries


def test_clean_registries_agree_with_active_baseline():
    cfg=load_config(); validate_baseline(cfg); validate_registries(cfg)


@pytest.mark.parametrize('field,value', [('production_allowed',True),('role','baseline'),('canonical_id','wrong')])
def test_registry_rejects_shadow_identity_or_admission_changes(field,value):
    cfg=deepcopy(load_config()); cfg['models']['model_a_plus_b'][field]=value
    with pytest.raises(ValueError): validate_registries(cfg)
