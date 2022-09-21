"""
Lightning network Speck utils, is a collection of methods that helps to
work with some concept of lightning network RFC
"""


class LightningUtils:
    """
    Main implementation class of the lightning networks utils.

    The implementation class contains only static methods that
    apply the rules specified in the lightning network RFC.
    """

    @staticmethod
    def derive_short_channel_id(block_height: int, tx_idx: int, tx_output) -> str:
        """
        Derive the short channel id with the specified
        parameters, and return the result as string.

        RFC definition: https://github.com/lightning/bolts/blob/93909f67f6a48ee3f155a6224c182e612dd5f187/07-routing-gossip.md#definition-of-short_channel_id

        The short_channel_id is the unique description of the funding transaction. It is constructed as follows:
            - the most significant 3 bytes: indicating the block height
            - the next 3 bytes: indicating the transaction index within the block
            - the least significant 2 bytes: indicating the output index that pays to the channel.

        e.g: a short_channel_id might be written as 539268x845x1, indicating a channel on the
        output 1 of the transaction at index 845 of the block at height 539268.

        block_height: str
            Block height.
        tx_idx: int
            Transaction index inside the block.
        tx_output: int
            Output index inside the transaction.
        """
        return f"{block_height}x{tx_idx}x{tx_output}"
