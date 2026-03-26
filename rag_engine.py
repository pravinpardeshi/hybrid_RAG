import sqlite3
import json
import numpy as np
import re
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from database import DB_NAME

model = SentenceTransformer('all-MiniLM-L6-v2')

def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return text.split()


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def retrieve_policies_old(query, amount=None, category=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    sql = "SELECT title, content, embedding FROM policies WHERE 1=1"
    params = []

    if amount is not None:
        sql += " AND min_amount <= ? AND max_amount >= ?"
        params.extend([amount, amount])

    if category:
        sql += " AND category = ?"
        params.append(category)

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    if not rows:
        return []

    # -------- BM25 --------
    docs = [r[1] for r in rows]
    tokenized_docs = [tokenize(d) for d in docs]
    bm25 = BM25Okapi(tokenized_docs)
    bm25_scores = bm25.get_scores(tokenize(query))

    # -------- Embeddings --------
    query_vec = model.encode(query)
    emb_scores = []

    for r in rows:
        emb = np.array(json.loads(r[2]))
        emb_scores.append(cosine_similarity(query_vec, emb))

    # -------- Hybrid Score --------
    hybrid_scores = []

    for i in range(len(rows)):
        score = 0.6 * bm25_scores[i] + 0.4 * emb_scores[i]
        hybrid_scores.append(score)

    ranked_indices = np.argsort(hybrid_scores)[::-1]

    results = []
    query_terms = set(tokenize(query))

    for i in ranked_indices[:3]:
        title, content, _ = rows[i]
        tokens = set(tokenize(content))
        matched = list(query_terms.intersection(tokens))

        results.append((title, content, matched, float(hybrid_scores[i])))

    return results


def retrieve_policies(query, amount=None, category=None, weight=0.6):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    sql = "SELECT title, content, embedding FROM policies WHERE 1=1"
    params = []

    if amount is not None:
        sql += " AND min_amount <= ? AND max_amount >= ?"
        params.extend([amount, amount])

    if category:
        sql += " AND category = ?"
        params.append(category)

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    if not rows:
        return []

    # BM25
    docs = [r[1] for r in rows]
    tokenized_docs = [tokenize(d) for d in docs]
    bm25 = BM25Okapi(tokenized_docs)
    bm25_scores = bm25.get_scores(tokenize(query))

    # Semantic
    query_vec = model.encode(query)

    results = []
    query_terms = set(tokenize(query))

    for i, (title, content, emb_str) in enumerate(rows):
        bm25_score = float(bm25_scores[i])

        # Fallback if embedding missing
        if not emb_str:
            semantic_score = 0
            hybrid_score = bm25_score
        else:
            emb = np.array(json.loads(emb_str))
            semantic_score = float(cosine_similarity(query_vec, emb))
            hybrid_score = weight * bm25_score + (1 - weight) * semantic_score

        tokens = set(tokenize(content))
        matched = list(query_terms.intersection(tokens))

        results.append({
            "title": title,
            "content": content,
            "matched": matched,
            "bm25": round(bm25_score, 3),
            "semantic": round(semantic_score, 3),
            "hybrid": round(hybrid_score, 3)
        })

    results.sort(key=lambda x: x["hybrid"], reverse=True)
    return results[:3]


