# standard imports


# external imports
import pytest
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.balance import (BalancesHandler,
                                      get_balances,
                                      get_cached_adjusted_balance,
                                      get_cached_display_balance)
from cic_ussd.account.transaction import from_wei
from cic_ussd.account.chain import Chain
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.error import CachedDataNotFoundError

# test imports
from tests.helpers.accounts import blockchain_address


def test_async_get_balances(activated_account,
                            celery_session_worker,
                            load_chain_spec,
                            load_config,
                            mock_async_balance_api_query):
    blockchain_address = activated_account.blockchain_address
    chain_str = Chain.spec.__str__()
    token_symbol = load_config.get('TEST_TOKEN_SYMBOL')
    get_balances(blockchain_address, chain_str, token_symbol, asynchronous=True)
    assert mock_async_balance_api_query.get('address') == blockchain_address
    assert mock_async_balance_api_query.get('token_symbol') == token_symbol


def test_sync_get_balances(activated_account,
                           balances,
                           celery_session_worker,
                           load_chain_spec,
                           load_config,
                           mock_sync_balance_api_query):
    blockchain_address = activated_account.blockchain_address
    chain_str = Chain.spec.__str__()
    token_symbol = load_config.get('TEST_TOKEN_SYMBOL')
    res = get_balances(blockchain_address, chain_str, token_symbol, asynchronous=False)
    assert res == balances


@pytest.mark.parametrize('balance_incoming, balance_network, balance_outgoing, display_balance', [
    (0, 50000000, 0, 50.00),
    (5000000, 89000000, 67000000, 27.00)
])
def test_balances(activated_account,
                  balance_incoming,
                  balance_network,
                  balance_outgoing,
                  cache_balances,
                  cache_default_token_data,
                  load_chain_spec,
                  display_balance,
                  token_symbol):
    balances = {
        'address': activated_account.blockchain_address,
        'converters': [],
        'balance_network': balance_network,
        'balance_outgoing': balance_outgoing,
        'balance_incoming': balance_incoming
    }
    balances = BalancesHandler(balances=balances, decimals=6)
    chain_str = Chain.spec.__str__()
    assert balances.display_balance() == display_balance
    assert balances.spendable_balance(chain_str, token_symbol) == from_wei(
        decimals=6, value=(balance_network - balance_outgoing))


def test_get_cached_available_balance(activated_account,
                                      balances,
                                      cache_balances,
                                      cache_default_token_data,
                                      load_chain_spec,
                                      token_symbol):
    identifier = [bytes.fromhex(activated_account.blockchain_address), token_symbol.encode('utf-8')]
    cached_display_balance = get_cached_display_balance(6, identifier)
    balances = BalancesHandler(balances=balances[0], decimals=6)
    display_balance = balances.display_balance()
    assert cached_display_balance == display_balance
    address = blockchain_address()
    with pytest.raises(CachedDataNotFoundError) as error:
        identifier = [bytes.fromhex(address), token_symbol.encode('utf-8')]
        cached_display_balance = get_cached_display_balance(6, identifier)
        assert cached_display_balance is None
    assert str(error.value) == 'No cached display balance.'


def test_get_cached_adjusted_balance(activated_account, cache_adjusted_balances, token_symbol):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    balances_identifier = [identifier, token_symbol.encode('utf-8')]
    key = cache_data_key(balances_identifier, MetadataPointer.BALANCES_ADJUSTED)
    adjusted_balances = get_cached_data(key)
    assert get_cached_adjusted_balance(balances_identifier) == adjusted_balances


def test_get_account_tokens_balance(activated_account,
                                    cache_token_data_list,
                                    celery_session_worker,
                                    load_chain_spec,
                                    load_config,
                                    mock_async_balance_api_query,
                                    token_symbol):
    blockchain_address = activated_account.blockchain_address
    chain_str = Chain.spec.__str__()
    get_balances(blockchain_address, chain_str, token_symbol, asynchronous=True)
    assert mock_async_balance_api_query.get('address') == blockchain_address
    assert mock_async_balance_api_query.get('token_symbol') == token_symbol
