"""Check the released wheel without extra APK packages, NumPy or network."""
import ruckig

assert ruckig.__version__ == '0.19.4'
otg = ruckig.Ruckig(1, 0.01)
inp = ruckig.InputParameter(1)
inp.current_position = [0.0]
inp.target_position = [1.0]
inp.max_velocity = [1.0]
inp.max_acceleration = [2.0]
inp.max_jerk = [4.0]
trajectory = ruckig.Trajectory(1)
assert otg.calculate(inp, trajectory) in (ruckig.Result.Working, ruckig.Result.Finished)
assert abs(trajectory.at_time(trajectory.duration)[0][0] - 1.0) < 1e-9
print('PASS: clean musl Python installation and trajectory calculation')
