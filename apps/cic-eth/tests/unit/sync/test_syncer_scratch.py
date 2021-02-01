# third-party imports
import pytest

# local imports
from cic_eth.db.models.sync import BlockchainSync
from cic_eth.sync.backend import SyncerBackend


def test_scratch(
    init_database,
        ):

    with pytest.raises(ValueError):
        s = SyncerBackend('Testchain:666', 13)

    syncer = SyncerBackend.live('Testchain:666', 13)

    s = SyncerBackend('Testchain:666', syncer.object_id)



def test_live(
    init_database,
    ):

    s = SyncerBackend.live('Testchain:666', 13)

    s.connect()
    assert s.db_object.target() == None
    s.disconnect()

    assert s.get() == (13, 0)

    s.set(14, 1)
    assert s.get() == (14, 1)


def test_resume(
    init_database,
    ):

    live = SyncerBackend.live('Testchain:666', 13)
    live.set(13, 2)

    resumes = SyncerBackend.resume('Testchain:666', 26)

    assert len(resumes) == 1
    resume = resumes[0]

    assert resume.get() == (13, 2)

    resume.set(13, 4)
    assert resume.get() == (13, 4)
    assert resume.start() == (13, 2)
    assert resume.target() == 26


def test_unsynced(
    init_database,
    ):

    live = SyncerBackend.live('Testchain:666', 13)
    live.set(13, 2)

    resumes = SyncerBackend.resume('Testchain:666', 26)
    live = SyncerBackend.live('Testchain:666', 26)
    resumes[0].set(18, 12)

    resumes = SyncerBackend.resume('Testchain:666', 42)

    assert len(resumes) == 2

    assert resumes[0].start() == (13, 2)
    assert resumes[0].get() == (18, 12)
    assert resumes[0].target() == 26

    assert resumes[1].start() == (26, 0)
    assert resumes[1].get() == (26, 0)
    assert resumes[1].target() == 42
