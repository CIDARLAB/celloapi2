"""
--------------------------------------------------------------------------------
Description: A Simplistic Python API designed to interface with CelloV2. Heavily
inspired by Ezira Wolfe's original pycello.

But this is Better than Ezira, which is Good.

No one who reads this will get the joke, and the world's poorer for it.

Written by W.R. Jackson <wrjackso@bu.edu>, DAMP Lab 2021
--------------------------------------------------------------------------------
"""
import datetime
import glob
import json
import math
import os
import shutil
import subprocess
import sys
from typing import (
    Any,
    Dict,
    List,
    Union,
)

import numpy as np
import yaml


def _fix_input_json(
    input_fp: str,
    final_trailing_comma: bool = False,
) -> Union[List[Dict], Dict]:
    """
    Fixes some of the weird data output from Cello2 when it comes to marshalling
    resources back and forth.

    Args:
        input_fp: Absolute path to the file
        final_trailing_comma: Whether or not the JSON in question has a final
            trailing comma.

    Returns:
        List of Dictionaries, typically.

    """
    with open(input_fp) as input_file:
        # TODO: Tim outputs invalid JSON in a number of very special ways
        #  that needs to be resolved. Quick and dirty hack for now.
        dirty_data = input_file.read()
        # It's tab-delineated!
        dirty_data = dirty_data.replace("\t", "")
        # There is (only sometimes!) a final trailing comma on the outside of
        # the entire JSON structure that can't be handled by the YAML superset!
        # Depends on the file for some reason!
        if final_trailing_comma:
            idx = dirty_data.rfind(",")
            dirty_data = dirty_data[:idx]
        data = yaml.load(dirty_data, Loader=yaml.FullLoader)
        # Generally, these kind of things are structured dictionaries but the
        # input JSONs are mangled so it's a coin flip.
        return data


class CelloResult:
    def __init__(self, results_dir: str):
        """
        High Level Class that encapsulates some of the oddities of
        recapitulating the necessary information from the Cello output
        documentation.

        Args:
            results_dir: The directory that contains all of the output from
                running the Cello DNAComplier Process.

        Attributes:
            logic_dict: Dictionary mapping the node label to it's boolean state.
                Used for scoring individual gates/repressors.
            activitiy_dict:  Dictionary mapping the node label to it's activity
                score.
            part_names: Dictionary mapping the node labels to their human
                readable labels.
            repressor_scores: Dictionary mapping the node label for each
                repressor and it's correlating score as dictated in the
                literature.
            circuit_score: Float representing the numerical score of the
                entirety of the circuit. Derived from a simulated annealing
                algorithm.
        """
        self.output_dir = results_dir
        self.logic_dict = self._parse_result_csv(filename="logic")
        self.activity_dict = self._parse_result_csv(filename="activity")
        self.part_names = self._map_symbolic_representation_to_true_name()
        self.repressor_scores = self.score_repressors()
        self.circuit_score = self._parse_log_file()

    def _parse_result_csv(
        self,
        filename: str,
    ) -> Dict[str, Any]:
        """
        Utility function to pull in a CSV and convert it into a dictionary where
        the keys are the node labels and the values correspond to whichever CSV
        is being requested.

        Numpy CSV parsing is due to future optimization concerns.

        Args:
            filename: Which file to parse.

        Returns:
            A dictionary composed of node label keys and whatever the requested
            data is.
        """
        in_file = glob.glob(f"{self.output_dir}/*_{filename}.csv")
        if not in_file:
            raise RuntimeError(
                f"Unable to find {filename}.csv. Please check output directory."
            )
        if len(in_file) - 1:
            raise RuntimeError(
                "Found multiple results matching pattern. Please investigate."
            )
        input_activity = np.genfromtxt(
            in_file[0],
            delimiter=",",
            dtype=None,
            encoding=None,
        )
        mapping_keys = {}
        for row in input_activity:
            row = list(row)
            mapping_keys[row[0]] = row[1:]
        return mapping_keys

    def _map_symbolic_representation_to_true_name(self) -> Dict[str, str]:
        """
        All internal references in all of the Cello results reference everything
        by it's associated verilog variable name, but that's not parsable by
        human beings.

        This maps those variables to their human names.

        Returns:
            A dictionary mapping verilog variable names to their corresponding
            biological nomenclature, e.g. yfp_cassette, Phlf, etc.

        """
        in_file = glob.glob(f"{self.output_dir}/*_outputNetlist.json")
        if not in_file:
            raise RuntimeError(
                "Unable to find Output Netlist. Please check output directory."
            )
        if len(in_file) - 1:
            raise RuntimeError(
                "Found multiple results matching pattern. Please investigate."
            )
        data = _fix_input_json(in_file[0], final_trailing_comma=True)
        out_mapping = {}
        repressor_keys = self.logic_dict.keys()
        for key in repressor_keys:
            for node in data["nodes"]:
                if key == node["name"]:
                    out_mapping[key] = node["deviceName"]
        return out_mapping

    def score_repressors(self) -> Dict[str, float]:
        """
        Scores all of the repressors in the genetic circuit according to the
        highest off and lowest on.

        Returns:
            Dictionary mapping the verilog variable label of each repressor to
            it's score.

        """
        # Should be identical for either one. If not, we got problems.
        if self.logic_dict.keys() != self.activity_dict.keys():
            raise RuntimeError(
                f"Logic and Activity Output do not match. Please investigate."
            )
        repressor_keys = self.logic_dict.keys()
        # TODO: I think this is a Tim-ism, but all repressors are prepended
        # with a dollar sign ala a bash variable. Otherwise they are the input
        # signals or the primary output.
        repressor_keys = list(filter(lambda x: x[0] == "$", repressor_keys))
        score_dict = {}
        for r_key in repressor_keys:
            truth_table = self.logic_dict[r_key]
            activity_values = self.activity_dict[r_key]
            low_on = min(
                [i for idx, i in enumerate(activity_values) if truth_table[idx]]
            )
            high_off = max(
                [
                    i
                    for idx, i in enumerate(activity_values)
                    if not truth_table[idx]
                ]
            )
            score = math.log(low_on / high_off)
            score_dict[r_key] = score
        return score_dict

    def get_part_map(self) -> Dict[str, str]:
        """
        Inverts the relationship between the verilog variable keys and
        human-readable part names.

        Returns:
            Dictionary mapping part names to their verilog labels.

        """
        return {v: k for k, v in self.part_names.items()}

    def _parse_log_file(self) -> float:
        """
        Pulls the total score of the circuit out of the final logging file.

        Returns:
            total score of the circuit out of the final logging file.

        """
        # This is probably a code smell, given that this information is vitally
        # important but only captures in a STDOUT Log. TODO, I suppose.
        in_file = glob.glob(f"{self.output_dir}/*.log")
        if len(in_file) - 1:
            raise RuntimeError(
                "Found multiple results matching pattern. Please investigate."
            )
        with open(in_file[0]) as input_file:
            for line in input_file:
                if "SimulatedAnnealing - Score:" in line:
                    circuit_score = float(line.split(" ")[-1])
                    return circuit_score
        # If we get here something is screwed in the logfile and we need to
        # bomb out.
        raise RuntimeError(
            "Unable to locate Circuit Score in log.log. Please investigate."
        )


