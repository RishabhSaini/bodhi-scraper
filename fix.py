import os
import json
import sys

def insert(file, line, column, text):
    ln, cn = line - 1, column - 1         # offset from human index to Python index
    count = 0                             # initial count of characters
    with open(file, 'r+') as f:           # open file for reading an writing
        for idx, line in enumerate(f):    # for all line in the file
            if idx < ln:                  # before the given line
                count += len(line)        # read and count characters 
            elif idx == ln:               # once at the line                                 
                f.seek(count + cn)        # place cursor at the correct character location
                remainder = f.read()      # store all character afterwards                         
                f.seek(count + cn)        # move cursor back to the correct character location 
                #f.write(text + remainder) # insert text and rewrite the remainder
                sys.stdout=open("correct.json", "w")
                print(remainder[:50])
                sys.stdout.close()

                return                    # You're finished!


insert("query.json", 1, 755621830, "")

query = json.load(open("query.json"))
