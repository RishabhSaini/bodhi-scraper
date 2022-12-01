import json
import sys
from bodhi.client.bindings import BodhiClient
import pandas as pd
import re
from concurrent.futures import ProcessPoolExecutor
import time
import threading
import os

rows_per_page = '30'
query_file = "query.json"
result_file = "json.json"
client = BodhiClient()
query = client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable')
pages = query.pages
#pages_list = list(range(1, pages + 1))
#file_lock = threading.Lock()
#open(query_file, "w").close()

def get_a_page(page_no):
    qe = json.dumps(client.query(rows_per_page=rows_per_page, content_type='rpm', releases='__current__, __pending__', status='stable', page=page_no)['updates'])
    with file_lock:    
        with open(query_file, 'a') as file:
            file.write(qe)
            file.write(',') 

def setup_threads(pages_list):
    with ProcessPoolExecutor() as executor:
        return executor.map(get_a_page, pages_list)

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

def process_data():
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
                pkg_name = pkg_name + "." + rows['release']['stable_tag']
                if pkg_name not in freq.keys():
                    freq[pkg_name] = [build_time]
                else:
                    freq[pkg_name].append(build_time)

    json_munch = json.dumps(freq)

    sys.stdout=open(result_file, "w")
    print(json_munch)
    sys.stdout.close()
    return

def main_thing():
    with open(query_file, 'a') as f:
        f.write('[')

    start = time.perf_counter()
    setup_threads(pages_list)
    finish = time.perf_counter()
    print("Time taken: ", finish - start)

    with open(query_file, 'rb+') as f:
        f.seek(-1, os.SEEK_END)
        f.truncate()

    with open(query_file, 'a') as f:
        f.write(']')

process_data()
