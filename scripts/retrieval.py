#!/usr/bin/env python3
"""TF-IDF 检索器（无 BERT / 无 GPU），支持分类硬过滤 + 软排序。"""
from collections import Counter
import math
import re

import jieba

SENT_BREAK = re.compile(r"[。！？!?；;\n]+")


def tokenize(text):
    return [t.lower() for t in jieba.cut(text or "") if t.strip()]


class TfIdfIndex:
    def __init__(self, docs):
        self.docs = docs
        self.tokens = [tokenize(d) for d in docs]
        self.df = Counter()
        for toks in self.tokens:
            for term in set(toks):
                self.df[term] += 1
        self.N = max(len(docs), 1)
        self.vectors = [self._tfidf(t) for t in self.tokens]

    def _tfidf(self, tokens):
        tf = Counter(tokens)
        return {term: cnt * math.log((self.N + 1) / (self.df[term] + 1))
                for term, cnt in tf.items()}

    def _cos(self, q, d):
        if not q or not d:
            return 0.0
        common = set(q) & set(d)
        if not common:
            return 0.0
        dot = sum(q[t] * d[t] for t in common)
        nq = math.sqrt(sum(v * v for v in q.values()))
        nd = math.sqrt(sum(v * v for v in d.values()))
        return dot / (nq * nd + 1e-12)

    def query(self, text, top_k=5, mask=None):
        q = self._tfidf(tokenize(text))
        scored = []
        for i, dv in enumerate(self.vectors):
            if mask is not None and not mask[i]:
                continue
            scored.append((i, self._cos(q, dv)))
        scored.sort(key=lambda x: -x[1])
        return [(idx, score) for idx, score in scored[:top_k] if score > 0]
