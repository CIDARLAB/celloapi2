# Cello API 2
CelloAPI2 is python interface for interacting with [Cellov2](https://github.com/CIDARLAB/Cello-v2), a CAD Tool for designing and scoring Genetic Circuits.

Currently, this works by wrapping interactions with a Docker container in a number of user-friendly Python classes.

## Usage Examples
This is an example of attempting to determine the best AND circuit possible in an E. Coli Chassis.

```
from itertools import combinations
from celloapi2 import CelloQuery, CelloResult

# Set our directory variables. If you have a Windows based
# operating system you need to input window based paths.
in_dir = '/home/jackson/cello/input'
out_dir = '/home/jackson/cello/output'
v_file = 'and.v'
options = 'options.csv'
# Calculate number of inputs into the Circuit.
signal_input = 2

# We want to try every e-coli chassis.
chassis_name = ['Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1']

best_score = 0
best_chassis = None
best_input_signals = None
for chassis in chassis_name:
    in_ucf = f'{chassis}.UCF.json'
    input_sensor_file = f'{chassis}.input.json'
    output_device_file = f'{chassis}.output.json'
    q = CelloQuery(
        input_directory=in_dir,
        output_directory=out_dir,
        verilog_file=v_file,
        compiler_options=options,
        input_ucf=in_ucf,
        input_sensors=input_sensor_file,
        output_device=output_device_file,
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
    print('-----')
print(f'Best Score: {best_score}')
print(f'Best Chassis: {best_chassis}')
print(f'Best Input Signals: {best_input_signals}')
``` 


# Installation
## Requirements
Prerequisites:
[Docker](https://docs.docker.com/get-docker/)

[Python 3.8+](https://www.python.org/downloads/)
## Commands
```
$ docker pull cidarlab/cello-dnacompiler:latest

$ pip install celloapi2
```


# CelloAPI2 requires a local input directory and a local output directory. The input directory contains the four primary inputs to the cello API:
     - A Verilog File that describes the genetic circuit.
     - A User-Constraint-File (UCF) that describes the target vector. 
     - A file (*.input.json) that describes the input signals into the circuit.
     - A file (*.output.json) that describes the resultant output signal at the end of the circuit. 
# These files can be found in Cello-UCF. 

```
## Roadmap
```
1. Removal of Docker Requirement by adding API layer to Cello2
Server that allows for arbitrary execution of Cello.

2. Interactive Data Visualization Output for individual parts.

3. Better Yosys/Eugene Interaction for re-ordering genetic circuits.
```