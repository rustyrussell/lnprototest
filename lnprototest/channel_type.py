# Support for channel_types.
from typing import Callable
from .bitfield import has_bit, bitfield, both_have_feature
from .event import Event, ResolvableStr
from .runner import Runner


# BOLT-channel_types #2:
# Channel types are an explicit enumeration: for convenience of future
# definitions they reuse even feature bits, but they are not an
# arbitrary combination (they represent the persistent features which
# affect the channel operation).
#
# The currently defined types are:
#   - no features (no bits set)
#   - `option_static_remotekey` (bit 12)
#   - `option_anchor_outputs` and `option_static_remotekey` (bits 20 and 12)
#   - `option_anchors_zero_fee_htlc_tx` and `option_static_remotekey` (bits 22 and 12)
class ChannelType(object):
    def __init__(self, bitfield: str) -> None:
        self.bitfield = bitfield

    STATIC_REMOTEKEY = 12
    ANCHOR_OUTPUTS = 20
    ANCHORS_ZERO_FEE = 22

    @classmethod
    def nofeatures(cls) -> 'ChannelType':
        return cls(bitfield())

    @classmethod
    def static_remotekey(cls) -> 'ChannelType':
        return cls(bitfield(cls.STATIC_REMOTEKEY))

    @classmethod
    def anchor_outputs(cls) -> 'ChannelType':
        return cls(bitfield(cls.STATIC_REMOTEKEY, cls.ANCHOR_OUTPUTS))

    @classmethod
    def anchor_outputs_zfee(cls) -> 'ChannelType':
        return cls(bitfield(cls.STATIC_REMOTEKEY, cls.ANCHORS_ZERO_FEE))

    # BOLT-channel_types #2:
    # Both peers:
    #  - if `channel_type` was present in both `open_channel` and `accept_channel`):
    #    - this is the `channel_type` (they must be equal, required above)
    #  - otherwise:
    #    - if `option_anchors_zero_fee_htlc_tx` was negotiated:
    #      - the `channel_type` is `option_anchors_zero_fee_htlc_tx` and `option_static_remotekey` (bits 22 and 12)
    #    - otherwise, if `option_anchor_outputs` was negotiated:
    #      - the `channel_type` is `option_anchor_outputs` and `option_static_remotekey` (bits 20 and 12)
    #    - otherwise, if `option_static_remotekey` was negotiated:
    #      - the `channel_type` is `option_static_remotekey` (bit 12)
    #    - otherwise:
    #      - the `channel_type` is empty
    #  - MUST use that `channel_type` for all commitment transactions.
    @staticmethod
    def default_channel_type(a: str, b: str) -> 'ChannelType':
        if both_have_feature(ChannelType.ANCHORS_ZERO_FEE, a, b):
            return ChannelType.anchor_outputs_zfee()
        elif both_have_feature(ChannelType.ANCHOR_OUTPUTS, a, b):
            return ChannelType.anchor_outputs()
        elif both_have_feature(ChannelType.STATIC_REMOTEKEY, a, b):
            return ChannelType.static_remotekey()
        else:
            return ChannelType.nofeatures()

    @staticmethod
    def resolve(open_channel: ResolvableStr,
                accept_channel: ResolvableStr,
                local_features: ResolvableStr,
                remote_features: ResolvableStr) -> Callable[['Runner', 'Event', str], 'ChannelType']:
        def _resolve(runner: Runner, event: Event, fieldname: str) -> ChannelType:
            openmsg = event.resolve_arg('open_channel', runner, open_channel)
            acceptmsg = event.resolve_arg('accept_channel', runner, accept_channel)

            opentlvs = openmsg.get('tlvs', {})
            accepttlvs = acceptmsg.get('tlvs', {})
            if 'channel_type' in opentlvs and 'channel_type' in accepttlvs:
                return ChannelType(accepttlvs['channel_type']['type'])

            return ChannelType.default_channel_type(event.resolve_arg('local_features', runner, local_features),
                                                    event.resolve_arg('remote_features', runner, remote_features))

        return _resolve

    def has_static_remotekey(self) -> bool:
        return has_bit(self.bitfield, self.STATIC_REMOTEKEY)

    def has_anchor_outputs(self) -> bool:
        return has_bit(self.bitfield, self.ANCHOR_OUTPUTS)

    def has_anchor_outputs_zerro_fee_htlc_tx(self) -> bool:
        return has_bit(self.bitfield, self.ANCHORS_ZERO_FEE)
