import numpy as np
import pytest
import ruckig


def parameters(dofs):
    inp = ruckig.InputParameter(dofs)
    inp.current_position = [0.0] * dofs
    inp.current_velocity = [0.0] * dofs
    inp.current_acceleration = [0.0] * dofs
    inp.target_position = [(-1) ** i * (0.2 + i * 0.05) for i in range(dofs)]
    inp.target_velocity = [0.0] * dofs
    inp.target_acceleration = [0.0] * dofs
    inp.max_velocity = [1.0] * dofs
    inp.max_acceleration = [2.0] * dofs
    inp.max_jerk = [4.0] * dofs
    return inp


@pytest.mark.parametrize('dofs', [1, 3, 14])
def test_offline_trajectory_limits_and_endpoint(dofs):
    inp = parameters(dofs)
    trajectory = ruckig.Trajectory(dofs)
    result = ruckig.Ruckig(dofs, 0.005).calculate(inp, trajectory)
    assert result in (ruckig.Result.Working, ruckig.Result.Finished)
    assert trajectory.duration > 0
    samples = np.array([trajectory.at_time(t) for t in np.linspace(0, trajectory.duration, 1001)])
    assert np.isfinite(samples).all()
    assert np.max(np.abs(samples[:, 1, :])) <= 1.0 + 1e-9
    assert np.max(np.abs(samples[:, 2, :])) <= 2.0 + 1e-9
    jerk = np.diff(samples[:, 2, :], axis=0) / (trajectory.duration / 1000)
    assert np.max(np.abs(jerk)) <= 4.0 + 1e-7
    np.testing.assert_allclose(samples[-1, 0, :], inp.target_position, atol=1e-9)
    np.testing.assert_allclose(samples[-1, 1:, :], 0.0, atol=1e-9)


def test_online_trajectory_reaches_target():
    inp = parameters(3)
    output = ruckig.OutputParameter(3)
    otg = ruckig.Ruckig(3, 0.005)
    target = list(inp.target_position)
    for _ in range(10000):
        result = otg.update(inp, output)
        assert result in (ruckig.Result.Working, ruckig.Result.Finished)
        assert max(abs(v) for v in output.new_velocity) <= 1.0 + 1e-9
        assert max(abs(a) for a in output.new_acceleration) <= 2.0 + 1e-9
        if result == ruckig.Result.Finished:
            break
        output.pass_to_input(inp)
    else:
        pytest.fail('Online trajectory did not finish')
    np.testing.assert_allclose(output.new_position, target, atol=1e-9)
