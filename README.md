# iCloud Shared Album Downloader

Download photos and videos from one or multiple public iCloud Shared Albums, organized into folders using the original album names.

## Features

- Download multiple albums with one command.
- Automatically name folders after each Shared Album.
- Download the largest available photo or video version.
- Retry failed downloads.
- Verify downloaded file sizes against iCloud metadata.
- Skip existing files with matching sizes when running again.
- Continue to the next album if one fails.
- No Apple Account login required for public albums.

## Requirements

- Python 3.8 or later.
- `curl` with support for `--retry-all-errors` (version 7.71.0 or later).
- An internet connection and enough free storage.

No additional Python packages are required. The instructions below are for macOS.

Check your installed versions:

```bash
python3 --version
curl --version
```

## Download the Script

1. Click **Code → Download ZIP** on this repository.
2. Extract the ZIP file.
3. Open Terminal.
4. Type `cd` followed by a space, drag the extracted folder into Terminal, then press Enter.

## Usage

Replace the example links below with your public Shared Album links. Keep the quotation marks and include the full `#...` portion.

### Download one album

```bash
python3 download_albums.py "https://www.icloud.com/sharedalbum/#YOUR_ALBUM_TOKEN"
```

### Download multiple albums

```bash
python3 download_albums.py \
  "https://www.icloud.com/sharedalbum/#FIRST_ALBUM_TOKEN" \
  "https://www.icloud.com/sharedalbum/#SECOND_ALBUM_TOKEN" \
  "https://www.icloud.com/sharedalbum/#THIRD_ALBUM_TOKEN"
```

### Download from a list

Create a plain-text file named `albums.txt` with one album link per line:

```text
https://www.icloud.com/sharedalbum/#FIRST_ALBUM_TOKEN
https://www.icloud.com/sharedalbum/#SECOND_ALBUM_TOKEN
https://www.icloud.com/sharedalbum/#THIRD_ALBUM_TOKEN
```

Then run:

```bash
python3 download_albums.py --file albums.txt
```

Blank lines and lines starting with `#` are ignored. Keep your personal album list local rather than committing it to this public repository.

### Choose a destination folder

```bash
python3 download_albums.py \
  --file albums.txt \
  --output "$HOME/Pictures/iCloud Albums"
```

### Adjust simultaneous downloads

The default is six downloads at a time. For a slower or unstable connection, try three:

```bash
python3 download_albums.py --file albums.txt --workers 3
```

The supported range is 1–16.

## Output

By default, files are saved in a `downloads` folder inside your current Terminal directory:

```text
downloads/
├── Family Holiday/
│   ├── PHOTO-ID.jpg
│   └── VIDEO-ID.mp4
├── Mountain Trip/
│   └── PHOTO-ID.jpg
└── .album-folders.json
```

- Folder names follow the original Shared Album names.
- Unsupported characters in folder names are replaced.
- Albums with identical names receive separate numbered folders.
- Files use iCloud identifiers as filenames.
- `.album-folders.json` keeps track of album folders for future runs. Keep it if you want reruns to reuse the same folders.
- An album renamed in iCloud will continue using its previously assigned local folder.

Open the default output folder on macOS:

```bash
open downloads
```

## Retrying Downloads

If a download fails or your connection drops, run the same command again with the same output folder.

Files whose sizes already match iCloud metadata will be skipped. Incomplete files will be downloaded again from the beginning.

The message below indicates that all returned album items were downloaded and their sizes matched:

```text
All albums complete.
```

File-size verification does not replace a full integrity or media-playback check.

## Limitations

- Supports public links in the form `https://www.icloud.com/sharedalbum/#...`.
- Does not download private albums that require Apple Account authentication.
- Uses an unofficial, undocumented iCloud API that Apple may change.
- Downloads the versions available through Shared Albums. These may differ from the original files on the uploader’s device.
- Does not export comments, likes, or album captions.
- Photos are saved with `.jpg` filenames and videos with `.mp4` filenames; the script does not convert media formats.
- Deleted or unavailable items may prevent an album from completing.

## Troubleshooting

### `python3: command not found`

Install Python 3 from [python.org](https://www.python.org/downloads/), reopen Terminal, and try again.

### `curl: option --retry-all-errors: is unknown`

Your version of `curl` is too old. Use version 7.71.0 or later.

### `can't open file 'download_albums.py'`

Make sure Terminal is in the folder containing the script. Type `cd` followed by a space, drag that folder into Terminal, and press Enter.

### An album fails

Check that the public link still opens in a browser and includes the complete `#...` portion. Retry with fewer simultaneous downloads:

```bash
python3 download_albums.py --file albums.txt --workers 3
```

If it continues failing, the album may be unavailable or Apple’s API may have changed.

## Privacy

Album links and download requests are sent to Apple’s servers. Downloaded files are stored locally in your chosen destination.

Do not publish personal album links, downloaded media, or `.album-folders.json` in this repository.

## Disclaimer

This project is not affiliated with or endorsed by Apple. Only download content you are authorized to access.

## License

MIT License. See [LICENSE](LICENSE).
