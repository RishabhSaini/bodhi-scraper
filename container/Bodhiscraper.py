import json
import sys
from bodhi.client.bindings import BodhiClient
import re
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
import time
import os

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

def get_a_page(client, query_file, page_no, rows_per_page, lock):
    qe = json.dumps(client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable', page=page_no)['updates'])
    with lock:    
        with open(query_file, 'a') as file:
            file.write(qe)
            file.write(',') 

def setup_threads(client, query_file, pages_list, rows_per_page):
    with Manager() as manager:
        lock = manager.Lock()
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(get_a_page, client, query_file, page_no, rows_per_page, lock) for page_no in pages_list]
            for future in futures:
                result = future.result()

def process_data(query_file, result_file):
    query = json.load(open(query_file))
    freq = {}
    for page_no in range(len(query)):
        for rows in query[page_no]:
            if 'F' not in rows['release']['name']:
                continue
            pkg_name = rows['title']
            build_time = rows['date_stable']
            release = "fc" + rows['release']['version']
            for build in rows['builds']:
                nvr = build['nvr']
                pkg_name = parse_nevr(nvr)
                name = pkg_name + "." + release
                if name not in freq.keys():
                    freq[name] = {Frequency(build_time, rows['alias'], nvr)}
                else:
                    freq[name].add(Frequency(build_time, rows['alias'], nvr))

    
    for key in freq:
        freq[key] = list(freq[key])
        for i, item in list(enumerate(freq[key])):
            freq[key][i] = item.toDict()
    
    json_munch = json.dumps(freq)

    sys.stdout=open(result_file, "w")
    print(json_munch)
    sys.stdout.close()
    return

#Run a container by mounting volume

def init():
    rows_per_page = '10'
    query_file = "./query.json"
    result_file = "./resultOfQuery.json"
    client = BodhiClient()
    query = client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable')
    pages = query.pages
    pages_list = list(range(1, pages + 1))
    open(query_file, "w").close()

    with open(query_file, 'a') as f:
        f.write('[')

    start = time.perf_counter()
    setup_threads(client, query_file, pages_list, rows_per_page)
    finish = time.perf_counter()
    print("Time taken: ", finish - start)

    with open(query_file, 'rb+') as f:
        f.seek(-1, os.SEEK_END)
        f.truncate()

    with open(query_file, 'a') as f:
        f.write(']')

    process_data(query_file, result_file)

init()
