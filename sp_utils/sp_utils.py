from datetime import datetime, timedelta


def get_last_sunday(date: datetime | None = None, day_delta: int = 7):
    if not date:
        date = datetime.now()
    delta = date.isocalendar().weekday + day_delta
    last_sunday = date - timedelta(days=delta)
    return last_sunday


def chunk_asins(asins: str | list, chunk_size: int = 18) -> list:
    """
    Helper function to group a string of ASINs into lists of 18 ASINs.

    Args:
        asins(str | list): a list of asins, or a string of space separated strings representing ASINS.
        chunk_size(int): How many ASINs per chunk (default = 18)

    Returns:
        clean_asins(list): a list of strings representing `chunk_size` number of ASINs, separated by space
    """
    asins_list = asins.split() if isinstance(asins, str) else asins
    clean_asins = []
    for chunk in range(0, len(asins_list), chunk_size):
        asins_str = asins_list[chunk : chunk + chunk_size]
        clean_asins.append(" ".join(asins_str))
    return clean_asins


def convert_date_to_isoformat(date_raw: str | datetime) -> str:
    if isinstance(date_raw, datetime):
        return date_raw.isoformat()
    elif isinstance(date_raw, str):
        date_format = "%Y-%m-%dT%H:%M:%S" if "T" in date_raw else "%Y-%m-%d"
        date_clean = datetime.strptime(date_raw, date_format)
        return date_clean.isoformat()
