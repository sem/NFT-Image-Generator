import json
import os
import shutil
import random
from datetime import datetime
from io import BytesIO
from itertools import product, combinations
from urllib.parse import quote

from PIL import Image
from termcolor import colored, cprint
from requests.sessions import Session
from requests.exceptions import HTTPError

DATETIME_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'
UPLOAD_URL = 'https://api.pinata.cloud/pinning/pinFileToIPFS'
UPLOAD_JSON_URL = 'https://api.pinata.cloud/pinning/pinJSONToIPFS'

base_dir = os.path.dirname(os.path.abspath(__file__))
http = Session()


class Config():
    def __init__(self, filename):
        self.filename = filename
        self.data = None

    def __getitem__(self, key):
        if self.data is None:
            with open(self.filename) as conf:
                self.data = json.load(conf)
        return self.data[key]

    def get(self, key):
        if self.data is None:
            with open(self.filename) as conf:
                self.data = json.load(conf)
        return self.data.get(key)


CONFIG = Config(os.path.join(base_dir, 'config.json'))
HEADERS = {'Authorization': f'Bearer {CONFIG["api_key"]}'}


def set_up():
    num_files_list = []
    m = 1

    for dir in ['images', 'metadata']:
        os.makedirs(os.path.join(base_dir, 'output', dir), exist_ok=True)

    for folder in CONFIG['folders']:
        current_path = os.path.join(base_dir, folder)
        os.makedirs(current_path, exist_ok=True)

        num_files = len(os.listdir(current_path))
        m *= num_files
        num_files_list.append(num_files)
        print(f'{current_path} contains {num_files} file(s)')

    possible_combinations = 1
    for i in num_files_list:
        possible_combinations *= i

    if m == 0:
        cprint('Please make sure that all folders contain images', 'red')
        return False
    # If the 'amount' value is higher than the number of possible combinations
    # ...then this can't be done

    if CONFIG['amount'] > m:
        shutil.rmtree('output')
        cprint(f"Can't make {CONFIG['amount']} images, there are only {possible_combinations} possible combinations",
               'red')
        return False

    cprint(f"Successfully created {CONFIG['amount']} images", 'green')
    return True


def get_items():
    p = list(product(*[os.listdir(os.path.join(base_dir, folder))
                       for folder in CONFIG['folders']]))

    name = CONFIG['project_name']

    image_files = []
    images_data = {}
    for num in range(CONFIG['amount']):
        idx = random.randint(0, len(p) - 1)
        item = [[f, p[idx][i]] for i, f in enumerate(CONFIG['folders'])]
        img_metadata, buffer = create_image(item, num)

        img_metadata['num'] = num
        image_files.append(('file', (
            'images/' + img_metadata['name'] + '.png',
            buffer.getvalue()
        )))
        images_data[img_metadata['name']] = img_metadata
        p.pop(idx)

    description = CONFIG['description']

    count, response = 0, None
    while count <= 3:
        response = upload(image_files, metadata={
            'keyvalues': images_data,
            'name': name,
            'description': description
        }, desc='Images')
        if response is None:
            # Keep trying
            count += 1
        break
    if count >= 3 or response is None:
        cprint('Images upload failed', 'red')
        return
    else:
        cprint(f'Images upload response: {json.dumps(response, indent=2)}',
               'green')

    ipfs_hash = response['IpfsHash']
    # the https version
    # ipfs_url = f'https://gateway.pinata.cloud/ipfs/{ipfs_hash}'
    ipfs_url = f'ipfs://{ipfs_hash}'
    timestamp = datetime.strptime(response['Timestamp'], DATETIME_FMT)

    json_files = []
    for img_name, desc in images_data.items():
        # Encoded URL of the image
        desc['image'] = ipfs_url + '/' + quote(img_name + '.png')
        desc['date'] = int(timestamp.timestamp() * 1000)

        img_num = desc["num"]
        desc_copy = desc.copy()
        del desc_copy['num']

        json_file = os.path.join(base_dir, 'output', 'metadata', f'{img_num}.json')
        with open(json_file, 'w') as outfile:
            json.dump(desc_copy, outfile, ensure_ascii=False, indent=4)
        json_files.append(
            ('file', (f'json/{img_num}.json', open(json_file, 'rb')))
        )
    json_metadata = {
        'name': f'{name} metadata',
        'description': description
    }
    # Upload the JSON, keep trying 3 times
    count, response = 0, None
    while count <= 3:
        response = upload(json_files, json_metadata, 'JSON')
        if response is None:
            # Keep trying
            count += 1
        break

    if count >= 3 or response is None:
        cprint('JSON upload failed', 'red')
        return
    else:
        cprint(f'JSON upload response: {json.dumps(response, indent=2)}',
               'green')

def create_image(image_items, num):
    attributes = []
    new_image = None
    for folder, image in sorted(image_items):
        with Image.open(os.path.join(base_dir, folder, image)) as img:
            if new_image is None:
                new_image = Image.new(mode='RGBA', size=img.size)
            new_image.paste(img, (0, 0), mask=img)
            attr_data = {
                'trait_value': ' '.join(folder.split(' ')[:-1]).capitalize(),
                'value': os.path.splitext(image)[0]
            }
            attributes.append(attr_data)

    new_image.save(os.path.join(base_dir, 'output', 'images', f'{num}.png'))

    img_metadata = {
        'description': CONFIG['description'],
        'name': f'{CONFIG["project_name"]}#{num}',
        'attributes': attributes
    }

    json_file_name = os.path.join(base_dir, 'output', 'metadata', f'{num}.json')
    with open(json_file_name, 'w') as outfile:
        json.dump(img_metadata, outfile, ensure_ascii=False, indent=4)

    buffer = BytesIO()
    new_image.save(buffer, format='PNG')
    return img_metadata, buffer


def upload(file_list, metadata, desc=None):
    """Upload files and its metadata"""

    cprint(f'Uploading {desc}', 'green')
    try:
        resp = http.post(
            UPLOAD_URL,
            files=file_list,
            headers=HEADERS,
            json={'pinataMetadata': json.dumps(metadata)},
            timeout=10.0
        )
        resp.raise_for_status()
        result = resp.json()
        return result
    except HTTPError as exc:
        try:
            cprint(f'HTTP ERROR: {exc.response.json()}', 'red')
        except:
            cprint(f'HTTP ERROR: {exc}', 'red')
    except Exception as exc:
        cprint(f'ERROR: {exc}', 'red')


if __name__ == '__main__':
    if set_up():
        get_items()

