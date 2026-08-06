"""纯 Python 图算法工具（无 networkx 依赖）。

为 S4 拓扑分析与 S5 缺口识别提供：密度、连通性、聚类、k-core、社团发现、
介数中心性（Brandes）、结构约束（Burt constraint）。局部子图 G 经 S3 规模控制
后规模可控，这些算法在小图上足够使用。
"""
from collections import defaultdict, deque
from itertools import combinations


def build_adjacency(node_ids, edges):
    """构建无向邻接表与带权邻接表。edges: [{source,target,weight}]。"""
    adj = {n: set() for n in node_ids}
    wadj = {n: defaultdict(float) for n in node_ids}
    nid = set(node_ids)
    for e in edges:
        u, v = e["source"], e["target"]
        if u not in nid or v not in nid or u == v:
            continue
        w = float(e.get("weight", 1.0))
        adj[u].add(v)
        adj[v].add(u)
        wadj[u][v] += w
        wadj[v][u] += w
    return adj, wadj


def degree(adj, v):
    return len(adj[v])


def neighborhood_density(adj, v):
    """节点 v 的邻域密度 = 邻居间实际边数 / 可连接对数。"""
    nbrs = list(adj[v])
    k = len(nbrs)
    if k < 2:
        return 0.0
    actual = sum(1 for a, b in combinations(nbrs, 2) if b in adj[a])
    return actual / (k * (k - 1) / 2)


def weighted_density(wadj, v):
    """带权密度 = 邻居间实际边权之和 / 可连接对数（弱连接=低密度）。"""
    nbrs = list(wadj[v].keys())
    k = len(nbrs)
    if k < 2:
        return 0.0
    total = 0.0
    for a, b in combinations(nbrs, 2):
        total += wadj[a].get(b, 0.0)
    return total / (k * (k - 1) / 2)


def clustering_coefficient(adj, v):
    """局部聚类系数。"""
    return neighborhood_density(adj, v)


def connected_components(adj, nodes):
    seen, comps = set(), []
    for s in nodes:
        if s in seen:
            continue
        comp, q = [], deque([s])
        seen.add(s)
        while q:
            u = q.popleft()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    q.append(w)
        comps.append(comp)
    return comps


def connectivity_stats(adj, nodes):
    """连通性类指标：连通分量数、最大分量占比、可达对比例。"""
    comps = connected_components(adj, nodes)
    n = len(nodes)
    if n == 0:
        return {"components": 0, "largest_ratio": 0.0, "reachable_pair_ratio": 0.0}
    largest = max((len(c) for c in comps), default=0)
    reachable_pairs = sum(len(c) * (len(c) - 1) / 2 for c in comps)
    total_pairs = n * (n - 1) / 2 or 1
    return {
        "components": len(comps),
        "largest_ratio": largest / n,
        "reachable_pair_ratio": reachable_pairs / total_pairs,
    }


def avg_shortest_path_normalized(adj, nodes):
    """最大连通分量内平均最短路（BFS），按分量规模归一化到 [0,1] 占位表达。"""
    comps = connected_components(adj, nodes)
    if not comps:
        return 0.0
    comp = max(comps, key=len)
    if len(comp) < 2:
        return 0.0
    total, cnt = 0, 0
    cset = set(comp)
    for s in comp:
        dist = {s: 0}
        q = deque([s])
        while q:
            u = q.popleft()
            for w in adj[u]:
                if w in cset and w not in dist:
                    dist[w] = dist[u] + 1
                    q.append(w)
        total += sum(dist.values())
        cnt += len(dist) - 1
    avg = total / cnt if cnt else 0.0
    return avg / max(len(comp) - 1, 1)


def k_core_numbers(adj):
    """k-core 分解：返回每个节点的核心层级（peeling 算法）。"""
    deg = {v: len(adj[v]) for v in adj}
    core = {}
    remaining = set(adj.keys())
    cur_adj = {v: set(adj[v]) for v in adj}
    k = 0
    while remaining:
        k = max(k, min(deg[v] for v in remaining))
        peeled = [v for v in remaining if deg[v] <= k]
        if not peeled:
            k += 1
            continue
        for v in peeled:
            core[v] = k
            remaining.discard(v)
            for w in cur_adj[v]:
                if w in remaining:
                    deg[w] -= 1
            cur_adj[v] = set()
    return core


def communities_label_propagation(adj, nodes, max_iter=30):
    """标签传播社团发现（确定性 tie-break，保证可复现）。"""
    label = {v: i for i, v in enumerate(sorted(nodes))}
    order = sorted(nodes)
    for _ in range(max_iter):
        changed = False
        for v in order:
            if not adj[v]:
                continue
            counts = defaultdict(int)
            for w in adj[v]:
                counts[label[w]] += 1
            best = max(sorted(counts.items()), key=lambda kv: (kv[1], -kv[0]))[0]
            if label[v] != best:
                label[v] = best
                changed = True
        if not changed:
            break
    # 归一化社团编号
    remap, nid = {}, 0
    for v in order:
        if label[v] not in remap:
            remap[label[v]] = nid
            nid += 1
        label[v] = remap[label[v]]
    return label


def betweenness_centrality(adj, nodes):
    """Brandes 算法（无权）。返回归一化介数中心性。"""
    bc = dict.fromkeys(nodes, 0.0)
    for s in nodes:
        stack, pred = [], {w: [] for w in nodes}
        sigma = dict.fromkeys(nodes, 0.0)
        sigma[s] = 1.0
        dist = {w: -1 for w in nodes}
        dist[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = dict.fromkeys(nodes, 0.0)
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]
    n = len(nodes)
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return {v: bc[v] * scale for v in nodes}


def burt_constraint(wadj, v):
    """Burt 结构约束系数：值越低 → 越接近结构洞位置（桥接机会越大）。"""
    nbrs = list(wadj[v].keys())
    if not nbrs:
        return None
    deg_w = sum(wadj[v].values()) or 1.0

    def p(i, j):
        s = sum(wadj[i].values()) or 1.0
        return wadj[i].get(j, 0.0) / s

    constraint = 0.0
    for j in nbrs:
        indirect = 0.0
        for qn in nbrs:
            if qn == j or qn == v:
                continue
            indirect += p(v, qn) * p(qn, j)
        constraint += (p(v, j) + indirect) ** 2
    return constraint
