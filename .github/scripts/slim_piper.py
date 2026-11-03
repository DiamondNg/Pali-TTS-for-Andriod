"""Remove the parts of the piper package that the Kannada voice never uses
(Hebrew and Arabic models, training code, eSpeak dictionaries of other languages):
about 45 MB less per copy. Usage: python slim_piper.py <folder that contains piper/>"""
import os
import shutil
import sys

KEEP_DICTS = {"kn_dict", "en_dict"}
root = os.path.join(sys.argv[1], "piper")
assert os.path.isdir(root), root
before = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)
for rel in ["hebrew/nakdimon.onnx", "tashkeel/model.onnx", "train"]:
    p = os.path.join(root, rel)
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.exists(p):
        os.remove(p)
data = os.path.join(root, "espeak-ng-data")
for name in os.listdir(data):
    if name.endswith("_dict") and name not in KEEP_DICTS:
        os.remove(os.path.join(data, name))
assert os.path.exists(os.path.join(data, "kn_dict")), "no Kannada dictionary"
after = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(root) for f in fs)
print("piper: %.1f MB → %.1f MB" % (before / 1e6, after / 1e6))
