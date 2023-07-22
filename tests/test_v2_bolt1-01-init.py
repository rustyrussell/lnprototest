from typing import Any

from lnprototest.runner import Runner


def test_v2_init_is_first_msg(runner: Runner, namespaceoverride: Any) -> None:
    """Tests workflow

    runner --- connect ---> ln node
    runner <-- init ------ ln node
    """
    runner.start()

    conn1 = runner.connect(None, connprivkey="03")
    init_msg = conn1.recv_msg()
    assert (
        init_msg.messagetype.number == 16
    ), f"received not an init msg but: {init_msg.to_str()}"
    conn1.send_msg("init", globalfeatures="", features="")
    runner.stop()
