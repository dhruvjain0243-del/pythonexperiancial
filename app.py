"""
StudyVerse Offline — Streamlit Application
===========================================
A high-end, multipage Streamlit frontend for:
  • Library — Upload, extract, index, and manage PDFs
  • Search Notes — Hybrid / Semantic / Keyword search with citations
  • Practice Arena — Auto-generated flashcard quiz from documents
  • Revision Hub — SM-2 Spaced Repetition due-card review
  • Progress & Streaks — Study analytics and streak tracking

Backend: FastAPI at http://127.0.0.1:8000
Fallback: Direct service imports when FastAPI is not running
"""
from __future__ import annotations

import time
from io import BytesIO

import requests
import streamlit as st

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StudyVerse Offline",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://127.0.0.1:8000"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global Reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}

/* ── Main container ── */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* ── Hero banner ── */
.sv-hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    color: white;
}
.sv-hero h1 { font-size: 2rem; font-weight: 700; margin: 0; }
.sv-hero p  { font-size: 1rem; opacity: 0.8; margin: 0.3rem 0 0; }

/* ── Metric cards ── */
.sv-metric {
    background: #f0f7ff;
    border: 1px solid #c8e0f7;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.sv-metric .num { font-size: 2.2rem; font-weight: 700; color: #1a3a5c; }
.sv-metric .lbl { font-size: 0.8rem; color: #5a7a9a; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Status pill badges ── */
.pill {
    display: inline-block;
    padding: 0.2rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.pill-green  { background: #e6f9f0; color: #1a6b42; border: 1px solid #a3d9b5; }
.pill-amber  { background: #fff7e6; color: #8a5700; border: 1px solid #f5cc80; }
.pill-red    { background: #fde8e8; color: #9b1c1c; border: 1px solid #f5a5a5; }
.pill-blue   { background: #e8f0fe; color: #1a56db; border: 1px solid #93b4f7; }
.pill-gray   { background: #f3f4f6; color: #555e6e; border: 1px solid #d1d5db; }

/* ── Direct Answer Banner ── */
.sv-answer-box {
    background: linear-gradient(135deg, #f0f7ff 0%, #e0effe 100%);
    border: 1px solid #bfdbfe;
    border-left: 5px solid #2563eb;
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
}
.sv-answer-box .title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #1d4ed8;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.sv-answer-box .direct-text {
    font-size: 1.15rem;
    font-weight: 600;
    line-height: 1.6;
    color: #0f172a;
    margin-bottom: 0.8rem;
}
.sv-answer-box .keypoint-item {
    font-size: 0.95rem;
    color: #334155;
    line-height: 1.5;
    margin: 0.35rem 0;
    padding-left: 0.5rem;
}
.sv-answer-box .meta {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.8rem;
    padding-top: 0.5rem;
    border-top: 1px dashed #cbd5e1;
}

/* ── Result cards ── */
.sv-result {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
}
.sv-result:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.sv-result .rank { font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; }
.sv-result .score { font-size: 0.85rem; font-weight: 600; color: #2563eb; }
.sv-result .text  { font-size: 0.95rem; line-height: 1.7; color: #1e293b; margin: 0.5rem 0; }
.sv-result .cite  { font-size: 0.78rem; color: #64748b; }



/* ── Flashcard ── */
.sv-card {
    background: linear-gradient(135deg, #fefefe 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
}
.sv-card .label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; color: #94a3b8; text-transform: uppercase; margin-bottom: 1rem; }
.sv-card .qtext { font-size: 1.2rem; font-weight: 600; color: #1e293b; line-height: 1.5; }
.sv-card .atext { font-size: 1rem; color: #334155; line-height: 1.6; }

/* ── Streak badge ── */
.streak-badge {
    background: linear-gradient(135deg, #f97316, #fb923c);
    color: white;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
}
.streak-badge small { display: block; font-size: 0.8rem; font-weight: 400; opacity: 0.9; }

/* ── Section titles ── */
.sv-section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

/* ── SM-2 grade buttons ── */
.grade-btn { border-radius: 10px !important; }

/* ── Connected / Disconnected indicator ── */
.online-dot  { color: #16a34a; }
.offline-dot { color: #dc2626; }

/* ── Table override ── */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# API CLIENT — thin wrapper; handles connectivity check
# ═══════════════════════════════════════════════════════════════════
def _get(path: str, **kwargs) -> requests.Response | None:
    """GET request to FastAPI; returns None on connection error."""
    try:
        return requests.get(f"{API_BASE}{path}", timeout=10, **kwargs)
    except requests.exceptions.ConnectionError:
        return None


def _post(path: str, **kwargs) -> requests.Response | None:
    """POST request to FastAPI; returns None on connection error."""
    try:
        return requests.post(f"{API_BASE}{path}", timeout=60, **kwargs)
    except requests.exceptions.ConnectionError:
        return None


def _delete(path: str, **kwargs) -> requests.Response | None:
    """DELETE request to FastAPI; returns None on connection error."""
    try:
        return requests.delete(f"{API_BASE}{path}", timeout=10, **kwargs)
    except requests.exceptions.ConnectionError:
        return None


def backend_online() -> bool:
    """Checks if the FastAPI backend is reachable."""
    r = _get("/health")
    return r is not None and r.status_code == 200


def api_list_documents() -> list[dict]:
    r = _get("/documents")
    if r and r.status_code == 200:
        data = r.json()
        return data if isinstance(data, list) else data.get("documents", [])
    return []


def api_upload_documents(files: list) -> list[dict]:
    file_tuples = [("files", (f.name, f.read(), "application/pdf")) for f in files]
    r = _post("/documents/upload", files=file_tuples)
    if r and r.status_code in (200, 201):
        data = r.json()
        return data if isinstance(data, list) else data.get("results", [])
    msg = r.json().get("detail", "Upload failed") if r else "Backend offline"
    st.error(f"Upload error: {msg}")
    return []


def api_index_document(doc_id: int) -> dict | None:
    r = _post(f"/documents/{doc_id}/index", json={})
    if r and r.status_code == 200:
        return r.json()
    msg = r.json().get("detail", "Indexing failed") if r else "Backend offline"
    st.error(f"Indexing error: {msg}")
    return None


def api_index_all() -> dict | None:
    r = _post("/documents/index-all", json={})
    if r and r.status_code == 200:
        return r.json()
    msg = r.json().get("detail", "Index-all failed") if r else "Backend offline"
    st.error(f"Index-all error: {msg}")
    return None


def api_delete_document(doc_id: int) -> bool:
    r = _delete(f"/documents/{doc_id}")
    if r and r.status_code == 200:
        return True
    msg = r.json().get("detail", "Delete failed") if r else "Backend offline"
    st.error(f"Delete error: {msg}")
    return False


def api_get_pages(doc_id: int) -> list[dict]:
    r = _get(f"/documents/{doc_id}/pages")
    if r and r.status_code == 200:
        data = r.json()
        return data if isinstance(data, list) else data.get("pages", [])
    return []


def api_search(query: str, mode: str, doc_ids: list[int], top_k: int, min_score: float) -> dict | None:
    r = _post("/search", json={
        "query": query.strip(),
        "mode": mode,
        "document_ids": doc_ids,
        "top_k": top_k,
        "min_score": min_score,
        "include_debug": False,
    })
    if r and r.status_code == 200:
        return r.json()
    if r and r.status_code == 422:
        details = r.json().get("detail", "Validation error")
        st.error(f"Search validation error: {details}")
    elif r:
        msg = r.json().get("detail", "Search failed")
        st.error(f"Search error: {msg}")
    else:
        st.error("Backend offline. Start the FastAPI server and try again.")
    return None


def api_get_progress() -> dict | None:
    r = _get("/progress/summary")
    if r and r.status_code == 200:
        return r.json()
    return None


def api_get_due_cards(limit: int = 50) -> list[dict]:
    r = _get(f"/revision/due?limit={limit}")
    if r and r.status_code == 200:
        return r.json()
    return []


def api_review_card(card_id: int, quality: int) -> dict | None:
    r = _post(f"/revision/review/{card_id}", json={"quality": quality})
    if r and r.status_code == 200:
        return r.json()
    return None


def api_generate_cards(doc_ids: list[int], max_per_doc: int = 10) -> dict | None:
    r = _post("/practice/generate", json={"document_ids": doc_ids, "max_cards_per_doc": max_per_doc})
    if r and r.status_code == 200:
        return r.json()
    msg = r.json().get("detail", "Card generation failed") if r else "Backend offline"
    st.error(f"Practice error: {msg}")
    return None


def api_list_flashcards(doc_id: int | None = None) -> list[dict]:
    url = "/practice/flashcards"
    if doc_id:
        url += f"?document_id={doc_id}"
    r = _get(url)
    if r and r.status_code == 200:
        return r.json()
    return []


def api_delete_flashcard(card_id: int) -> bool:
    r = _delete(f"/practice/flashcards/{card_id}")
    return r is not None and r.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
def status_pill(status: str) -> str:
    mapping = {
        "completed": ("pill-green", "✅ Indexed"),
        "pending":   ("pill-gray",  "⏳ Pending"),
        "warning":   ("pill-amber", "⚠️ Warning"),
        "failed":    ("pill-red",   "❌ Failed"),
    }
    css, label = mapping.get(status, ("pill-gray", status.title()))
    return f'<span class="pill {css}">{label}</span>'


def score_color(pct: float) -> str:
    if pct >= 70: return "🟢"
    if pct >= 40: return "🟡"
    return "🔴"


def metric_card(col, num, label):
    col.markdown(f"""
        <div class="sv-metric">
            <div class="num">{num}</div>
            <div class="lbl">{label}</div>
        </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════
if "current_revision_idx" not in st.session_state:
    st.session_state.current_revision_idx = 0
if "revision_queue" not in st.session_state:
    st.session_state.revision_queue = []
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False
if "quiz_cards" not in st.session_state:
    st.session_state.quiz_cards = []
if "quiz_idx" not in st.session_state:
    st.session_state.quiz_idx = 0
if "quiz_show_answer" not in st.session_state:
    st.session_state.quiz_show_answer = False
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_done" not in st.session_state:
    st.session_state.quiz_done = False


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    online = backend_online()
    status_indicator = "🟢" if online else "🔴"
    status_text = "Backend Online" if online else "Backend Offline"

    st.markdown(f"""
    <div style="background: {'#f0fdf4' if online else '#fef2f2'};
                border: 1px solid {'#bbf7d0' if online else '#fecaca'};
                border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 1rem;">
        <strong>{status_indicator} {status_text}</strong><br>
        <small style="color: #64748b;">{API_BASE}</small>
    </div>
    """, unsafe_allow_html=True)

    if not online:
        st.info("💡 Start the backend:\n```\ncd backend\n.venv\\Scripts\\uvicorn app.main:app --reload\n```")

    st.markdown("---")
    st.markdown("### 🎓 StudyVerse")
    st.caption("Offline academic study assistant")

    page = st.radio(
        "Navigate",
        ["📚 Library", "🔍 Search Notes", "🎯 Practice Arena", "🔁 Revision Hub", "📈 Progress"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("All processing is 100% local. No data leaves your device.")


# ═══════════════════════════════════════════════════════════════════
# PAGE: LIBRARY
# ═══════════════════════════════════════════════════════════════════
if page == "📚 Library":
    st.markdown("""
    <div class="sv-hero">
        <h1>📚 Document Library</h1>
        <p>Upload and manage your academic PDF files for offline semantic search.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload panel ──
    with st.expander("➕ Upload PDFs", expanded=True):
        uploaded = st.file_uploader(
            "Drop PDF files here",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload text-based PDFs. Scanned or image-only PDFs cannot be indexed.",
        )
        col_upload, col_idx_all = st.columns([1, 1])
        if col_upload.button("📤 Upload", type="primary", disabled=not uploaded or not online):
            with st.spinner("Uploading and extracting text…"):
                results = api_upload_documents(list(uploaded))
            if results:
                ok = sum(1 for r in results if r.get("extraction_status") == "completed")
                warn = sum(1 for r in results if r.get("extraction_status") == "warning")
                st.success(f"✅ Uploaded {ok} readable PDF(s)." + (f" ⚠️ {warn} may be scanned/image-only." if warn else ""))
                st.rerun()

        if col_idx_all.button("⚡ Index All", disabled=not online):
            with st.spinner("Indexing all eligible documents…"):
                result = api_index_all()
            if result:
                st.success(f"✅ Indexed {result.get('indexed_document_count', 0)} document(s). Total chunks: {result.get('total_chunks_created', 0)}")
                st.rerun()

    # ── Documents table ──
    st.markdown('<div class="sv-section-title">Your Documents</div>', unsafe_allow_html=True)
    docs = api_list_documents()

    if not docs:
        st.info("📭 No documents yet. Upload a text-based PDF to get started.")
    else:
        for doc in docs:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 1.5, 1.5])
                c1.markdown(f"**{doc['filename']}**")

                extraction_status = doc.get("extraction_status", "pending")
                is_indexed = doc.get("is_indexed", False)
                display_status = "completed" if is_indexed else extraction_status
                c2.markdown(status_pill(display_status), unsafe_allow_html=True)

                chunks = doc.get("chunks_count", 0)
                pages = doc.get("page_count", 0)
                c3.markdown(f"<small>{pages} pages · {chunks} chunks</small>", unsafe_allow_html=True)

                doc_id = doc["id"]

                with c4:
                    if st.button("⚡ Index", key=f"idx_{doc_id}", disabled=not online or extraction_status != "completed"):
                        with st.spinner(f"Indexing {doc['filename']}…"):
                            result = api_index_document(doc_id)
                        if result:
                            st.success(f"✅ {result.get('chunks_created', 0)} chunks indexed")
                            st.rerun()

                with c5:
                    if st.button("🗑️", key=f"del_{doc_id}", help="Delete document", disabled=not online):
                        with st.spinner("Deleting…"):
                            ok = api_delete_document(doc_id)
                        if ok:
                            st.success("Deleted")
                            st.rerun()

                # Page text expander
                if is_indexed:
                    with st.expander(f"📖 View extracted text — {doc['filename']}"):
                        pages_data = api_get_pages(doc_id)
                        if pages_data:
                            page_sel = st.selectbox(
                                "Select page",
                                [p["page_number"] for p in pages_data],
                                key=f"psel_{doc_id}",
                            )
                            for p in pages_data:
                                if p["page_number"] == page_sel:
                                    st.text_area(
                                        f"Page {page_sel} text",
                                        value=p.get("text", ""),
                                        height=250,
                                        key=f"ptxt_{doc_id}_{page_sel}",
                                        label_visibility="collapsed",
                                    )
                st.divider()


# ═══════════════════════════════════════════════════════════════════
# PAGE: SEARCH NOTES
# ═══════════════════════════════════════════════════════════════════
elif page == "🔍 Search Notes":
    st.markdown("""
    <div class="sv-hero">
        <h1>🔍 Search Notes</h1>
        <p>Find the original source text in your indexed PDFs using semantic and keyword search.</p>
    </div>
    """, unsafe_allow_html=True)

    docs = api_list_documents()
    indexed_docs = [d for d in docs if d.get("is_indexed")]

    col_q, col_mode = st.columns([3, 1])
    query = col_q.text_input(
        "Ask a question or enter a formula:",
        placeholder="e.g. What is Newton's second law? or F = ma",
    )
    mode = col_mode.selectbox(
        "Search mode",
        ["hybrid", "semantic", "keyword"],
        format_func=lambda x: {"hybrid": "🔀 Hybrid (Recommended)", "semantic": "🧠 Semantic", "keyword": "🔑 Keyword"}.get(x, x),
    )

    col_k, col_score = st.columns(2)
    top_k = col_k.slider("Results to show (Top-K)", 1, 10, 5)
    min_score = col_score.slider("Minimum relevance (0 = show all)", 0.0, 1.0, 0.0, 0.05)

    st.markdown("**🗂️ Search in documents:**")
    if not indexed_docs:
        st.warning("⚠️ No indexed documents. Go to Library → Index a PDF first.")
        selected_ids = []
    else:
        col_sel_all, _ = st.columns([1, 4])
        if col_sel_all.button("Select All"):
            for d in indexed_docs:
                st.session_state[f"doc_chk_{d['id']}"] = True

        doc_cols = st.columns(min(len(indexed_docs), 4))
        selected_ids = []
        for i, d in enumerate(indexed_docs):
            key = f"doc_chk_{d['id']}"
            if key not in st.session_state:
                st.session_state[key] = True
            checked = doc_cols[i % 4].checkbox(d["filename"], key=key)
            if checked:
                selected_ids.append(d["id"])

    search_btn = st.button("🔍 Search", type="primary", disabled=not query.strip() or not selected_ids or not online)

    if search_btn:
        with st.spinner("Searching your local indexes…"):
            result = api_search(query, mode, selected_ids, top_k, min_score)

        if result:
            results = result.get("results", [])
            st.markdown("---")
            n = len(results)
            filtered = result.get("filtered_by_min_score", False)

            if filtered:
                st.warning("⚠️ Matches were found but none met your minimum relevance. Lower the slider to see them.")
            elif n == 0:
                st.info("🔍 No matching content found. Try different keywords or index more documents.")
            else:
                # ── Direct Answer Synthesis at Top ──
                direct_ans = result.get("direct_answer")
                if direct_ans and direct_ans.get("direct_answer"):
                    ans_text = direct_ans.get("direct_answer")
                    key_pts = direct_ans.get("key_points", [])
                    src_page = direct_ans.get("primary_source_page")
                    src_file = direct_ans.get("primary_source_filename")
                    conf = direct_ans.get("confidence", "medium").upper()
                    
                    points_html = ""
                    if key_pts:
                        points_html = "<div style='margin-top: 0.6rem;'>" + "".join([f"<div class='keypoint-item'>• {pt}</div>" for pt in key_pts]) + "</div>"
                        
                    meta_info = f"Source: <strong>{src_file}</strong> (Page {src_page}) &nbsp;·&nbsp; Confidence: {conf}" if src_file else ""
                    
                    st.markdown(f"""
                    <div class="sv-answer-box">
                        <div class="title">💡 Direct Answer</div>
                        <div class="direct-text">{ans_text}</div>
                        {points_html}
                        <div class="meta">{meta_info}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f'<div class="sv-section-title">📖 {n} Source Extract{"s" if n != 1 else ""} — Retrieved from Documents</div>', unsafe_allow_html=True)
                for r in results:
                    score_pct = r.get("final_score_percent", 0.0)
                    sem_pct = r.get("semantic_score_percent")
                    kw_pct = r.get("keyword_score_percent")

                    score_details = ""
                    if sem_pct is not None:
                        score_details += f" · Semantic: {sem_pct:.1f}%"
                    if kw_pct is not None:
                        score_details += f" · Keyword: {kw_pct:.1f}%"

                    st.markdown(f"""
                    <div class="sv-result">
                        <div class="rank">Result #{r['rank']}</div>
                        <div class="score">{score_color(score_pct)} {score_pct:.1f}% relevance{score_details}</div>
                        <div class="text">{r['text']}</div>
                        <div class="cite">📁 {r['filename']} &nbsp;·&nbsp; 📄 Page {r['page_number']} &nbsp;·&nbsp; Chunk {r['chunk_number']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Copy button
                    with st.expander(f"📋 Copy extract — {r['filename']} p.{r['page_number']}"):
                        st.text_area("Extract text", value=r["text"], height=120, key=f"copy_{r['chunk_id']}", label_visibility="collapsed")


# ═══════════════════════════════════════════════════════════════════
# PAGE: PRACTICE ARENA
# ═══════════════════════════════════════════════════════════════════
elif page == "🎯 Practice Arena":
    st.markdown("""
    <div class="sv-hero">
        <h1>🎯 Practice Arena</h1>
        <p>Auto-generated quiz questions from your indexed documents. Test your understanding.</p>
    </div>
    """, unsafe_allow_html=True)

    docs = api_list_documents()
    indexed_docs = [d for d in docs if d.get("is_indexed")]

    # Card generation panel
    with st.expander("⚙️ Generate Practice Cards", expanded=not st.session_state.quiz_cards):
        if not indexed_docs:
            st.warning("⚠️ No indexed documents. Go to Library → Index a PDF first.")
        else:
            gen_cols = st.columns([3, 1, 1])
            gen_doc_names = {d["filename"]: d["id"] for d in indexed_docs}
            chosen_filenames = gen_cols[0].multiselect(
                "Source documents",
                list(gen_doc_names.keys()),
                default=list(gen_doc_names.keys())[:2],
            )
            max_per = gen_cols[1].number_input("Max cards per doc", 1, 30, 8)
            if gen_cols[2].button("⚡ Generate", type="primary", disabled=not chosen_filenames or not online):
                chosen_ids = [gen_doc_names[n] for n in chosen_filenames]
                with st.spinner("Extracting questions from documents…"):
                    result = api_generate_cards(chosen_ids, max_per_doc=int(max_per))
                if result:
                    st.session_state.quiz_cards = result.get("cards", [])
                    st.session_state.quiz_idx = 0
                    st.session_state.quiz_show_answer = False
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_done = False
                    st.success(f"✅ Generated {result['total_generated']} practice cards!")
                    st.rerun()

    # ── Quiz interface ──
    cards = st.session_state.quiz_cards
    if not cards:
        all_cards = api_list_flashcards()
        if all_cards:
            st.markdown("---")
            st.markdown(f"**{len(all_cards)} existing cards** — Select documents above and generate to start a fresh quiz session.")

            with st.expander("📋 Browse all existing cards"):
                for c in all_cards[:20]:
                    with st.container():
                        q_col, a_col, del_col = st.columns([4, 4, 1])
                        q_col.markdown(f"**Q:** {c['question']}")
                        a_col.markdown(f"**A:** {c['answer'][:200]}")
                        if del_col.button("🗑️", key=f"del_card_{c['id']}", help="Delete card"):
                            api_delete_flashcard(c["id"])
                            st.rerun()
        else:
            st.info("🃏 No practice cards yet. Select documents above and click Generate to create your first quiz.")
    else:
        idx = st.session_state.quiz_idx
        total = len(cards)

        if st.session_state.quiz_done or idx >= total:
            # Results screen
            score = st.session_state.quiz_score
            pct = round(score / total * 100) if total else 0
            st.markdown(f"""
            <div style="text-align:center; padding: 3rem;">
                <div style="font-size:4rem;">{"🏆" if pct >= 70 else "📚"}</div>
                <h2>Quiz Complete!</h2>
                <p style="font-size:1.5rem; font-weight:700; color: {'#16a34a' if pct >= 70 else '#d97706'};">{score}/{total} correct ({pct}%)</p>
                <p>{"Excellent work! Keep up the momentum." if pct >= 70 else "Keep practising! Review wrong answers in the Revision Hub."}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Restart Quiz", type="primary"):
                st.session_state.quiz_idx = 0
                st.session_state.quiz_show_answer = False
                st.session_state.quiz_score = 0
                st.session_state.quiz_done = False
                st.rerun()
        else:
            card = cards[idx]
            # Progress bar
            st.progress((idx) / total, text=f"Card {idx + 1} of {total}")

            # Question card
            st.markdown(f"""
            <div class="sv-card">
                <div class="label">❓ Question</div>
                <div class="qtext">{card['question']}</div>
            </div>
            """, unsafe_allow_html=True)

            if card.get("context"):
                with st.expander("📖 Source context"):
                    st.caption(card["context"])

            if not st.session_state.quiz_show_answer:
                if st.button("👁️ Reveal Answer", type="primary", use_container_width=True):
                    st.session_state.quiz_show_answer = True
                    st.rerun()
            else:
                # Answer card
                st.markdown(f"""
                <div class="sv-card" style="background: linear-gradient(135deg, #f0fdf4, #dcfce7);">
                    <div class="label">✅ Answer</div>
                    <div class="atext">{card['answer']}</div>
                </div>
                """, unsafe_allow_html=True)
                st.caption(f"📁 {card.get('document_id', '?')} · Page {card.get('page_number', '?')}")

                st.markdown("**Did you get it right?**")
                c1, c2 = st.columns(2)
                if c1.button("✅ Correct", type="primary", use_container_width=True):
                    st.session_state.quiz_score += 1
                    st.session_state.quiz_idx += 1
                    st.session_state.quiz_show_answer = False
                    if st.session_state.quiz_idx >= total:
                        st.session_state.quiz_done = True
                    st.rerun()
                if c2.button("❌ Incorrect", use_container_width=True):
                    st.session_state.quiz_idx += 1
                    st.session_state.quiz_show_answer = False
                    if st.session_state.quiz_idx >= total:
                        st.session_state.quiz_done = True
                    st.rerun()

        if st.button("⏭️ Skip to end"):
            st.session_state.quiz_done = True
            st.rerun()


# ═══════════════════════════════════════════════════════════════════
# PAGE: REVISION HUB (SM-2 Spaced Repetition)
# ═══════════════════════════════════════════════════════════════════
elif page == "🔁 Revision Hub":
    st.markdown("""
    <div class="sv-hero">
        <h1>🔁 Revision Hub</h1>
        <p>Spaced repetition review — Study smarter by revisiting what matters most today.</p>
    </div>
    """, unsafe_allow_html=True)

    # Load due cards on page open
    if st.button("🔄 Load / Refresh Due Cards"):
        st.session_state.revision_queue = api_get_due_cards(limit=50)
        st.session_state.current_revision_idx = 0
        st.session_state.show_answer = False
        st.rerun()

    # Auto-load on first visit
    if not st.session_state.revision_queue:
        st.session_state.revision_queue = api_get_due_cards(limit=50)
        st.session_state.current_revision_idx = 0
        st.session_state.show_answer = False

    queue = st.session_state.revision_queue
    idx = st.session_state.current_revision_idx

    if not queue:
        st.balloons()
        st.success("🎉 **All done for today!** No cards are due right now. Come back later or generate more practice cards.")
    elif idx >= len(queue):
        score_display = f"{idx} cards reviewed"
        st.markdown(f"""
        <div style="text-align:center; padding: 2rem;">
            <div style="font-size:3rem;">🎊</div>
            <h2>Session Complete!</h2>
            <p style="color: #16a34a; font-weight: 600;">{score_display}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Start another session"):
            st.session_state.revision_queue = api_get_due_cards(limit=50)
            st.session_state.current_revision_idx = 0
            st.session_state.show_answer = False
            st.rerun()
    else:
        card = queue[idx]
        remaining = len(queue) - idx

        # Progress
        st.progress(idx / len(queue), text=f"Progress: {idx}/{len(queue)} cards reviewed · {remaining} remaining")

        # Card metadata
        meta_c1, meta_c2, meta_c3 = st.columns(3)
        meta_c1.metric("Repetitions", card.get("repetitions", 0))
        meta_c2.metric("Interval", f"{card.get('interval', 1)} day(s)")
        meta_c3.metric("Ease Factor", f"{card.get('easiness_factor', 2.5):.2f}")

        # Question card
        st.markdown(f"""
        <div class="sv-card">
            <div class="label">❓ Question</div>
            <div class="qtext">{card['question']}</div>
        </div>
        """, unsafe_allow_html=True)

        if card.get("context"):
            with st.expander("📖 Source context"):
                st.caption(card["context"])

        if not st.session_state.show_answer:
            if st.button("👁️ Show Answer", type="primary", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()
        else:
            # Answer
            st.markdown(f"""
            <div class="sv-card" style="background: linear-gradient(135deg, #f0fdf4, #dcfce7);">
                <div class="label">✅ Answer</div>
                <div class="atext">{card['answer']}</div>
            </div>
            """, unsafe_allow_html=True)

            # SM-2 Grade buttons
            st.markdown("**Rate your recall** *(affects next review interval)*")
            grade_cols = st.columns(4)

            grade_map = [
                (0, "❌ Again",     "Forgot completely — reset",          "secondary"),
                (3, "😓 Hard",      "Remembered with difficulty",         "secondary"),
                (4, "😊 Good",      "Correct after slight hesitation",    "primary"),
                (5, "⚡ Easy",      "Recalled perfectly",                  "primary"),
            ]

            for i, (quality, label, tooltip, btn_type) in enumerate(grade_map):
                with grade_cols[i]:
                    if st.button(label, key=f"grade_{quality}", help=tooltip, type=btn_type, use_container_width=True):
                        result = api_review_card(card["id"], quality)
                        if result:
                            next_days = result.get("interval", 1)
                            msg_map = {0: "Reset", 3: "See in 1+ day(s)", 4: f"See in {next_days} day(s)", 5: f"See in {next_days} day(s)"}
                            st.toast(f"✅ Rated: {label} — {msg_map.get(quality, '')}")
                        st.session_state.current_revision_idx += 1
                        st.session_state.show_answer = False
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# PAGE: PROGRESS & STREAKS
# ═══════════════════════════════════════════════════════════════════
elif page == "📈 Progress":
    st.markdown("""
    <div class="sv-hero">
        <h1>📈 Progress & Streaks</h1>
        <p>Track your study momentum, card mastery, and retention over time.</p>
    </div>
    """, unsafe_allow_html=True)

    if not online:
        st.warning("Backend is offline. Start the FastAPI server to view your progress.")
    else:
        prog = api_get_progress()
        if not prog:
            st.info("No progress data yet. Start by indexing documents and reviewing flashcards.")
        else:
            # ── Streak ──
            streak = prog.get("study_streak_days", 0)
            sc1, sc2, sc3 = st.columns([1, 3, 1])
            with sc2:
                st.markdown(f"""
                <div class="streak-badge">
                    🔥 {streak} Day{"s" if streak != 1 else ""} Streak
                    <small>Keep reviewing daily to maintain your streak!</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Metric row ──
            m1, m2, m3, m4 = st.columns(4)
            metric_card(m1, prog.get("total_documents", 0), "Documents")
            metric_card(m2, prog.get("total_indexed_chunks", 0), "Indexed Chunks")
            metric_card(m3, prog.get("total_flashcards", 0), "Total Cards")
            metric_card(m4, prog.get("due_today", 0), "Due Today 📅")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Card mastery breakdown ──
            st.markdown('<div class="sv-section-title">📊 Card Mastery Breakdown</div>', unsafe_allow_html=True)
            total_cards = prog.get("total_flashcards", 0)
            mastered = prog.get("cards_mastered", 0)
            learning = prog.get("cards_learning", 0)
            new_cards = prog.get("cards_new", 0)

            if total_cards > 0:
                col_m, col_l, col_n = st.columns(3)
                with col_m:
                    st.markdown(f"""
                    <div class="sv-metric">
                        <div class="num" style="color: #16a34a;">🏆 {mastered}</div>
                        <div class="lbl">Mastered (3+ reviews)</div>
                    </div>""", unsafe_allow_html=True)
                with col_l:
                    st.markdown(f"""
                    <div class="sv-metric">
                        <div class="num" style="color: #d97706;">📖 {learning}</div>
                        <div class="lbl">Still Learning</div>
                    </div>""", unsafe_allow_html=True)
                with col_n:
                    st.markdown(f"""
                    <div class="sv-metric">
                        <div class="num" style="color: #2563eb;">🆕 {new_cards}</div>
                        <div class="lbl">New (not studied)</div>
                    </div>""", unsafe_allow_html=True)

                # Progress bar visualization
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Mastery Distribution:**")
                if mastered > 0:
                    st.progress(mastered / total_cards, text=f"Mastered: {mastered}/{total_cards} ({mastered/total_cards*100:.0f}%)")
            else:
                st.info("No flashcards yet. Generate practice cards from your indexed documents.")

            # ── Retention ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sv-section-title">🎯 Review Performance</div>', unsafe_allow_html=True)
            r1, r2 = st.columns(2)
            retention = prog.get("retention_rate_percent", 100.0)
            total_reviews = prog.get("total_reviews_completed", 0)

            with r1:
                st.markdown(f"""
                <div class="sv-metric">
                    <div class="num" style="color: {'#16a34a' if retention >= 70 else '#d97706'};">{retention:.0f}%</div>
                    <div class="lbl">Retention Rate</div>
                </div>""", unsafe_allow_html=True)
            with r2:
                st.markdown(f"""
                <div class="sv-metric">
                    <div class="num">{total_reviews}</div>
                    <div class="lbl">Total Reviews Done</div>
                </div>""", unsafe_allow_html=True)

            if retention >= 90:
                st.success("🌟 Excellent retention! You're mastering your material efficiently.")
            elif retention >= 70:
                st.info("📚 Good retention. Keep reviewing regularly to push towards mastery.")
            elif total_reviews > 0:
                st.warning("🔧 Low retention. Focus on difficult cards and revisit source material.")
