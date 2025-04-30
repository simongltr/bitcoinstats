import pandas as pd


def get_blocks_data() -> pd.DataFrame:
    """Load the blocks data.

    Returns:
        pd.DataFrame: A DataFrame containing the blocks data.

    """
    data = pd.read_pickle("blocks_data.pkl").reset_index(drop=False)
    data["reward"] = data["subsidy"] + data["fees"]
    data["feepercentage"] = data["fees"] / data["reward"]
    data["work"] = data.difficulty * 0x0100010001
    data["chainwork"] = data["work"].cumsum()
    data["mediantime"] = data["timestamp"].rolling(11, min_periods=1).median()
    data["timedelta"] = data["timestamp"].diff().fillna(600)
    data["supply"] = data["subsidy"].cumsum()
    return data


def get_blocks_data_over_period(
    period: str = "daily",
    hashrate_unit: str = "EH/s",
    btc_unit: str = "btc",
    from_day: str | None = None,
    to_day: str | None = None,
) -> pd.DataFrame:
    """Load the blocks data and add stats over a given period.

    Args:
        period (str): The period to group the data by.
        hashrate_unit (str): The unit to use for the hashrate.
        btc_unit (str): The unit to use for the BTC values.
        from_day (str): The start date of the period.
        to_day (str): The end date of the period.

    Returns:
        pd.DataFrame: A DataFrame containing the blocks data over the given period.

    """
    frequency_labels = {"daily": "D", "monthly": "MS", "yearly": "YS"}
    hashrate_units = {
        "EH/s": 1e18,
        "PH/s": 1e15,
        "TH/s": 1e12,
        "GH/s": 1e9,
        "MH/s": 1e6,
        "KH/s": 1e3,
        "H/s": 1,
    }
    btc_units = {"btc": int(1e8), "sat": 1}

    if period not in frequency_labels:
        msg = f"frequency must be either {' or '.join(frequency_labels.keys())}"
        raise ValueError(msg)
    if hashrate_unit not in hashrate_units:
        msg = f"hashrate_unit must be either {' or '.join(hashrate_units.keys())}"
        raise ValueError(msg)
    if btc_unit not in btc_units:
        msg = f"btc_unit must be either {' or '.join(btc_units.keys())}"
        raise ValueError(msg)

    data = get_blocks_data()
    data["datetime"] = pd.to_datetime(data["timestamp"], unit="s")
    if from_day:
        data = data[data["datetime"] >= from_day]
    if to_day:
        data = data[data["datetime"] <= to_day]

    data = data[data["datetime"] >= "2010"]
    grouped = data.groupby(pd.Grouper(key="datetime", freq=frequency_labels[period]))
    res = grouped.agg(
        {
            "hash": "count",
            "difficulty": "mean",
            "work": "sum",
            "txs": "sum",
            "reward": "sum",
            "subsidy": "sum",
            "fees": "sum",
            "supply": "last",
        }
    )
    res = res.rename(columns={"hash": "nbblocks"})
    res["reward"] /= btc_units[btc_unit]
    res["subsidy"] /= btc_units[btc_unit]
    res["fees"] /= btc_units[btc_unit]
    res["feepercentage"] = res["fees"] / res["reward"]
    res["hashrate"] = (
        res["work"] / grouped.timedelta.sum() / hashrate_units[hashrate_unit]
    )
    res["rewardperexa"] = (
        res["reward"]
        / res["hashrate"]
        * hashrate_units[hashrate_unit]
        / hashrate_units["EH/s"]
    )
    return res


if __name__ == "__main__":
    # Example usage
    res = get_blocks_data_over_period(period="yearly")
    res.to_csv("blocks_data_yearly.csv")
    print("Done")