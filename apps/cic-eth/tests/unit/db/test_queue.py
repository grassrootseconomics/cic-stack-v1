# standard imports
import logging

# third-party imports
import pytest

# local imports
from cic_eth.db import Otx
from cic_eth.db.error import TxStateChangeError

logg = logging.getLogger()


# Check that invalid transitions throw exceptions
# sent
def test_db_queue_states(
        init_database,
        ):

    session = init_database

    # these values are completely arbitary
    tx_hash = '0xF182DFA3AD48723E7E222FE7B4C2C44C23CD4D7FF413E8999DFA15ECE53F'
    address = '0x38C5559D6EDDDA1F705D3AB1A664CA1B397EB119'
    signed_tx = '0xA5866A5383249AE843546BDA46235A1CA1614F538FB486140693C2EF1956FC53213F6AEF0F99F44D7103871AF3A12B126DCF9BFB7AF11143FAB3ECE2B452EE35D1320C4C7C6F999C8DF4EB09E729715B573F6672ED852547F552C4AE99D17DCD14C810'
    o = Otx(
            nonce=42,
            address=address[2:],
            tx_hash=tx_hash[2:],
            signed_tx=signed_tx[2:],
            )
    session.add(o)
    session.commit()

    o.sent(session=session)
    session.commit()

    # send after sent is ok
    o.sent(session=session)
    session.commit()

    o.sendfail(session=session)
    session.commit()

    with pytest.raises(TxStateChangeError):
        o.sendfail(session=session)

    o.sent(session=session)
    session.commit()

    o.minefail(1234, session=session)
    session.commit()

    with pytest.raises(TxStateChangeError):
        o.sent(session=session)
