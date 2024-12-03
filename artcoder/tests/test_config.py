# tests/test_config.py

import os
import json
import pytest
from artcoder.config import Config

@pytest.fixture
def temp_config():
    config = Config()
    yield config
    # Cleanup
    if os.path.exists(config.config_file):
        os.remove(config.config_file)

def test_config_initialization(temp_config):
    assert temp_config.get('credentials_path') == './credentials.json'
    assert temp_config.get('active_spreadsheet_id') is None
    assert temp_config.get('spreadsheet_name') == 'Patient Records'

def test_config_set_and_get(temp_config):
    temp_config.set('test_key', 'test_value')
    assert temp_config.get('test_key') == 'test_value'

def test_config_persistence(temp_config):
    temp_config.set('test_key', 'test_value')
    
    # Create new config instance to test persistence
    new_config = Config()
    assert new_config.get('test_key') == 'test_value'

def test_invalid_config_file_handling(temp_config):
    # Write invalid JSON
    with open(temp_config.config_file, 'w') as f:
        f.write('invalid json')
    
    # New config should load default values
    new_config = Config()
    assert new_config.get('credentials_path') == './credentials.json'
