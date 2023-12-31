import os
import logging
import time


def formatTime(millis):
    seconds = millis // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class TimeThis:
    def __init__(self, getter):
        self.startTime = 0
        self.getter = getter

    def __enter__(self):
        self.startTime = time.time_ns()

    def __exit__(self, exc_type, exc_value, traceback):
        self.getter(time.time_ns() - self.startTime)


def apply_function_to_files(function, input_directory, output_directory=None):
    logging.info(f"input directory: \"{input_directory}\"")

    if not os.path.exists(input_directory):
        logging.info(f"input directory: \"{input_directory}\" does not exist")
        return

    if not os.path.isdir(input_directory):
        logging.info(
            f"input directory: \"{input_directory}\" is not a directory"
        )
        return

    if output_directory is None:
        for filename in os.listdir(input_directory):
            input_file_path = os.path.join(input_directory, filename)

            if os.path.isfile(input_file_path):
                function(input_file_path)

            elif os.path.isdir(input_file_path):
                apply_function_to_files(function, input_file_path)
    else:
        if not os.path.exists(output_directory):
            os.mkdir(output_directory)
            logging.info(
                f"directory: \"{output_directory}\" successfully created"
            )
        else:
            logging.info(f"output directory: \"{output_directory}\"")

        for filename in os.listdir(input_directory):
            input_file_path = os.path.join(input_directory, filename)
            output_file_path = os.path.join(output_directory, filename)

            if os.path.isfile(input_file_path):
                function(input_file_path, output_file_path)

            elif os.path.isdir(input_file_path):
                apply_function_to_files(
                    function, input_file_path, output_file_path
                )
