"""Sealed independent declarative oracle; never imported by the application."""


def witnesses(edges, source, target):
    return tuple(index for index, edge in enumerate(edges)
                 if edge[0] == source and edge[1] == target)


def accepted(edges, source, target):
    return len(witnesses(edges, source, target)) > 0


def degrees(edges):
    return {"sources": [sum(left == source for left, _ in edges) for source in range(4)],
            "targets": [sum(right == target for _, right in edges) for target in range(4)]}


def competitors(edges, source, target):
    count = len(witnesses(edges, source, target))
    return {"same_bridge_exists": count > 0,
            "source_has_any_bridge": any(left == source for left, _ in edges),
            "target_has_any_bridge": any(right == target for _, right in edges),
            "exactly_one_matching_bridge": count == 1}
