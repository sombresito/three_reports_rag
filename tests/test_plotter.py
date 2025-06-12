import os
import pytest
matplotlib = pytest.importorskip('matplotlib')
import plotter  # noqa: E402

matplotlib.use('Agg')


def test_team_plot_saving(tmp_path):
    old_dir = plotter.PLOT_DIR
    plotter.PLOT_DIR = str(tmp_path)

    team = "My Team"
    report = [{"status": "passed", "uid": "1", "name": "t"}]

    plotter.plot_trends_for_reports([report], ["uid1"], [team], team_name=team)
    team_dir = os.path.join(plotter.PLOT_DIR, plotter.normalize_collection_name(team))
    assert os.path.isdir(team_dir)
    assert os.path.isfile(os.path.join(team_dir, "trend_uid1.png"))
    assert os.path.isfile(os.path.join(team_dir, "trend_summary.png"))

    plotter.PLOT_DIR = old_dir
