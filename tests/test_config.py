
from config.config import DataTransformationConfig

def test_config_integrity():
    config = DataTransformationConfig()
    
    # 1. Check Bins
    assert len(config.trans_amt_bins) > 1
    assert config.trans_amt_bins == sorted(config.trans_amt_bins), "Bins must be sorted!"
    
    # 2. Check Required Columns
    assert 'uid1' in config.uid_cols
    assert 'card1' in config.card_cols
