#!/usr/bin/env python3
"""Download public iCloud Shared Albums. Requires Python 3.8+ and curl."""

import argparse
import concurrent.futures
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


def request_json(url, payload):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "response.json"
        subprocess.run(
            [
                "curl", "-fLsS",
                "--retry", "3",
                "--retry-all-errors",
                "--connect-timeout", "30",
                "--max-time", "180",
                "-H", "Content-Type: text/plain",
                "--data", json.dumps(payload),
                url, "-o", str(target),
            ],
            check=True,
        )
        return json.loads(target.read_text())


def download_file(job):
    url, target, expected_size = job

    if target.exists() and target.stat().st_size == expected_size:
        return True

    partial = target.with_suffix(target.suffix + ".part")

    for _ in range(3):
        result = subprocess.run(
            [
                "curl", "-fLsS",
                "--retry", "2",
                "--retry-all-errors",
                "--connect-timeout", "30",
                "--max-time", "600",
                url, "-o", str(partial),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if (
            result.returncode == 0
            and partial.exists()
            and partial.stat().st_size == expected_size
        ):
            partial.replace(target)
            return True

    print(f"\nFailed: {target.name}", flush=True)
    return False


def download_album(url, output, workers):
    parsed = urlsplit(url)
    token = parsed.fragment

    if (
        parsed.hostname not in ("icloud.com", "www.icloud.com")
        or not parsed.path.rstrip("/").endswith("/sharedalbum")
        or not re.fullmatch(r"[BD][A-Za-z0-9_-]+", token)
    ):
        raise ValueError("Use a public iCloud Shared Album link including #...")

    base = f"https://sharedstreams.icloud.com/{token}/sharedstreams"
    stream = request_json(f"{base}/webstream", {"streamCtag": None})

    host = stream.get("X-Apple-MMe-Host")
    if host:
        if not re.fullmatch(r"[A-Za-z0-9-]+\.icloud\.com", host):
            raise ValueError("Unexpected iCloud server")
        base = f"https://{host}/{token}/sharedstreams"
        stream = request_json(f"{base}/webstream", {"streamCtag": None})

    if "photos" not in stream:
        raise RuntimeError("iCloud did not return an album")

    title = stream.get("streamName") or "Untitled Album"
    name = re.sub(r'[/:\x00-\x1f]', "-", title).strip(" .")
    name = name or "Untitled Album"

    # Keep a local mapping so reruns reuse folders, even after album renames.
    index_path = output / ".album-folders.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    saved_name = index.get(token)

    if saved_name:
        if Path(saved_name).name != saved_name or saved_name in (".", ".."):
            raise ValueError("Invalid folder mapping")
        folder = output / saved_name
    else:
        folder = output / name
        number = 2
        while folder.exists():
            folder = output / f"{name} ({number})"
            number += 1
        folder.mkdir()
        index[token] = folder.name
        temporary = index_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2))
        temporary.replace(index_path)

    folder.mkdir(exist_ok=True)
    photos = stream["photos"]
    print(f"\nAlbum: {title}\nItems: {len(photos)}\nFolder: {folder}", flush=True)

    jobs = []
    unavailable = 0

    for offset in range(0, len(photos), 100):
        batch = photos[offset:offset + 100]
        assets = request_json(
            f"{base}/webasseturls",
            {"photoGuids": [photo["photoGuid"] for photo in batch]},
        ).get("items", {})

        for photo in batch:
            video = photo.get("mediaAssetType") == "video"
            derivatives = photo.get("derivatives", {})

            if video:
                derivatives = {
                    key: value for key, value in derivatives.items()
                    if key != "PosterFrame"
                }

            if not derivatives:
                unavailable += 1
                continue

            best = max(
                derivatives.values(),
                key=lambda item: int(item.get("fileSize", 0)),
            )
            asset = assets.get(best["checksum"])
            if not asset:
                unavailable += 1
                continue

            guid = photo["photoGuid"]
            if not re.fullmatch(r"[A-Za-z0-9-]+", guid):
                raise ValueError("Unexpected photo identifier")

            extension = ".mp4" if video else ".jpg"
            target = folder / f"{guid}{extension}"
            media_url = f"https://{asset['url_location']}{asset['url_path']}"
            jobs.append((media_url, target, int(best["fileSize"])))

    total_bytes = sum(job[2] for job in jobs)
    print(f"Download size: {total_bytes / 1e9:.2f} GB", flush=True)

    successful = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download_file, job) for job in jobs]
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            successful += bool(future.result())
            print(f"\rChecked: {done}/{len(jobs)}", end="", flush=True)

    print(f"\nComplete files: {successful}/{len(photos)}")
    if unavailable:
        print(f"Unavailable items: {unavailable}")

    return successful == len(photos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*", help="Public Shared Album URLs")
    parser.add_argument("--file", type=Path, help="Text file: one URL per line")
    parser.add_argument("--output", type=Path, default=Path("downloads"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")

    urls = list(args.urls)
    if args.file:
        urls.extend(
            line.strip()
            for line in args.file.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )

    urls = list(dict.fromkeys(urls))
    if not urls:
        parser.error("Provide album URLs or use --file albums.txt")

    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    failures = 0

    for number, url in enumerate(urls, 1):
        print(f"\n=== Album {number}/{len(urls)} ===", flush=True)
        try:
            if not download_album(url, output, args.workers):
                failures += 1
        except Exception as error:
            failures += 1
            print(f"Album failed: {error}", flush=True)

    print(f"\nResults: {output}")
    if failures:
        print(f"{failures} album(s) incomplete. Run again to retry.")
        print("Existing files with matching sizes will be skipped.")
        return 1

    print("All albums complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
