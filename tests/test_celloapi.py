'''
--------------------------------------------------------------------------------
Description:

Written by W.R. Jackson <wrjackso@bu.edu>, DAMP Lab 2021
--------------------------------------------------------------------------------
'''
import glob
import os

from celloapi2.celloapi import CelloQuery, CelloResult


def _make_cello_query():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    root_path = os.path.dirname(dir_path)
    in_dir = root_path + "/example_data"
    out_dir = in_dir + "/dummy_output"
    v_file = "and.v"
    options = "options.csv"
    in_ucf = "Eco1C1G1T1.UCF.json"
    input_sensor_file = "Eco1C1G1T1.input.json"
    output_device_file = "Eco1C1G1T1.output.json"
    query = CelloQuery(
        input_directory=in_dir,
        output_directory=out_dir,
        verilog_file=v_file,
        compiler_options=options,
        input_ucf=in_ucf,
        input_sensors=input_sensor_file,
        output_device=output_device_file,
        logging=True,
    )
    return query


def test_cello_query():
    q = _make_cello_query()
    res = q.get_results()
    assert res


def test_cello_query_input_selection():
    q = _make_cello_query()
    input_signals = ["LacI", "TetR"]
    q.set_input_signals(input_signals)
    assert q.get_input_signals() == input_signals


def test_cello_result():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    root_path = os.path.dirname(dir_path)
    in_dir = root_path + "/example_data"
    out_dir = in_dir + "/dummy_output"
    res = CelloResult(results_dir=out_dir)
    assert res.logic_dict
    assert res.activity_dict
    assert res.repressor_scores
    assert res.circuit_score
    assert res.part_names


def test_cleanup():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    root_path = os.path.dirname(dir_path)
    in_dir = root_path + "/example_data"
    out_dir = in_dir + "/dummy_output"
    files = glob.glob(f'{out_dir}/*')
    for file in files:
        try:
            if os.path.isdir(file):
                os.rmdir(file)
            else:
                os.remove(file)
        except OSError:
            print('Unable to delete files, please investigate.')
