class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        if self.parent.setdefault(x, x) != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        self.parent[self.find(y)] = self.find(x)


def build_clusters(pairs, records, match_func):

    uf = UnionFind()

    for r1, r2 in pairs:
        if match_func(records[r1], records[r2]):
            uf.union(r1, r2)

    clusters = {}
    cluster_map = {}
    cluster_id = 0

    for record_id in records:
        root = uf.find(record_id)

        if root not in clusters:
            clusters[root] = cluster_id
            cluster_id += 1

        cluster_map[record_id] = clusters[root]

    return cluster_map
