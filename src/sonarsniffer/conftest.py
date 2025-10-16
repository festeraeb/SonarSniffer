import pytest
from pathlib import Path


@pytest.fixture(scope='session')
def rsd_path():
    # Prefer sample RSD in repository if present
    p = Path('sample code') / 'RSD_Studio_Modular_Full' / 'Sonar000.RSD'
    if p.exists():
        return str(p)
    # fallback to any .RSD file in repository
    for fp in Path('.').rglob('*.RSD'):
        return str(fp)
    pytest.skip('No RSD sample found for tests')


@pytest.fixture(scope='session')
def out_dir(tmp_path_factory):
    p = tmp_path_factory.mktemp('test_out')
    return str(p)


@pytest.fixture
def parser_name():
    return 'Garmin RSD'


@pytest.fixture
def parser_class():
    # Lazy import to avoid heavy deps during collection
    from engine_glue import run_engine
    return run_engine


@pytest.fixture
def file_path(rsd_path):
    return rsd_path
