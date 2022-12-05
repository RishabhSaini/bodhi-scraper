import json
import sys
from bodhi.client.bindings import BodhiClient
import pandas as pd
import re
from concurrent.futures import ProcessPoolExecutor
import time
from multiprocessing import Lock
import os


def get_a_page(client, query_file, page_no, rows_per_page):
    #print("Getting page:", page_no)
    qe = json.dumps(client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable', page=page_no)['updates'])
    with lock:    
        with open(query_file, 'a') as file:
            file.write(qe)
            file.write(',') 

def init_processes(file_lock):
    global lock
    lock = file_lock

def setup_threads(client, query_file, pages_list, rows_per_page):
    print("Setting up threads")
    file_lock = Lock()
    with ProcessPoolExecutor(initializer=init_processes, initargs=(file_lock, )) as executor:
        futures = [executor.submit(get_a_page, client, query_file, page_no, rows_per_page) for page_no in pages_list]
        for future in futures:
            result = future.result()

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

def process_data(query_file, result_file):
    query = json.load(open(query_file))
    freq = {}
    for i in range(len(query)):
        for rows in query[i]:
            pkg_name = rows['title']
            build_time = rows['date_stable']
            name_arr = []
            if ' ' in pkg_name:
                name_arr = pkg_name.split(" ")
            else:
                name_arr.append(pkg_name)
            for name in name_arr:
                pkg_name = parse_nevr(name)
                pkg_name = pkg_name + "." + rows['release']['dist_tag']
                if pkg_name not in freq.keys():
                    freq[pkg_name] = {Frequency(build_time, rows['alias'], name)}
                else:
                    freq[pkg_name].add(Frequency(build_time, rows['alias'], name))

    
    for key in freq:
        freq[key] = list(freq[key])
        for i, item in list(enumerate(freq[key])):
            freq[key][i] = item.toDict()
    
    json_munch = json.dumps(freq)

    sys.stdout=open(result_file, "w")
    print(json_munch)
    sys.stdout.close()
    return

def init():
    rows_per_page = '5'
    query_file = "../parsed/view1Query.json"
    result_file = "../results/result1Query.json"
    client = BodhiClient()
    #query = client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable')
    pages = 500#query.pages
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
