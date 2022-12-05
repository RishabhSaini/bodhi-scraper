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
        return '<Frequency {}>'.format(self.name)

    def toDict(self):
        return {"build_time": self.build_time, "alias": self.alias, "name": self.name}

a = {Frequency('a', 'a', 'a')}
a.add(Frequency('b', 'b', 'b'))
a.add(Frequency('b', 'b', 'a'))

b = {}
b['first'] = a

for key in b:
    b[key] = list(b[key])
    print(b[key])
