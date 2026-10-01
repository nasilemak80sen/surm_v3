

def render_navigation() -> None:
    """
    Render page navigation.

    Navigation remains intentionally simple and reliable; workflow state and
    form guidance are provided by the shared workflow engine.
    """

    page_names = list(PAGE_DEFINITIONS.keys())

    # Repository resume has priority over the page that rendered the load
    # action. Consume it once, then let normal sidebar navigation take over.
    pending_page = st.session_state.pop("_pending_navigation_page", None)
    if pending_page in PAGE_DEFINITIONS:
        st.session_state["current_page"] = pending_page

    selected_page = st.session_state.get("current_page", page_names[0])
    if selected_page not in PAGE_DEFINITIONS:
        selected_page = page_names[0]

    is_workflow_page = selected_page in WORKFLOW_PAGES
    workflow_index = WORKFLOW_PAGES.index(selected_page) if is_workflow_page else -1
    title = selected_page.split(" ", 1)[-1]
    descriptions = {
        "🗂️ Study Repository": "Browse, view, and edit saved field studies.",
        "📋 Overview": "A live view of study progress, outputs, and the next recommended step.",
        "👥 Team": "Maintain the people and roles contributing to this study.",
        "📖 How to Use": "A concise guide to the SURM study workflow.",
        "1️⃣ Uncertainties": "Select and refine the subsurface uncertainties relevant to the study.",
        "2️⃣ Key Decisions": "Define the decisions that the uncertainty assessment must support.",
        "3️⃣ Impact Assessment": "Rate uncertainty degree and decision impact to build the ranking.",
        "4️⃣ Key Uncertainties": "Review the ranked uncertainties and select those for resolution planning.",
        "5️⃣ Resolution List": "Map selected uncertainties to the actions that can resolve them.",
        "6️⃣ Resolution Planner": "Turn selected resolution actions into an owned, trackable workplan.",
        "7️⃣ Risk Register": "Convert study outputs into a managed risk register and bowtie view.",
        "📄 PRA Output": "Review the read-only portfolio output generated from the risk register.",
        "📊 Intelligence": "See study health, risk portfolio, actions, barriers, QA and traceability in one place.",
        "🛡️ Barrier Management": "Manage owners, status, verification and administrative health for Bowtie barriers.",
        "✅ Assurance & Review": "Control study lifecycle, review decisions, validation and approval readiness.",
        "🕘 Revision History": "Inspect immutable study revisions and compare durable changes.",
    }

    if is_workflow_page:
        session = cast(dict[str, Any], dict(st.session_state))
        stage_key = stage_results(session)[workflow_index].key
        allowed, reason = validate_stage(session, stage_key)
        if not allowed:
            render_page_frame(title, descriptions.get(selected_page, "SURM study workspace."), step=workflow_index + 1)
            st.warning(f"This stage is not ready yet. {reason}")
            current = current_stage(session)
            st.info(f"Current study stage: **{current.label}** — {current.guidance}")