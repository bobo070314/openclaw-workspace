import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")
from core.yolo_classifier import classify

rr = classify("import os\nos.system('rm -rf /')\npassword = 'admin123'")
print("result:", rr)
