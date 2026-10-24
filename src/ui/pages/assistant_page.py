"""Conversational Assistant page for technician follow-up Q&A grounded in investigation evidence."""

import streamlit as st

from src.diagnosis.assistant import DiagnosticAssistantService
from src.storage.repository import InvestigationRepository


def render_assistant_page() -> None:
    """Renders the conversational assistant interface scoped to the selected investigation."""
    st.markdown("## 💬 Diagnostic Conversational Assistant")
    st.markdown(
        "Ask targeted follow-up questions regarding the active fault investigation, physical sensor readings, "
        "and documented OEM corrective procedures."
    )

    repo = InvestigationRepository()
    all_invs = repo.list_all(limit=50)

    if not all_invs:
        st.info("No investigations logged yet. Please execute an investigation from **New Investigation** first.", icon="ℹ️")
        if st.button("🚀 Launch Investigation", type="primary"):
            from src.ui.components.sidebar import navigate_to
            navigate_to("new_investigation")
        return

    # Select investigation to scope the assistant
    inv_ids = [inv["investigation_id"] for inv in all_invs]
    curr_id = st.session_state.get("current_investigation_id")
    default_idx = inv_ids.index(curr_id) if curr_id in inv_ids else 0

    c_sel, c_clear = st.columns([3, 1])
    with c_sel:
        selected_inv_id = st.selectbox(
            "Scoped Investigation Session",
            options=inv_ids,
            index=default_idx,
            format_func=lambda x: f"{x} — Unit: {next((i['elevator_id'] for i in all_invs if i['investigation_id'] == x), '')} [{next((str(i['subsystem']).replace('_', ' ').title() for i in all_invs if i['investigation_id'] == x), '')}]",
        )
    with c_clear:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        chat_key = f"chat_{selected_inv_id}"
        if st.button("🗑️ Reset Chat History", use_container_width=True):
            if chat_key in st.session_state:
                st.session_state[chat_key] = []
            st.rerun()

    inv_data = repo.get(selected_inv_id)
    if not inv_data:
        st.error("Selected investigation could not be retrieved.")
        return

    # Context Header Card
    elv_id = inv_data.get("elevator_id", "UNKNOWN")
    subsystem = str(inv_data.get("subsystem", "")).replace("_", " ").title()
    fault_code = inv_data.get("fault_code") or "N/A"
    rc_summary = inv_data.get("root_cause_hypothesis", "N/A")

    st.markdown(
        f"""
        <div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 3px solid #06B6D4;
                    border-radius: 6px; padding: 10px 16px; margin: 8px 0 16px 0;">
            <div style="font-size: 0.75rem; color: #38BDF8; font-weight: 700; text-transform: uppercase;">
                Active Investigation Scope
            </div>
            <div style="font-size: 0.95rem; color: #F8FAFC; margin-top: 2px;">
                Unit <b>{elv_id}</b> | Subsystem: <b>{subsystem}</b> | Code: <code>{fault_code}</code>
            </div>
            <div style="font-size: 0.82rem; color: #94A3B8; margin-top: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                Primary Hypothesis: {rc_summary}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize chat session state
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                "role": "assistant",
                "content": (
                    f"Hello! I am ready to assist with **{selected_inv_id}** (Elevator `{elv_id}`). "
                    f"My responses are strictly grounded in this session's telemetry, symptoms, and retrieved OEM cases. "
                    f"What technical questions do you have about the diagnosis or corrective steps?"
                ),
                "is_supported": True,
                "cited_cases": inv_data.get("matched_case_ids", []),
            }
        ]

    # Quick Suggestion Chips
    st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: #64748B; margin-bottom: 4px;'>QUICK DIAGNOSTIC PROMPTS</div>", unsafe_allow_html=True)
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    suggested_prompt = None

    with q_col1:
        if st.button("🔧 Recommended Checks", key=f"btn_chk_{selected_inv_id}", use_container_width=True):
            suggested_prompt = "What physical diagnostic checks and multimeter tests are recommended?"
    with q_col2:
        if st.button("🛠️ Corrective Actions", key=f"btn_act_{selected_inv_id}", use_container_width=True):
            suggested_prompt = "What step-by-step corrective actions should I execute?"
    with q_col3:
        if st.button("📡 Telemetry Analysis", key=f"btn_tel_{selected_inv_id}", use_container_width=True):
            suggested_prompt = "Explain the recorded sensor telemetry readings for this unit."
    with q_col4:
        if st.button("⚠️ Safety Advisories", key=f"btn_saf_{selected_inv_id}", use_container_width=True):
            suggested_prompt = "What LOTO and electrical safety precautions must I follow?"

    # Display Chat History
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("cited_cases"):
                cites_str = " ".join(f"`{cid}`" for cid in msg["cited_cases"])
                st.caption(f"📚 Grounded in OEM cases: {cites_str}")
            if msg.get("is_supported") is False:
                st.caption("⚠️ Grounding Note: Out-of-domain or unsupported query rejected by assistant guardrail.")

    # Process Input
    user_input = st.chat_input("Ask a question about this elevator investigation...") or suggested_prompt

    if user_input:
        # Append user message
        st.session_state[chat_key].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate evidence-grounded answer
        assistant_service = DiagnosticAssistantService()
        with st.chat_message("assistant"):
            with st.spinner("Analyzing investigation evidence..."):
                response = assistant_service.answer_question(
                    investigation=inv_data,
                    question=user_input,
                    chat_history=st.session_state[chat_key],
                )

            st.markdown(response["answer"])
            if response.get("cited_cases"):
                cites_str = " ".join(f"`{cid}`" for cid in response["cited_cases"])
                st.caption(f"📚 Grounded in OEM cases: {cites_str}")
            if not response.get("is_supported"):
                st.caption("⚠️ Grounding Note: Inquiry is unsupported by current investigation evidence.")

        # Persist assistant reply
        st.session_state[chat_key].append({
            "role": "assistant",
            "content": response["answer"],
            "is_supported": response.get("is_supported", True),
            "cited_cases": response.get("cited_cases", []),
        })
