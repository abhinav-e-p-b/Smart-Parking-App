

from roboflow import Roboflow
rf = Roboflow(api_key="sq6W38HVjyLeFqV6zQFx")
project = rf.workspace("vishal-hwk3p").project("number-plate-h14v7")
version = project.version(1)
dataset = version.download("yolov8")
                