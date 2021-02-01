# third-party imports
import pytest

# local imports
from cic_eth.db.util import num_serialize


@pytest.mark.parametrize(
        'n,b',
        [
            (0, b'\x00'),
            (1, b'\x01'),
            (255, b'\xff'),
            (256, b'\x01\x00'),
            (18446744073709551616, b'\x01\x00\x00\x00\x00\x00\x00\x00\x00'),
        ],
        )
def test_num_serialize(n, b):
    assert(num_serialize(n) == b)
