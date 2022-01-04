# standard imports
import datetime
import json
import logging
import time
from typing import List, Union

# external imports
from cic_types.condiments import MetadataPointer
from cic_types.models.person import get_contact_data_from_vcard
from tinydb.table import Document

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.translation import translation_for

logg = logging.getLogger(__file__)


def latest_input(user_input: str) -> str:
    """
    :param user_input:
    :return:
    """
    return user_input.split('*')[-1]


def parse_person_metadata(cached_metadata: str, display_key: str, preferred_language: str) -> str:
    """This function extracts person metadata formatted to suite display on the ussd interface.
    :param cached_metadata: Person metadata JSON str.
    :type cached_metadata: str
    :param display_key: Path to an entry in menu data in translation files.
    :type display_key: str
    :param preferred_language: An account's set preferred language.
    :type preferred_language: str
    :return:
    :rtype:
    """
    user_metadata = json.loads(cached_metadata)
    contact_data = get_contact_data_from_vcard(user_metadata.get('vcard'))
    full_name = f'{contact_data.get("given")} {contact_data.get("family")}'
    date_of_birth = user_metadata.get('date_of_birth')
    year_of_birth = date_of_birth.get('year')
    present_year = datetime.datetime.now().year
    age = present_year - year_of_birth
    gender = user_metadata.get('gender')
    products = ', '.join(user_metadata.get('products'))
    location = user_metadata.get('location').get('area_name')

    return translation_for(
        key=display_key,
        preferred_language=preferred_language,
        full_name=full_name,
        age=age,
        gender=gender,
        location=location,
        products=products
    )


def resume_last_ussd_session(last_state: str) -> Document:
    """
    :param last_state:
    :type last_state:
    :return:
    :rtype:
    """
    # TODO [Philip]: This can be cleaned further
    non_reusable_states = [
        'account_creation_prompt',
        'exit',
        'exit_invalid_pin',
        'exit_invalid_new_pin',
        'exit_invalid_recipient',
        'exit_invalid_request',
        'exit_pin_blocked',
        'exit_pin_mismatch',
        'exit_successful_transaction'
    ]
    if last_state in non_reusable_states:
        return UssdMenu.find_by_name('start')
    return UssdMenu.find_by_name(last_state)


def ussd_menu_list(fallback: str, menu_list: list, split: int = 3) -> List[str]:
    """
    :param fallback:
    :type fallback:
    :param menu_list:
    :type menu_list:
    :param split:
    :type split:
    :return:
    :rtype:
    """
    menu_list_sets = [menu_list[item:item + split] for item in range(0, len(menu_list), split)]
    menu_list_reprs = []
    for i in range(split):
        try:
            menu_list_reprs.append(''.join(f'{list_set_item}\n' for list_set_item in menu_list_sets[i]).rstrip('\n'))
        except IndexError:
            menu_list_reprs.append(fallback)
    return menu_list_reprs


def wait_for_cache(identifier: Union[list, bytes], resource_name: str, salt: MetadataPointer, interval: int = 1, max_retry: int = 5):
    """
    :param identifier:
    :type identifier:
    :param interval:
    :type interval:
    :param resource_name:
    :type resource_name:
    :param salt:
    :type salt:
    :param max_retry:
    :type max_retry:
    :return:
    :rtype:
    """
    key = cache_data_key(identifier=identifier, salt=salt)
    resource = get_cached_data(key)
    counter = 0
    while resource is None:
        logg.debug(f'Waiting for: {resource_name} at: {key}. Checking after: {interval} ...')
        time.sleep(interval)
        counter += 1
        resource = get_cached_data(key)
        if resource is not None:
            logg.debug(f'{resource_name} now available.')
            break
        else:
            if counter == max_retry:
                logg.debug(f'Could not find: {resource_name} within: {max_retry}')
                break


def wait_for_session_data(resource_name: str, session_data_key: str, ussd_session: dict, interval: int = 1, max_retry: int = 5):
    """
    :param interval:
    :type interval:
    :param resource_name:
    :type resource_name:
    :param session_data_key:
    :type session_data_key:
    :param ussd_session:
    :type ussd_session:
    :param max_retry:
    :type max_retry:
    :return:
    :rtype:
    """
    data = ussd_session.get('data')
    data_poller = 0
    while not data:
        logg.debug(f'Waiting for data object on ussd session: {ussd_session.get("external_session_id")}')
        logg.debug(f'Data poller at: {data_poller}. Checking again after: {interval} secs...')
        time.sleep(interval)
        data_poller += 1
        if data:
            logg.debug(f'Data object found, proceeding to poll for: {session_data_key}')
            break
    if data:
        session_data_poller = 0
        session_data = data.get(session_data_key)
        while not session_data_key:
            logg.debug(
                f'Session data poller at: {data_poller} with max retry at: {max_retry}. Checking again after: {interval} secs...')
            time.sleep(interval)
            session_data_poller += 1

            if session_data:
                logg.debug(f'{resource_name} now available.')
                break

            elif session_data_poller >= max_retry:
                logg.debug(f'Could not find data object within: {max_retry}')
