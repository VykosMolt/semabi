import json

from semabi.eval.oracle import latent_for


def test_latent_declarations_survive_renamed_run_directory(tmp_path):
    run = tmp_path / "copied_experiment_name"
    run.mkdir()
    (run / "hidden_domain.json").write_text(json.dumps({"name": "climbing"}))

    assert latent_for(run) == {("Route", "closed")}
