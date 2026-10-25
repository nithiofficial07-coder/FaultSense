"""Knowledge Base browser and dataset ingestion page for FaultSense in enterprise light theme."""

from pathlib import Path
import tempfile
import streamlit as st

from fault_sense.schema import SubsystemType
from src.knowledge_base.manager import KnowledgeBaseManager


def render_knowledge_base_page() -> None:
    """Renders the case repository search browser, file ingestion workflow, and FAISS indexing controls."""
    st.markdown("## Elevator Fault Knowledge Base")
    st.markdown("Search verified field maintenance logs, OEM service bulletins, and benchmark diagnostic cases.")

    kb_manager = KnowledgeBaseManager()
    kb_manager.seed_initial_data_if_empty()

    tab_browse, tab_import, tab_vector = st.tabs(["Browse & Search Cases", "Ingest New Datasets", "Vector Store (FAISS)"])

    with tab_browse:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

        with c1:
            query = st.text_input("Search query (symptom, root cause, fault code)", value="", placeholder="e.g. door sill debris, overvoltage...")
        with c2:
            search_mode = st.selectbox("Search Mode", ["Semantic Vector (FAISS)", "Lexical (FTS5)"])
        with c3:
            subsystem_filter = st.selectbox(
                "Subsystem",
                options=["All"] + [s.value for s in SubsystemType],
                format_func=lambda x: "All Subsystems" if x == "All" else x.replace("_", " ").title(),
            )
        with c4:
            prov_filter = st.selectbox(
                "Provenance",
                options=["All Records", "Verified Only", "Synthetic Only"],
            )

        # Map filters
        sub_arg = None if subsystem_filter == "All" else subsystem_filter
        synth_arg = None
        if prov_filter == "Verified Only":
            synth_arg = False
        elif prov_filter == "Synthetic Only":
            synth_arg = True

        if search_mode == "Semantic Vector (FAISS)" and query.strip():
            from src.retrieval.index_manager import IndexManager
            idx_mgr = IndexManager()
            idx_mgr.initialize(repo=kb_manager.repo, force_rebuild=False)
            vec_results = idx_mgr.search(
                query=query.strip(),
                top_k=50,
                subsystem=sub_arg,
                is_synthetic=synth_arg,
            )
            # Retrieve full case models by case_id
            cases = []
            score_map = {}
            for vr in vec_results:
                c = kb_manager.repo.get(vr.case_id)
                if c:
                    cases.append(c)
                    score_map[c.case_id] = vr.score
            st.caption(f"Showing **{len(cases)}** semantically matched records via FAISS Cosine Similarity.")
        else:
            cases = kb_manager.search_cases(
                query=query.strip() if query.strip() else None,
                subsystem=sub_arg,
                is_synthetic=synth_arg,
                limit=50,
            )
            score_map = {}
            st.caption(f"Showing **{len(cases)}** matching records.")

        if not cases:
            st.info("No fault cases match your current filter criteria.")
        else:
            for c in cases:
                prov_badge = "Synthetic Benchmark" if c.is_synthetic else "Verified Incident"
                prov_color = "#4169A8" if c.is_synthetic else "#3F7D62"

                header_text = f"**{c.case_id}** — {c.source_title} [{c.subsystem.replace('_', ' ').title()} | {c.fault_code}]"

                with st.expander(header_text):
                    m_col1, m_col2 = st.columns([3, 1])
                    with m_col1:
                        st.markdown(f"**Source Document**: {c.source_title} *(Ref: `{c.source_reference}`)*")
                        st.markdown(f"**Origin Category**: `{c.source_type}` | **Verification**: `{c.verification_status}`")
                    with m_col2:
                        st.markdown(
                            f"<span style='color: {prov_color}; font-weight: 600; font-size: 0.85rem;'>● {prov_badge}</span>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("---")
                    st.markdown(f"**Observed Symptoms**:\n" + "\n".join([f"- {s}" for s in c.symptoms]))
                    st.markdown(f"**Confirmed Root Cause**: {c.confirmed_root_cause}")
                    st.markdown(f"**Corrective Action Taken**: {c.corrective_action}")

                    if c.telemetry_summary:
                        st.markdown(f"**Telemetry Summary**: `{c.telemetry_summary}`")

                    if c.metadata:
                        st.caption(f"Metadata: {c.metadata}")

    with tab_import:
        st.markdown("### Ingest CSV or JSON Fault Datasets")
        st.markdown(
            "Upload files to validate against schema rules, check for duplicates, and insert into the persistent SQLite knowledge base."
        )

        uploaded_file = st.file_uploader(
            "Choose a CSV or JSON file",
            type=["csv", "json"],
            help="Files up to 50MB with case_id, subsystem, fault_code, symptoms, root cause, etc.",
        )

        if uploaded_file is not None:
            if st.button("Validate & Import Dataset", icon=":material/upload_file:", type="primary"):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(uploaded_file.name).suffix
                ) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = Path(tmp_file.name)

                try:
                    with st.spinner("Processing ingestion pipeline and duplicate checking..."):
                        summary = kb_manager.import_file(tmp_path)

                    if summary.valid_records > 0:
                        st.success(
                            f"Imported **{summary.valid_records}** valid cases successfully! "
                            f"(Duplicates: {summary.duplicate_records}, Rejected: {summary.rejected_records})"
                        )
                    else:
                        st.warning(
                            f"No valid records imported. Duplicates: {summary.duplicate_records}, Rejected: {summary.rejected_records}."
                        )

                    # Display formatted summary report
                    st.code(summary.formatted_report(), language="text")

                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

    with tab_vector:
        st.markdown("### FAISS Vector Indexing & Synchronization")
        st.markdown(
            "Dense vector embeddings index elevator fault cases for sub-millisecond semantic similarity search."
        )

        from src.retrieval.index_manager import IndexManager

        idx_mgr = IndexManager()
        idx_mgr.initialize(repo=kb_manager.repo, force_rebuild=False)
        v_status = idx_mgr.get_status()

        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            st.metric("Total Indexed Vectors", str(v_status["total_vectors"]))
        with vc2:
            st.metric("Vector Dimension", f"{v_status['dimension']} dims", "all-MiniLM-L6-v2")
        with vc3:
            st.metric("Similarity Metric", "Cosine Similarity", "IndexFlatIP + L2 norm")

        st.caption(f"**Index Directory**: `{v_status['index_dir']}`")

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("Rebuild Vector Index (Atomic)", icon=":material/refresh:", type="primary"):
                with st.spinner("Embedding fault cases and building FAISS index..."):
                    count = kb_manager.rebuild_vector_index(idx_mgr)
                    st.success(f"FAISS index successfully rebuilt with **{count}** vectors!")
                    st.rerun()

        with col_act2:
            if st.button("Synchronize Unindexed Cases", icon=":material/sync:", type="secondary"):
                with st.spinner("Scanning for unindexed records in SQLite..."):
                    added = kb_manager.sync_vector_index(idx_mgr)
                    if added > 0:
                        st.success(f"Synchronized **{added}** newly added cases into vector index.")
                        st.rerun()
                    else:
                        st.info("All knowledge base records are already synchronized.")

        with st.expander("Vector Index File Manifest"):
            st.json(v_status)
