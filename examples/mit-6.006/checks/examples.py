"""Verify every number in short_plan.json's worked examples (MIT 6.006 demo series).

Run: python checks/examples.py   (prints the values; any mismatch raises AssertionError)
"""
import heapq
import itertools

# ---------------------------------------------------------------- s01: BFS level sets
# Lecture 9's own exercise: "Run breadth-first search from s in the graph in Example 3".
G3 = {"a": ["s", "b"], "b": ["a"], "s": ["a", "c"], "c": ["s", "d", "e"],
      "d": ["c", "e", "f"], "e": ["c", "d", "f"], "f": ["d", "e"], "g": []}
assert all(u in G3[v] for u in G3 for v in G3[u]), "undirected: adjacency must be symmetric"


def bfs_levels(adj, s):
    levels, parent = [[s]], {s: None}
    while levels[-1]:
        nxt = []
        for u in levels[-1]:
            for v in adj[u]:
                if v not in parent:
                    parent[v] = u
                    nxt.append(v)
        levels.append(nxt)
    return levels[:-1], parent


levels, parent = bfs_levels(G3, "s")
dist = {v: i for i, L in enumerate(levels) for v in L}
assert levels == [["s"], ["a", "c"], ["b", "d", "e"], ["f"]]
assert parent == {"s": None, "a": "s", "c": "s", "b": "a", "d": "c", "e": "c", "f": "d"}
assert "g" not in dist                                   # unreachable: distance infinity
edges = {frozenset((u, v)) for u in G3 for v in G3[u]}
assert len(G3) == 8 and len(edges) == 8
assert sum(len(G3[u]) for u in G3) == 2 * len(edges) == 16   # each edge checked from both ends
assert all(abs(dist[u] - dist[v]) <= 1 for u, v in map(tuple, edges))  # no edge skips a level
same_level = sorted("".join(sorted(e)) for e in edges if len({dist[x] for x in e}) == 1)
assert same_level == ["de"]


def brute_dist(adj, s, t):                               # second route: try every simple path
    best = None
    stack = [(s, (s,))]
    while stack:
        u, path = stack.pop()
        if u == t:
            best = len(path) - 1 if best is None else min(best, len(path) - 1)
            continue
        stack += [(v, path + (v,)) for v in adj[u] if v not in path]
    return best


assert all(brute_dist(G3, "s", v) == dist[v] for v in dist)
assert brute_dist(G3, "s", "g") is None
# practice: add edge s-f
G3p = {k: list(v) for k, v in G3.items()}
G3p["s"].append("f")
G3p["f"].append("s")
dist_p = {v: i for i, L in enumerate(bfs_levels(G3p, "s")[0]) for v in L}
assert dist_p["f"] == 1 and all(dist_p[v] == dist[v] for v in dist if v != "f")
print("s01 levels", levels, "parents", parent, "g unreachable; 16 adjacency checks")

# ---------------------------------------------------------------- s02: Dijkstra relaxation
ROADS = {("Home", "Cafe"): 2, ("Home", "Park"): 5, ("Home", "Work"): 10, ("Cafe", "Park"): 1,
         ("Cafe", "Shop"): 6, ("Park", "Shop"): 2, ("Park", "Work"): 6, ("Shop", "Work"): 1}


def adjacency(roads):
    adj = {}
    for (u, v), w in roads.items():
        assert w >= 0
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))
    return adj


def dijkstra(adj, s):
    d = {v: float("inf") for v in adj}
    d[s] = 0
    done, order, log = set(), [], []
    pq = [(0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        order.append((u, du))
        for v, w in adj[u]:
            if v not in done and du + w < d[v]:
                log.append((u, v, d[v], du + w))
                d[v] = du + w
                heapq.heappush(pq, (d[v], v))
    return d, order, log


ADJ = adjacency(ROADS)
d, order, log = dijkstra(ADJ, "Home")
INF = float("inf")
assert order == [("Home", 0), ("Cafe", 2), ("Park", 3), ("Shop", 5), ("Work", 6)]
assert log == [("Home", "Cafe", INF, 2), ("Home", "Park", INF, 5), ("Home", "Work", INF, 10),
               ("Cafe", "Park", 5, 3), ("Cafe", "Shop", INF, 8),
               ("Park", "Shop", 8, 5), ("Park", "Work", 10, 9),
               ("Shop", "Work", 9, 6)]


def all_routes(adj, s, t):
    out, stack = [], [(s, (s,), 0)]
    while stack:
        u, path, cost = stack.pop()
        if u == t:
            out.append((cost, path))
            continue
        stack += [(v, path + (v,), cost + w) for v, w in adj[u] if v not in path]
    return sorted(out)


assert sum(1 for _, _, before, _ in log if before != INF) == 4        # lowered an already finite estimate
routes = all_routes(ADJ, "Home", "Work")
assert routes[0] == (6, ("Home", "Cafe", "Park", "Shop", "Work"))
assert routes[1][0] > 6                                   # the fastest route is unique
assert all(min(c for c, _ in all_routes(ADJ, "Home", v)) == d[v] for v in ADJ if v != "Home")
# practice: Cafe-Park takes 4 minutes instead of 1
SLOW = {**ROADS, ("Cafe", "Park"): 4}
d2, order2, _ = dijkstra(adjacency(SLOW), "Home")
assert d2["Work"] == 8 and all_routes(adjacency(SLOW), "Home", "Work")[0] == (8, ("Home", "Park", "Shop", "Work"))
print("s02 pop order", order, "relaxations", len(log), "fastest", routes[0])

# ---------------------------------------------------------------- s03: Fibonacci call tree -> DAG
calls = {0: 1, 1: 1}
for n in range(2, 41):
    calls[n] = calls[n - 1] + calls[n - 2] + 1             # one call for n, plus both recursions
F = [0, 1]
while len(F) < 42:
    F.append(F[-1] + F[-2])
assert all(calls[n] == 2 * F[n + 1] - 1 for n in calls)


def tree(n):                                             # the actual call tree of fib(n)
    return (n, [] if n < 2 else [tree(n - 1), tree(n - 2)])


def count(t):
    return 1 + sum(count(c) for c in t[1])


def labels(t):
    return [t[0]] + [x for c in t[1] for x in labels(c)]


T5 = tree(5)
assert count(T5) == calls[5] == 15
assert sorted(set(labels(T5))) == [0, 1, 2, 3, 4, 5]          # only 6 distinct subproblems
assert {k: labels(T5).count(k) for k in range(6)} == {5: 1, 4: 1, 3: 2, 2: 3, 1: 5, 0: 3}
dag_edges = [(k, k - j) for k in range(2, 6) for j in (1, 2)]
assert len(dag_edges) == 8 < 2 * 5                               # n+1 vertices, < 2n edges
tree_edges = count(T5) - 1
assert tree_edges == 14
assert F[:6] == [0, 1, 1, 2, 3, 5] and F[5] == 5
assert calls[30] == 2_692_537 and F[30] == 832_040
additions = 30 - 1                                             # bottom up: F(2) .. F(30)
print("s03 fib(5) calls", calls[5], "subproblems 6, dag edges 8; fib(30) calls", calls[30], "vs 31 subproblems,", additions, "additions; F(30) =", F[30])
assert calls[6] == 25                                          # practice
