import json
from io import StringIO

from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.cli import main


def test_demo_cli_emits_the_public_report_as_json() -> None:
    output = StringIO()

    exit_code = main(["demo", "--seed", "42"], stdout=output)

    payload = json.loads(output.getvalue())
    assert exit_code == 0
    assert payload == run_synthetic_demo(seed=42).to_dict()
    assert payload["execution_mode"] == "SYNTHETIC_PAPER"
    assert payload["economy"] == "UNAVAILABLE"
    assert payload["profitability_claim"] is False
