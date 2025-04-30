import logging
import os
from datetime import datetime
from itertools import count
from pathlib import Path

import pandas as pd
from bitcoin.core import CBlockHeader, b2lx
from bitcoin.rpc import JSONRPCError, Proxy
from dotenv import load_dotenv
from pytz import utc

load_dotenv()
logger = logging.getLogger("uvicorn")


def _fetch_data(height: int, proxy: Proxy) -> tuple[dict, dict]:
    h = proxy.getblockhash(height)
    try:
        header = proxy.getblockheader(h)
        stat = proxy._call("getblockstats", b2lx(h))
    except JSONRPCError:
        # Probably a "Can't read undo data from disk" error
        # So we compute the stats manually, long to process but happens rarely

        # CBlock inherits from CBlockHeader, so we can use it as a header
        block = proxy.getblock(h)
        header = block

        stat = {}
        stat["txs"] = len(block.vtx)
        stat["subsidy"] = int(50e8) >> (height // 210000)
        stat["totalfee"] = 0
        for tx in block.vtx:
            if tx.is_coinbase():
                continue
            fee = 0
            for txin in tx.vin:
                prevout = txin.prevout
                prevtx = proxy._call("getrawtransaction", b2lx(prevout.hash), True)
                fee += prevtx["vout"][prevout.n]["value"] * 100_000_000
            fee -= sum(vout.nValue for vout in tx.vout)
            stat["totalfee"] += int(fee)
    return header, stat


def _step(start: int, end: int, proxy: Proxy) -> tuple[list[CBlockHeader], list[dict]]:
    verbose = __name__ == "__main__"
    headers = []
    stats = []
    for height in range(start, end + 1):
        header, stat = _fetch_data(height, proxy)
        headers.append(header)
        stats.append(stat)
        if verbose:
            mined_at = datetime.fromtimestamp(header.nTime, tz=utc)
            print(
                f"Blocks [{start}:{end}] > Block {height} mined at ",
                mined_at.strftime("%Y-%m-%d %H:%M:%S"),
                end="\r",
            )
    if verbose:
        print(f"Blocks [{start}:{end}] > Done." + " " * 50)
    logger.info(f"Blocks [{start}:{end}] > Done.")
    return headers, stats


def sync(step_size: int = 25000) -> None:
    """Update local database with Bitcoin blocks data.

    Arg:
        step_size (int): The number of blocks to fetch in each batch.
    """
    logger.info("Sync initiated.")

    # Retrieve existing data
    data = pd.DataFrame()
    if Path("blocks_data.pkl").exists():
        data = pd.read_pickle("blocks_data.pkl")

    service_url = None
    if not Path("~/.bitcoin/.cookie").expanduser().exists():
        service_url = os.getenv("BITCOIN_RPC_URL")
    proxy = Proxy(service_url=service_url)

    # Make sure we have no forks
    if not data.empty:
        last_hash = data.iloc[-1].hash
        last_height = int(data.index[-1])
        double_check_hash = b2lx(proxy.getblockhash(last_height))
        if last_hash != double_check_hash:
            logger.warning("Fork detected, removing last 5 blocks")
            data = data.drop(data.tail(5).index)

    # Next block height to fetch
    known_blocks = data.shape[0]

    # Fetch data in batches of step_size
    n = proxy.getblockcount()
    for start in range(known_blocks, n + 1, step_size):
        try:
            headers, stats = _step(start, min(start + step_size - 1, n), proxy)
        except BrokenPipeError:
            proxy = Proxy()

        new_data = pd.DataFrame.from_records(
            [
                {
                    "height": height,
                    "hash": b2lx(header.GetHash()),
                    "timestamp": header.nTime,
                    "difficulty": header.difficulty,
                    "txs": stat["txs"],
                    "subsidy": stat["subsidy"],
                    "fees": stat["totalfee"],
                }
                for height, header, stat in zip(count(start), headers, stats)
            ],
            index="height",
        )

        data = pd.concat([data, new_data])
    data.to_pickle("blocks_data.pkl")


if __name__ == "__main__":
    sync()
