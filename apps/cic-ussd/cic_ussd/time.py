# standard imports
import datetime

# external imports
from backports.zoneinfo import ZoneInfo

# local imports


class TimezoneHandler:
    timezone = None

    def convert(self, timestamp: str):
        timestamp_format = "%d/%m/%y, %H:%M %p"
        converted_timestamp = datetime.datetime.fromtimestamp(int(timestamp)).astimezone(ZoneInfo(self.timezone))
        return converted_timestamp.strftime(timestamp_format)
