# standard imports
import calendar
from datetime import datetime, timedelta

# external imports

# local imports
from cic_ussd.time import TimezoneHandler


def test_timezone_handler(load_timezone):
    datetime_time_now = datetime.utcnow()
    epoch_time_now = calendar.timegm(datetime_time_now.utctimetuple())
    expected_time_after_conversion = datetime_time_now + timedelta(hours=3)
    timezone_handler = TimezoneHandler()
    converted_timestamp = timezone_handler.convert(epoch_time_now)
    assert converted_timestamp == expected_time_after_conversion.strftime("%d/%m/%y, %H:%M %p")


