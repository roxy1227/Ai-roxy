from ultralytics import YOLO

model = YOLO("models/yolo12n.pt")
model.export(format="engine", int8=True)