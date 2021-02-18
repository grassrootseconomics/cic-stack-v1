# standard imports
import os
import logging

# third-party imports
import pytest
import confini

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
logg = logging.getLogger(__file__)


@pytest.fixture(scope='session')
def load_config():
    config_dir = os.path.join(root_dir, '.config/test')
    conf = confini.Config(config_dir, 'CICTEST')
    conf.process()
    logg.debug('config {}'.format(conf))
    return conf
