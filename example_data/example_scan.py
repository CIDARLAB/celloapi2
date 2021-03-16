from itertools import combinations
from celloapi2 import CelloQuery, CelloResult

# Set our directory variables. If you have a different OS then Linux you need
# to input a valid Windows path.
in_dir = "/home/jackson/cello/input"
out_dir = "/home/jackson/cello/output"
v_file = "and.v"
options = "options.csv"
# Calculate number of inputs into the Circuit.
signal_input = 2

# We want to try every e-coli chassis.
chassis_name = ["Eco1C1G1T1", "Eco1C2G2T2", "Eco2C1G3T1"]

best_score = 0
best_chassis = None
best_input_signals = None
for chassis in chassis_name:
    in_ucf = f"{chassis}.UCF.json"
    input_sensor_file = f"{chassis}.input.json"
    output_device_file = f"{chassis}.output.json"
    q = CelloQuery(
        input_directory=in_dir,
        output_directory=out_dir,
        verilog_file=v_file,
        compiler_options=options,
        input_ucf=in_ucf,
        input_sensors=input_sensor_file,
        output_device=output_device_file,
        logging=True,
    )
    signals = q.get_input_signals()
    signal_pairing = list(combinations(signals, signal_input))
    for signal_set in signal_pairing:
        signal_set = list(signal_set)
        q.set_input_signals(signal_set)
        q.get_results()
        try:
            res = CelloResult(results_dir=out_dir)
            if res.circuit_score > best_score:
                best_score = res.circuit_score
                best_chassis = chassis
                best_input_signals = signal_set
        except:
            pass
        q.reset_input_signals()
    print("-----")
print(f"Best Score: {best_score}")
print(f"Best Chassis: {best_chassis}")
print(f"Best Input Signals: {best_input_signals}")
