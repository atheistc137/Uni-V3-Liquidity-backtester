from datetime import datetime, timezone
from typing import Union
from web3 import Web3


def get_block_by_timestamp(
    web3: Web3,
    target_time: Union[int, datetime],
    *,
    approx_block_time: float | None = None,
    tolerance_seconds: int = 5,
    max_tries: int = 50,
) -> int:
    """
    Return the first block whose timestamp is ≥ target_time.

    Parameters
    ----------
    web3 : Web3
        Connected Web3 instance.
    target_time : int | datetime
        Desired moment.  If datetime, must be timezone‑aware (UTC preferred).
    approx_block_time : float, optional
        Average seconds per block for the chain (e.g. 13 for Ethereum main‑net,
        2 for Base, 12 for Polygon).  Used to narrow the initial search window.
        If None (default) the full 0‑to‑latest range is searched.
    tolerance_seconds : int, optional
        Acceptable timestamp error before we stop.  Default 5 s.
    max_tries : int, optional
        Hard stop on iterations.  Default 50.

    Returns
    -------
    int
        Block number.

    Raises
    ------
    ValueError
        If the target time is in the future or we cannot converge.
    """

    # 1) normalise target timestamp
    if isinstance(target_time, datetime):
        if target_time.tzinfo is None:
            raise ValueError("datetime must be timezone‑aware (UTC).")
        target_ts = int(target_time.timestamp())
    else:
        target_ts = int(target_time)

    # 2) latest block
    latest_block = web3.eth.get_block("latest")
    latest_num = latest_block.number
    latest_ts = latest_block.timestamp

    if target_ts > latest_ts:
        raise ValueError("Target time is in the future relative to latest block.")

    # 3) quick exit if we're already close enough
    if abs(latest_ts - target_ts) <= tolerance_seconds:
        return latest_num

    # -----------------------------------------------------------------
    # 4) derive initial low / high using approx_block_time  (***new***)
    # -----------------------------------------------------------------
    if approx_block_time and approx_block_time > 0:
        # naive estimate of how many blocks back the target is
        blocks_back = int((latest_ts - target_ts) / approx_block_time)
        guess = latest_num - blocks_back

        # clamp guess into valid range
        guess = max(0, min(guess, latest_num))

        # pick a window around the guess (± 2×blocks_back for safety)
        low = max(0, guess - 2 * blocks_back)
        high = min(latest_num, guess + 2 * blocks_back)

        # ensure window isn’t degenerate
        if low >= high:
            low, high = 0, latest_num
    else:
        low, high = 0, latest_num

    # -----------------------------------------------------------------
    # 5) binary search inside [low, high]
    # -----------------------------------------------------------------
    tries = 0
    while low < high and tries < max_tries:
        mid = (low + high) // 2
        blk_ts = web3.eth.get_block(mid).timestamp

        if blk_ts < target_ts:
            low = mid + 1
        else:
            high = mid

        if abs(blk_ts - target_ts) <= tolerance_seconds:
            return mid

        tries += 1

    if tries >= max_tries:
        raise ValueError("Exceeded maximum iterations; did not converge.")

    return low
