from locust import HttpUser, task, between
import random
import json
from pathlib import Path
import csv

cur_dir = Path(__file__).parent
output_dir = Path(r"C:\UCLEAP\UC_LEAP\step3_5\work\step1_0218\generated_type1")
output_dir.mkdir(parents=True, exist_ok=True)

candidate_manifest_paths = [
    cur_dir / "manifest.json",
    Path.cwd() / "manifest.json",
    output_dir / "manifest.json",
    cur_dir.parent / "manifest.json",
]
manifest_path = next((p for p in candidate_manifest_paths if p.exists()), None)

# Load the manifest
if manifest_path is None:
    raise FileNotFoundError(
        "IIIF Manifest file not found in the script directory, current working directory, "
        "output directory, or bundle parent directory.\n\n"
        "You can download the manifest from `/api/iiif/record:{id}/manifest` of the "
        "Zenodo instance you're testing."
    )

with manifest_path.open() as f:
    MANIFEST = json.load(f)
CANVASES = [c for c in MANIFEST["sequences"][0]["canvases"] if "height" in c]

sample_csv_path = output_dir / "iiif_sample_requests.csv"
_sample_csv_initialized = False


def _append_sample_row(row):
    global _sample_csv_initialized
    write_header = not sample_csv_path.exists() or not _sample_csv_initialized
    with sample_csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["base_url", "random_slice", "thumbnail", "info_json"])
            _sample_csv_initialized = True
        writer.writerow(row)


class ImageEndpointUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def access_image_endpoint(self):
        item = random.choice(CANVASES)
        base_url = item["images"][0]["resource"]["service"]["@id"]

        x = random.randint(1, item["width"] - 1)
        y = random.randint(1, item["height"] - 1)
        h = random.randint(1, 1000)
        w = random.randint(1, 1000)
        s = 256 * random.choice([1, 2, 4, 8])
        r = random.choice([0, 90, 180, 270])
        random_slice = f"{base_url}/{x},{y},{h},{w}/^{s},/{r}/default.jpg"
        thumbnail = f"{base_url}/full/^250,/0/default.jpg"
        info_json = f"{base_url}/info.json"

        _append_sample_row([base_url, random_slice, thumbnail, info_json])

        self.client.get(random_slice, name="/iiif/random_chunk")
        self.client.get(thumbnail, name="/iiif/thumbnail")
        self.client.get(info_json, name="/iiif/info.json")
