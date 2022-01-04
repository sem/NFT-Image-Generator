# NFT-Image-Generator
Utility for creating a generative art collection from supplied image layers, especially made for making NFT collectibles.

## Prerequisites
1. Clone the repository by running ```git clone https://github.com/sem/NFT-Image-Generator```.
2. Install the dependencies ```pip3 install -r requirements.txt```.

## How to use
1. Get an API key from [Pinata](https://app.pinata.cloud/keys).
2. Go to ``config.json`` and put the JWT (Secret access token) in ``api_key``.
3. Adapt the config to your liking and make sure there is a sequencial number after each folder to represent the order of layers.
4. Run ``main.py``.

## File structure
Before you start, make sure your file structure looks something like this:
```
NFT-Image-Generator/
├─ main.py
├─ config.json
├─ background 1/
│  ├─ red.png
│  ├─ green.png
│  ├─ blue.png
├─ body 2/
│  ├─ female.png
│  ├─ male.png
│  ├─ zombie.png
├─ eyes 3/
│  ├─ sun_glasses.png
│  ├─ normal_eyes.png
│  ├─ vr_glasses.png
```

## Features
- Generates metadata for direct use on [OpenSea](https://docs.opensea.io/docs/metadata-standards).
- Automatically uploads your images and metadata to [Pinata](https://www.pinata.cloud).
- Ensures that no duplicate images will be in the collection.
