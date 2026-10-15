
from pathlib import Path
import requests
import time

folder = Path(__file__).resolve().parent / "official_pdfs"
folder.mkdir(parents=True, exist_ok=True)

laws = {
    "Bharatiya_Nyaya_Sanhita_2023.pdf": [
        "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a2023-45.pdf",
        "https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf",
        "https://xn--i1b5bzbybhfo5c8b4bxh.xn--11b7cb3a6a.xn--h2brj9c/sites/default/files/2024-04/250883_english_01042024.pdf",
    ],
    "Bharatiya_Sakshya_Adhiniyam_2023.pdf": [
        "https://www.indiacode.nic.in/bitstream/123456789/20063/1/aa202347.pdf",
    ],
    "Dowry_Prohibition_Act_1961.pdf": [
        "https://www.indiacode.nic.in/bitstream/123456789/1679/4/a1961-28.pdf",
        "https://www.indiacode.nic.in/bitstream/123456789/16243/1/196128.pdf",
    ],
    "Information_Technology_Act_2000.pdf": [
        "https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf",
    ],
}

def is_valid_pdf(path):
    try:
        with path.open("rb") as file:
            return file.read(5) == b"%PDF-"
    except OSError:
        return False

def download(filename, urls):
    destination = folder / filename

    if is_valid_pdf(destination):
        print(f"ALREADY DOWNLOADED: {filename}")
        return

    for url in urls:
        for attempt in range(3):
            temp = destination.with_suffix(".pdf.part")
            try:
                print(f"Trying {filename} (attempt {attempt + 1})")

                with requests.get(
                    url,
                    stream=True,
                    timeout=(20, 180),
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as response:
                    response.raise_for_status()

                    first_chunk = True
                    with temp.open("wb") as file:
                        for chunk in response.iter_content(1024 * 128):
                            if not chunk:
                                continue
                            if first_chunk:
                                if not chunk.startswith(b"%PDF-"):
                                    raise ValueError(
                                        "The server did not return a PDF."
                                    )
                                first_chunk = False
                            file.write(chunk)

                if not is_valid_pdf(temp):
                    raise ValueError("Downloaded file is not a valid PDF.")

                temp.replace(destination)
                print(f"SUCCESS: {destination}")
                return

            except Exception as error:
                print(f"Failed: {error}")
                temp.unlink(missing_ok=True)
                time.sleep(3 * (attempt + 1))

    print(f"NOT DOWNLOADED: {filename}")

for filename, urls in laws.items():
    download(filename, urls)

print(f"\nCheck folder: {folder}")
