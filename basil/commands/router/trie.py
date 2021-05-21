from __future__ import annotations
from typing import Dict, Optional, Any, Generator, Tuple


class Trie(object):
    def __init__(self, key: str = "", parent: Optional[Trie] = None, char: str = ""):
        self._key: str = key
        self._char: str = char
        self._children: Dict[str, Trie] = {}
        self._parent: Optional[Trie] = parent
        self._value: Optional[Any] = None
        self._len = 0

    def insert(self, key: str, value: Any, replace: bool = False):
        cur_node: Trie = self

        for c in key:
            try:
                cur_node = cur_node._children[c]
            except KeyError:
                cur_node._children[c] = Trie(cur_node._key + c, cur_node, c)
                cur_node = cur_node._children[c]

        if cur_node._value is not None:
            if not replace:
                raise KeyError(key + " already present in trie")
        else:
            self._len += 1

        cur_node._value = value

    def suffixes(self, reverse: bool = False) -> Generator[Tuple[str, Any], None, None]:
        if self._value is not None:
            yield (self._key, self._value)

        for _, v in sorted(
            self._children.items(), key=lambda kv: kv[0], reverse=reverse
        ):
            yield from v.suffixes()

    def search(self, prefix: str = "") -> Generator[Tuple[str, Any], None, None]:
        return self._find_node(prefix).suffixes()

    def keys(self, prefix: str = "") -> Generator[str, None, None]:
        return map(lambda kv: kv[0], self.search(prefix))

    def values(self, prefix: str = "") -> Generator[Any, None, None]:
        return map(lambda kv: kv[1], self.search(prefix))

    def contains_prefix(self, prefix: str) -> bool:
        try:
            self._find_node(prefix)
            return True
        except KeyError:
            return False

    def _find_node(self, key: str) -> Trie:
        cur_node: Trie = self

        for c in key:
            try:
                cur_node = cur_node._children[c]
            except KeyError:
                raise KeyError(key) from None

        return cur_node

    def _cleanup_child(self, char: str):
        del self._children[char]
        if len(self._children) == 0 and self._value is not None:
            return self._parent._cleanup_child(self._char)

    def __len__(self) -> int:
        return self._len

    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        return self.suffixes()

    def __reversed__(self) -> Generator[Tuple[str, Any], None, None]:
        return self.suffixes(True)

    def __getitem__(self, key: str) -> Any:
        return self._find_node(key)._value

    def __setitem__(self, key: str, value: Any):
        return self.insert(key, value, True)

    def __delitem__(self, key: str):
        if len(key) == 0:
            raise KeyError("cannot delete empty string")

        node = self._find_node(key)

        if node._value is None:
            raise KeyError(key)

        node._value = None
        if len(node._children) == 0:
            node._parent._cleanup_child(node._char)
        self._len -= 1

    def __contains__(self, key: str) -> bool:
        try:
            return self._find_node(key)._value is not None
        except KeyError:
            return False
