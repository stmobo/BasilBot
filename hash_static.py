import hashlib
import json
from pathlib import Path
import shutil


in_dir = Path("static/css")
out_dir = Path("build/css")
in_manifest_file = Path("build/js/base_manifest.json")
out_manifest_file = Path("build/js/static_manifest.json")
subst_files = {Path("static/series_index.html"): Path("build/series_index.html")}


out_dir.mkdir(exist_ok=True, parents=True)
for file in filter(Path.is_file, out_dir.iterdir()):
    file.unlink()

with in_manifest_file.open("r", encoding="utf-8") as f:
    manifest = json.load(f)

new_manifest = {
    "js": {},
    "css": {},
}

for key in manifest.keys():
    new_manifest["js"][key] = manifest[key]

for file in filter(Path.is_file, in_dir.iterdir()):
    with file.open("rb") as f:
        h = hashlib.sha1(f.read())

    outpath = out_dir.joinpath(file.stem + "." + h.hexdigest() + file.suffix)
    shutil.copyfile(file, outpath)

    new_manifest["css"][file.name] = outpath.name

for subst_file, out_file in subst_files.items():
    with subst_file.open("r", encoding="utf-8") as f:
        contents = f.read()

    for filetype, manifest in new_manifest.items():
        prefix = "/" + filetype + "/"

        for old_filename, new_filename in manifest.items():
            print(prefix + old_filename + " => " + prefix + new_filename)

            contents = contents.replace(prefix + old_filename, prefix + new_filename)

    with out_file.open("w", encoding="utf-8") as f:
        f.write(contents)

with out_manifest_file.open("w", encoding="utf-8") as f:
    json.dump(new_manifest, f, indent=4)
