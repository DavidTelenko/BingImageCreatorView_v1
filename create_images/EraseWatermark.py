import uuid
import cv2
import sys
import os
from Utils import apply_function_to_files


def make_inpaint_all(mask):
    def inpaint_all(i, o):
        try:
            print(f"file: \"{i}\" started processing")
            src = cv2.imread(i)
            res = cv2.inpaint(src, mask, 3, cv2.INPAINT_TELEA)
            cv2.imwrite(o, res)
            print(f"file saved as: \"{o}\"")
        except Exception as e:
            print(e)
            return
    return inpaint_all


def rename_to_unique(i):
    try:
        directory = os.path.dirname(i)
        ext = os.path.splitext(i)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        os.rename(i, os.path.join(directory, unique_name))
    except Exception as e:
        print(e)
        return


def make_change_extension(from_ext, to_ext):
    def change_extension(i):
        try:
            name, ext = os.path.splitext(i)
            if not ext == from_ext:
                return
            directory = os.path.dirname(i)
            changed = f"{name}{to_ext}"
            os.rename(i, os.path.join(directory, changed))
        except Exception as e:
            print(e)
            return
    return change_extension


if __name__ == "__main__":
    apply_function_to_files(
        make_inpaint_all(
            cv2.imread(
                sys.argv[3],
                cv2.IMREAD_GRAYSCALE)
        ),
        sys.argv[1],
        sys.argv[2]
    )