class CelloQuery:
    def __init__(
        self,
        input_directory: str = None,
        output_directory: str = None,
        verilog_file: str = None,
        compiler_options: str = None,
        input_ucf: str = None,
        input_sensors: str = None,
        output_device: str = None,
        logging: bool = False,
    ):
        """
        Class encapsulating all of the weirdness of interacting with Cello.

        Args:
            input_directory: The input directory containing all of our input
                files for Cello analysis. All of the input files should
                exist at this level and not be nested any further.
            output_directory: The output directory where all results will be
                saved.
            verilog_file: A valid verilog file.
            compiler_options: A CSV describing various inputs to the compiler.
                Fairly static in practice, but this could change in the future.
            input_ucf: The input UCF (User Constraint File) that defines the
                chassis or input vector that the circuit will be implanted into.
            input_sensors: The input sensors that define the behavior of the
                input into the genetic circuit.
            output_device: The output (Generally something like a
                fluorescent protein)
            logging: Optional. If true, when results are submitted the terminal
                output from the docker container will be displayed in the
                terminal.
        """
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.verilog_file = verilog_file
        self.compiler_options = compiler_options
        self.input_ucf = input_ucf
        self.input_sensors = input_sensors
        self.output_device = output_device
        self.logging = logging

    def get_results(self) -> int:
        """
        Primary Entrypoint for the library. Wraps calling the Cello Docker
        Container and takes care of all of the busywork neccesary to make
        everything come together.

        Returns:
            An integer value representing success or failure.
        """
        query_attributes = vars(self)
        for query_attr in query_attributes:
            if query_attributes[query_attr] is None:
                raise RuntimeError(
                    f"Unable to submit request, required attribute {query_attr} "
                    f"is not set."
                )
        # Probably some check to see if the directories are being generated
        # properly.
        if self.check_for_prior_results():
            print("Prior results detected, moving to prevent clobber.")
            dest = self.archive_prior_results()
            print(f"Prior results move to {dest}")
        docker_cmd = [
            f"docker run --rm "
            f"-v {self.input_directory}:/root/input "
            f"-v {self.output_directory}:/root/output"
            f" -t cidarlab/cello-dnacompiler:latest java -classpath /root/app.jar "
            f"org.cellocad.v2.DNACompiler.runtime.Main "
            f"-inputNetlist /root/input/{self.verilog_file} "
            f"-options /root/input/{self.compiler_options} "
            f"-userConstraintsFile /root/input/{self.input_ucf} "
            f"-inputSensorFile /root/input/{self.input_sensors} "
            f"-outputDeviceFile /root/input/{self.output_device} "
            f"-pythonEnv python "
            f"-outputDir /root/output"
        ]
        try:
            process = subprocess.Popen(
                docker_cmd, shell=True, stdout=subprocess.PIPE
            )
            if self.logging:
                for line in iter(lambda: process.stdout.read(1), b""):
                    sys.stdout.buffer.write(line)
            else:
                print("Executing Cello Query... (This may take a moment)")
                process.communicate()
                print("Cello Query Finished!")
                return 0
        except subprocess.CalledProcessError:
            print(
                "Eugene failed to synthesize valid gate and part placement. "
                "Please re-attempt (The process is non-deterministic) or "
                "change input parameters to CelloQuery. Partial Results "
                "are available in output directory"
            )
        return 1

    def get_input_signals(self) -> List[str]:
        """
        Parses the input UCF and pulls out all of the human readable names
        for input signals.

        Returns:
            A list of human readable input signals.
        """
        data = _fix_input_json(f"{self.input_directory}/{self.input_sensors}")
        # Each input sensor is represented by a disjoint triplet of
        # an input sensor datastructure, a model of that input sensor, and one
        # representing the structure.
        # This is kind of a master class in how not to do data modeling, so this
        # is a bit squidgy.
        name_list = []
        for row in data:
            if row["collection"] == "input_sensors":
                raw_name = row["name"]
                name_list.append(raw_name.split("_")[0])
        return name_list

    def set_input_signals(
        self,
        input_signals: List[str],
        output_filename: str = "custom_input.input.json",
        mutate: bool = True,
    ) -> str:
        """
        "Sets" the input signals for the circuit.

        In this context, it's accomplished by removing all entries from the
        input.json that don't correspond to the selected inputs.

        This also mutates the class to point to the new input.json as a default.

        Returns:
            A string corresponding to the filename. Typically for scripting or
            generating programmatic inputs for the homework assignment.
        """

        def _prune_other_sensors(
            suffix: str,
            target_collection: str,
            in_data: List[Dict],
            in_signals: List[str],
        ):
            query_list = []
            for sig in in_signals:
                query_list.append(sig + suffix)
            for row in in_data:
                if row["collection"] == target_collection:
                    if row["name"] not in query_list:
                        in_data.remove(row)
            return in_data

        available_input_signals = self.get_input_signals()
        for signal in input_signals:
            if signal not in available_input_signals:
                raise RuntimeError(
                    f"Cannot set {signal}, not present in available signals "
                )
        # Once we're good we need to trim the input sensors to just what is
        # being used.
        data = _fix_input_json(f"{self.input_directory}/{self.input_sensors}")
        data = _prune_other_sensors(
            "_sensor", "input_sensors", data, input_signals
        )
        data = _prune_other_sensors(
            "_sensor_model", "models", data, input_signals
        )
        data = _prune_other_sensors(
            "_sensor_structure", "structures", data, input_signals
        )
        with open(f"{self.input_directory}/{output_filename}", "w") as out_file:
            json.dump(data, out_file)
        if mutate:
            self.input_sensors = output_filename
        return output_filename

    def check_for_prior_results(self) -> bool:
        """
        Checks to see if there are any prior results in the output directory

        Returns:
            If there are prior results in the output directory.
        """
        dir_contents = glob.glob(f"{self.output_directory}/*")
        dir_contents = list(
            filter(lambda x: "prior_cello_result" not in x, dir_contents)
        )
        if len(dir_contents) > 1:
            return True
        return False

    def archive_prior_results(self) -> str:
        """
        Moves prior results to a safe location to prevent clobbering.

        Returns:
            The location that the prior results were move to.

        """
        # TODO: Not sure how to do compression that's safe across all OSes.
        archive_dir_name = f"prior_cello_result_{datetime.datetime.now()}"
        archive_dir = f"{self.output_directory}/{archive_dir_name}"
        os.mkdir(archive_dir)
        active_files = glob.glob(f"{self.output_directory}/*")
        active_files = list(
            filter(lambda x: "prior_cello_result" not in x, active_files)
        )
        for file in active_files:
            shutil.move(file, archive_dir)
        return archive_dir
