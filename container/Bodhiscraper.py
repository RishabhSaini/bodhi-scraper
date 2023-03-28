import json
from bodhi.client.bindings import BodhiClient
import re
import requests
import xml.etree.ElementTree as ET
import lzma

# Get frequencyupdateinfo.json from all current releases of fedora and rhel and combine them to make a single json respectively.

#Architecture Decision
#Option 1 
#Push file to ostree-config (Example: fcos/rhcos/scos config git repos)

#Option 2
#Push file directly to yum/dnf repos so it works better with Image Builder when creating bootable OS images
    
class Frequency(dict):
    def __init__(self, build_time, alias, name):
        self.build_time = build_time
        self.alias = alias
        self.name = name

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return '<Frequency Name: {} Alias: {} BuildTime: {}>'.format(self.name, self.alias, self.build_time)

    def toDict(self):
        return {"build_time": self.build_time, "alias": self.alias, "name": self.name}

#Use library
def parse_nevr(s):
    EPOCH_RE = re.compile(r"^(\d+):")
    ss = s.split('-')
    while (len(ss) < 3):
        ss.append("")
    r = ss.pop()
    v = ss.pop()
    e = ""
 
    m = EPOCH_RE.search(v)
    if m:  # N-E:V-R
        e = m.group(1)
        v = v[len(m.group(0)):]
    else:
        m = EPOCH_RE.search(ss[0])
        if m:  # E:N-V-R
            e = m.group(1)
            ss[0] = ss[0][len(m.group(0)):]
    return ("-".join(ss))

def process_data(query, result_file):
    freq = {}
    for update in query:
        if 'F' not in update['release']['name']:
            continue
        pkg_name = update['title']
        build_time = update['date_stable']
        release = "fc" + update['release']['version']
        for build in update['builds']:
            nvr = build['nvr']
            pkg_name = parse_nevr(nvr)
            name = pkg_name + "." + release
            if name not in freq.keys():
                freq[name] = {Frequency(build_time, update['alias'], nvr)}
            else:
                freq[name].add(Frequency(build_time, update['alias'], nvr))

    
    for key in freq:
        freq[key] = list(freq[key])
        for i, item in list(enumerate(freq[key])):
            freq[key][i] = item.toDict()
    
    json_munch = json.dumps(freq)

    with open(result_file, "w") as f:
        f.write(json_munch)

def init():
    client = BodhiClient()
    rows_per_page = 30
    query = client.get_releases(rows_per_page=rows_per_page, state='current')
    pages = query.pages
    releases = []
    
    #Get all release names
    for page_no in list(range(1, pages+1)):
        releases.append(client.get_releases(page=page_no, rows_per_page=rows_per_page, state='current')['releases'])
    
    #Flatten the pages and Filter the releases
    releases = [release for page in releases for release in page if release.id_prefix == "FEDORA"]

    #Download the frequenctupdateinfo.json for each release and combine
    update_infos = []
    for release in releases:
        repomd = requests.get(f"https://fedora.mirror.garr.it/fedora/linux/updates/{release.version}/Everything/source/tree/repodata/repomd.xml")
        repomd_root = ET.fromstring(repomd.text)
        ns = re.match(r'{.*}', repomd_root.tag).group(0)
        for data in repomd_root.findall(f"{ns}data"):
            if data.attrib['type'] == 'frequencyupdateinfo':
                location = data.find(f"{ns}location").attrib['href']
                zipped_update_info = requests.get(f"https://fedora.mirror.garr.it/fedora/linux/updates/{release.version}/Everything/source/tree/{location}")
                filename = f"frequency_update_info_{release.version}.xml.xz"
                open(filename, 'wb').write(zipped_update_info.content)
                update_info = lzma.open(filename)
                update_info_json = json.load(update_info)
                for update in update_info_json:
                    update_infos.append(update)
    
    #process and save file
    process_data(update_infos, "processed_frequency.json")

    #Option 1 
    #Push file to ostree-config (Example: fcos/rhcos/scos config git repos)
    
    #Option 2
    #Push file directly to yum/dnf repos so it works better with Image Builder when creating bootable OS images
    

init()
