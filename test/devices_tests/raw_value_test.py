"""Unit test for RawValue objects."""
import pytest
from xknx import XKNX
from xknx.devices import RawValue
from xknx.dpt import DPTArray, DPTBinary
from xknx.telegram import GroupAddress, Telegram
from xknx.telegram.apci import GroupValueRead, GroupValueResponse, GroupValueWrite


@pytest.mark.asyncio
class TestRawValue:
    """Test class for RawValue objects."""

    @pytest.mark.parametrize(
        "payload_length,raw_payload,expected_state",
        [
            # DPT-14 values are according to ETS group monitor values
            (
                0,
                DPTBinary(0),
                0,
            ),
            (
                0,
                DPTBinary(True),
                1,
            ),
            (
                0,
                DPTBinary(45),
                45,
            ),
            (
                1,
                DPTArray((0x6B,)),
                107,
            ),
            (
                1,
                DPTArray((0xFC,)),
                252,
            ),
            (
                2,
                DPTArray((0x6C, 0x95)),
                27797,
            ),
        ],
    )
    async def test_payloads(
        self,
        payload_length,
        raw_payload,
        expected_state,
    ):
        """Test raw value types."""
        xknx = XKNX()
        raw_value = RawValue(
            xknx,
            "Test",
            payload_length=payload_length,
            group_address="1/2/3",
        )
        telegram = Telegram(
            destination_address=GroupAddress("1/2/3"),
            payload=GroupValueWrite(value=raw_payload),
        )
        await raw_value.process(telegram)
        assert raw_value.resolve_state() == expected_state
        assert raw_value.last_telegram == telegram

    #
    # TEST RESPOND
    #
    async def test_respond_to_read(self):
        """Test respond_to_read function."""
        xknx = XKNX()
        responding = RawValue(
            xknx,
            "TestSensor1",
            2,
            group_address="1/1/1",
            respond_to_read=True,
        )
        non_responding = RawValue(
            xknx,
            "TestSensor2",
            2,
            group_address="1/1/1",
            respond_to_read=False,
        )
        responding_multiple = RawValue(
            xknx,
            "TestSensor3",
            2,
            group_address=["1/1/1", "3/3/3"],
            group_address_state="2/2/2",
            respond_to_read=True,
        )
        #  set initial payload of RawValue
        responding.remote_value.value = 256
        non_responding.remote_value.value = 256
        responding_multiple.remote_value.value = 256

        read_telegram = Telegram(
            destination_address=GroupAddress("1/1/1"), payload=GroupValueRead()
        )
        # verify no response when respond is False
        await non_responding.process(read_telegram)
        assert xknx.telegrams.qsize() == 0

        # verify response when respond is True
        await responding.process(read_telegram)
        assert xknx.telegrams.qsize() == 1
        response = xknx.telegrams.get_nowait()
        assert response == Telegram(
            destination_address=GroupAddress("1/1/1"),
            payload=GroupValueResponse(DPTArray((0x01, 0x00))),
        )
        # verify no response when GroupValueRead request is not for group_address
        await responding_multiple.process(read_telegram)
        assert xknx.telegrams.qsize() == 1
        response = xknx.telegrams.get_nowait()
        assert response == Telegram(
            destination_address=GroupAddress("1/1/1"),
            payload=GroupValueResponse(DPTArray((0x01, 0x00))),
        )
        await responding_multiple.process(
            Telegram(
                destination_address=GroupAddress("2/2/2"), payload=GroupValueRead()
            )
        )
        await responding_multiple.process(
            Telegram(
                destination_address=GroupAddress("3/3/3"), payload=GroupValueRead()
            )
        )
        assert xknx.telegrams.qsize() == 0

    #
    # TEST SET
    #
    async def test_set_0(self):
        """Test set with raw value."""
        xknx = XKNX()
        raw_value = RawValue(xknx, "TestSensor", 0, group_address="1/2/3")
        await raw_value.set(True)
        assert xknx.telegrams.qsize() == 1

        telegram = xknx.telegrams.get_nowait()
        assert telegram == Telegram(
            destination_address=GroupAddress("1/2/3"),
            payload=GroupValueWrite(DPTBinary(True)),
        )

    async def test_set_1(self):
        """Test set with raw value."""
        xknx = XKNX()
        raw_value = RawValue(xknx, "TestSensor", 1, group_address="1/2/3")
        await raw_value.set(75)
        assert xknx.telegrams.qsize() == 1

        telegram = xknx.telegrams.get_nowait()
        assert telegram == Telegram(
            destination_address=GroupAddress("1/2/3"),
            payload=GroupValueWrite(DPTArray((0x4B,))),
        )

    def test_string(self):
        """Test RawValue string representation."""

        xknx = XKNX()
        value = RawValue(xknx, "Raw", 1, group_address="1/2/3")
        value.remote_value.value = 4
        assert (
            str(value)
            == '<RawValue name="Raw" addresses=<1/2/3, None, [], 4 /> value=4/>'
        )
