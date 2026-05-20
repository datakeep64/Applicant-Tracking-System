import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

REQUIRED_DOCS = {
    "Internship": ["ID Proof", "Resume", "Transcript"],
    "Contract": ["ID Proof", "Resume", "Transcript"],
    "Part-Time": ["ID Proof", "Transcript", "Resume"],
    "Permanent": ["ID Proof", "Resume", "Transcript", "Supporting Letter"]
}

STATUS_TRANSITIONS = {
    "Pending Review": ["Documents Requested", "Under Review", "Incomplete"],
    "Documents Requested": ["Pending Review", "Under Review", "Incomplete"],
    "Under Review": ["Documents Requested", "Completed", "Approved", "Rejected", "Incomplete"],
    "Incomplete": ["Pending Review", "Documents Requested"],
    "Completed": ["Approved", "Rejected"],
    "Approved": [],
    "Rejected": []
}

STATUS_OPTIONS = [
    "Pending Review",
    "Documents Requested",
    "Under Review",
    "Completed",
    "Approved",
    "Rejected",
    "Incomplete"
]

PRIORITY_OPTIONS = ["Low-Priority", "Medium-Priority", "High Priority"]
DOCUMENT_OPTIONS = ["ID Proof", "Resume", "Transcript", "Supporting Letter"]
EXPORT_FILTERS = [
    "All applications",
    "Pending applications",
    "Incomplete applications",
    "Monthly summary"
]
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_stamp():
    return datetime.now().strftime(DATE_FORMAT)


def date_only(dt):
    return dt.strftime("%Y-%m-%d") if isinstance(dt, (datetime, date)) else dt


def init_db():
    conn = sqlite3.connect("applicants.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            application_type TEXT,
            documents TEXT,
            status TEXT,
            remarks TEXT,
            last_contacted TEXT,
            follow_up_required INTEGER,
            follow_up_due TEXT,
            priority TEXT,
            audit_log TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()

    existing_columns = {row[1] for row in cursor.execute("PRAGMA table_info(applicants)").fetchall()}
    for column_name, column_type in [
        ("remarks", "TEXT"),
        ("last_contacted", "TEXT"),
        ("follow_up_required", "INTEGER"),
        ("follow_up_due", "TEXT"),
        ("priority", "TEXT"),
        ("audit_log", "TEXT"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT")
    ]:
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE applicants ADD COLUMN {column_name} {column_type}")
    conn.commit()
    return conn, cursor


def get_required_docs(application_type):
    return REQUIRED_DOCS.get(application_type, ["ID Proof"])


def evaluate_documents(application_type, submitted_documents):
    required = get_required_docs(application_type)
    missing = [doc for doc in required if doc not in submitted_documents]
    return required, missing


def append_audit_entry(cursor, application_id, entry):
    existing = cursor.execute(
        "SELECT audit_log FROM applicants WHERE id = ?",
        (application_id,),
    ).fetchone()[0]
    timestamped_entry = f"{date_only(datetime.now())}: {entry}"
    updated = f"{existing}\n{timestamped_entry}" if existing else timestamped_entry
    cursor.execute(
        "UPDATE applicants SET audit_log = ?, updated_at = ? WHERE id = ?",
        (updated, now_stamp(), application_id),
    )


def load_applications(conn, search_query=None, status_filter=None):
    query = "SELECT * FROM applicants"
    params = []
    where_clauses = []
    if search_query:
        search_query = search_query.strip()
        if search_query.isdigit():
            where_clauses.append("(id = ? OR lower(name) LIKE ?)")
            params.extend([int(search_query), f"%{search_query.lower()}%"])
        else:
            where_clauses.append("lower(name) LIKE ?")
            params.append(f"%{search_query.lower()}%")
    if status_filter and status_filter != "All applications":
        if status_filter == "Pending applications":
            where_clauses.append("status = 'Pending Review'")
        elif status_filter == "Incomplete applications":
            where_clauses.append("status = 'Incomplete'")
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY created_at DESC"
    return pd.read_sql_query(query, conn, params=params)


def get_existing_duplicates(cursor, email, phone):
    rows = cursor.execute(
        "SELECT id, name, email, phone, application_type FROM applicants WHERE email = ? OR phone = ?",
        (email, phone),
    ).fetchall()
    return rows


conn, cursor = init_db()

st.set_page_config(
    page_title="Applicant Tracking & Verification System",
    layout="wide",
)

st.title("Applicant Tracking & Verification System")
st.markdown(
    "Manage applications with automatic document rule checks, officer notes, follow-up tracking, audit history, search, and export reporting."
)

new_app_col, metrics_col = st.columns([3, 1])

with new_app_col:
    st.header("New Application")
    application_type_options = ["Internship", "Contract", "Part-Time", "Permanent"]

    name = st.text_input("Applicant Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    application_type = st.selectbox(
        "Application Type",
        application_type_options,
    )
    required_docs = get_required_docs(application_type)
    st.info(
        f"Required documents for {application_type}: {', '.join(required_docs)}"
    )
    documents = st.multiselect("Documents Submitted", DOCUMENT_OPTIONS)
    missing_docs_live = [doc for doc in required_docs if doc not in documents]
    if missing_docs_live:
        st.warning(
            f"Missing required documents for {application_type}: {', '.join(missing_docs_live)}"
        )
    else:
        st.success("All required documents are selected for this application type.")
    priority = st.selectbox("Priority", PRIORITY_OPTIONS, index=0)
    remarks = st.text_area(
        "Remarks / Internal Notes",
        placeholder="Example: Applicant contacted for missing transcript",
    )
    follow_up_required = st.checkbox("Follow-up required")
    last_contacted = st.date_input("Last contacted date", value=date.today())
    follow_up_due = st.date_input("Follow-up due date", value=date.today())
    submit_button = st.button("Submit Application")

    if submit_button:
        if not name or not email or not phone:
            st.warning("Name, email, and phone are required to create a case.")
        else:
            duplicates = get_existing_duplicates(cursor, email, phone)
            if duplicates:
                st.warning(
                    "Possible duplicate application found for the same email or phone."
                )
                st.write(duplicates)
            required_docs, missing_docs = evaluate_documents(application_type, documents)
            status = "Pending Review" if not missing_docs else "Incomplete"
            if missing_docs and follow_up_required:
                status = "Documents Requested"
            docs_string = ", ".join(documents)
            last_contacted_value = date_only(last_contacted) if follow_up_required else ""
            follow_up_due_value = date_only(follow_up_due) if follow_up_required else ""
            created_at = now_stamp()
            updated_at = created_at
            audit_log = f"{date_only(datetime.now())}: Application created with status {status}"
            cursor.execute(
                "INSERT INTO applicants (name, email, phone, application_type, documents, status, remarks, last_contacted, follow_up_required, follow_up_due, priority, audit_log, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    email,
                    phone,
                    application_type,
                    docs_string,
                    status,
                    remarks,
                    last_contacted_value,
                    int(follow_up_required),
                    follow_up_due_value,
                    priority,
                    audit_log,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            if missing_docs:
                st.warning(
                    f"Missing required documents: {', '.join(missing_docs)}. Status set to {status}."
                )
            else:
                st.success("Application submitted and ready for review.")

with metrics_col:
    st.header("Operational Metrics")
    df_all = pd.read_sql_query("SELECT * FROM applicants", conn)
    if not df_all.empty:
        total_apps = len(df_all)
        pending_apps = len(df_all[df_all["status"] == "Pending Review"])
        approved_apps = len(df_all[df_all["status"] == "Approved"])
        incomplete_apps = len(df_all[df_all["status"] == "Incomplete"])
        follow_up_count = len(df_all[df_all["follow_up_required"] == 1])
        urgent_count = len(df_all[df_all["priority"] == "Urgent"]) + len(df_all[df_all["priority"] == "High Priority"])
        st.metric("Total cases", total_apps)
        st.metric("Pending review", pending_apps)
        st.metric("Incomplete", incomplete_apps)
        st.metric("Follow-up needed", follow_up_count)
        st.metric("Urgent / high priority", urgent_count)
    else:
        st.info("No cases have been added yet.")

st.markdown("---")

st.header("Case Lookup & Management")
search_query = st.text_input("Search by applicant name or case ID")
status_filter = st.selectbox("Filter by status", ["All applications"] + STATUS_OPTIONS)
applications = load_applications(conn, search_query=search_query, status_filter=status_filter)

if applications.empty:
    st.info("No applications match the current lookup criteria.")
else:
    st.dataframe(applications)
    selected_id = st.selectbox(
        "Select case to manage",
        applications["id"].astype(str),
        format_func=lambda x: f"{x} - {applications.loc[applications['id'] == int(x), 'name'].iloc[0]}"
    )
    selected_case = cursor.execute(
        "SELECT * FROM applicants WHERE id = ?",
        (int(selected_id),),
    ).fetchone()
    if selected_case:
        (
            _,
            sel_name,
            sel_email,
            sel_phone,
            sel_type,
            sel_docs,
            sel_status,
            sel_remarks,
            sel_last_contacted,
            sel_follow_up_required,
            sel_follow_up_due,
            sel_priority,
            sel_audit_log,
            sel_created_at,
            sel_updated_at,
        ) = selected_case
        st.subheader("Selected Case Details")
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.markdown(f"**ID:** {selected_id}")
            st.markdown(f"**Name:** {sel_name}")
            st.markdown(f"**Email:** {sel_email}")
            st.markdown(f"**Phone:** {sel_phone}")
            st.markdown(f"**Application Type:** {sel_type}")
            st.markdown(f"**Priority:** {sel_priority}")
            st.markdown(f"**Current Status:** {sel_status}")
            st.markdown(f"**Created At:** {sel_created_at}")
            st.markdown(f"**Updated At:** {sel_updated_at}")
        with detail_cols[1]:
            st.markdown(f"**Required Documents:** {', '.join(get_required_docs(sel_type))}")
            st.markdown(f"**Submitted Documents:** {sel_docs}")
            st.markdown(f"**Follow-up required:** {'Yes' if sel_follow_up_required == 1 else 'No'}")
            st.markdown(f"**Last contacted:** {sel_last_contacted or 'N/A'}")
            st.markdown(f"**Follow-up due:** {sel_follow_up_due or 'N/A'}")
            st.markdown("**Remarks / Notes:**")
            st.write(sel_remarks or "No notes yet.")

        st.markdown("### Update Case")
        with st.form("update_case_form"):
            updated_documents = st.multiselect(
                "Update documents submitted",
                DOCUMENT_OPTIONS,
                default=sel_docs.split(", ") if sel_docs else [],
            )
            updated_priority = st.selectbox(
                "Priority",
                PRIORITY_OPTIONS,
                index=PRIORITY_OPTIONS.index(sel_priority) if sel_priority in PRIORITY_OPTIONS else 0,
            )
            possible_statuses = [sel_status] + STATUS_TRANSITIONS.get(sel_status, [])
            updated_status = st.selectbox("Status", possible_statuses, index=0)
            updated_remarks = st.text_area("Remarks / Internal Notes", value=sel_remarks or "")
            updated_follow_up_required = st.checkbox(
                "Follow-up required",
                value=bool(sel_follow_up_required),
            )
            updated_last_contacted = st.date_input(
                "Last contacted date",
                value=datetime.strptime(sel_last_contacted, "%Y-%m-%d").date()
                if sel_last_contacted
                else date.today(),
            )
            updated_follow_up_due = st.date_input(
                "Follow-up due date",
                value=datetime.strptime(sel_follow_up_due, "%Y-%m-%d").date()
                if sel_follow_up_due
                else date.today(),
            )
            update_button = st.form_submit_button("Update case")

        if update_button:
            missing_documents = evaluate_documents(sel_type, updated_documents)[1]
            if updated_status not in possible_statuses:
                st.warning(
                    f"Status transition from {sel_status} to {updated_status} is not allowed."
                )
            else:
                new_status = updated_status
                if missing_documents and new_status == "Approved":
                    st.warning("Cannot approve an application with missing required documents.")
                else:
                    if missing_documents and new_status == "Pending Review":
                        new_status = "Incomplete"
                        st.info(
                            "Application remains Incomplete because required documents are missing."
                        )
                    updated_docs_string = ", ".join(updated_documents)
                    last_contacted_value = date_only(updated_last_contacted) if updated_follow_up_required else ""
                    follow_up_due_value = date_only(updated_follow_up_due) if updated_follow_up_required else ""
                    cursor.execute(
                        "UPDATE applicants SET documents = ?, status = ?, remarks = ?, last_contacted = ?, follow_up_required = ?, follow_up_due = ?, priority = ?, updated_at = ? WHERE id = ?",
                        (
                            updated_docs_string,
                            new_status,
                            updated_remarks,
                            last_contacted_value,
                            int(updated_follow_up_required),
                            follow_up_due_value,
                            updated_priority,
                            now_stamp(),
                            int(selected_id),
                        ),
                    )
                    if sel_status != new_status:
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            f"Status changed from {sel_status} to {new_status} by system",
                        )
                    if sel_docs != updated_docs_string:
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            f"Documents updated to: {updated_docs_string}",
                        )
                    if sel_priority != updated_priority:
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            f"Priority updated to {updated_priority}",
                        )
                    if sel_remarks != updated_remarks:
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            "Officer remarks updated",
                        )
                    if bool(sel_follow_up_required) != bool(updated_follow_up_required):
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            f"Follow-up required set to {'Yes' if updated_follow_up_required else 'No'}",
                        )
                    if updated_follow_up_required and (sel_last_contacted != last_contacted_value or sel_follow_up_due != follow_up_due_value):
                        append_audit_entry(
                            cursor,
                            int(selected_id),
                            f"Follow-up schedule updated: contacted {last_contacted_value}, due {follow_up_due_value}",
                        )
                    conn.commit()
                    st.success("Case updated successfully.")

        st.markdown("### Audit Log & Timeline")
        if sel_audit_log:
            for line in sel_audit_log.split("\n"):
                st.write(f"- {line}")
        else:
            st.info("No audit entries have been recorded for this case yet.")

        st.markdown("### Status Timeline")
        timeline_items = []
        if sel_audit_log:
            for line in sel_audit_log.split("\n"):
                if any(keyword in line for keyword in ["Status changed", "Application created", "Documents updated", "Follow-up required", "Priority updated"]):
                    timeline_items.append(line)
        if timeline_items:
            for item in timeline_items:
                st.write(f"- {item}")
        else:
            st.write("Timeline data will appear as actions are logged.")

st.markdown("---")

st.header("Export Report")
export_filter = st.selectbox("Report type", EXPORT_FILTERS)
export_df = df_all.copy()
if export_filter == "Pending applications":
    export_df = export_df[export_df["status"] == "Pending Review"]
elif export_filter == "Incomplete applications":
    export_df = export_df[export_df["status"] == "Incomplete"]

if export_filter == "Monthly summary":
    if not export_df.empty:
        export_df["created_month"] = pd.to_datetime(export_df["created_at"]).dt.to_period("M").astype(str)
        summary = export_df.groupby("created_month")["id"].count().reset_index()
        summary.columns = ["Month", "Applications submitted"]
        csv = summary.to_csv(index=False)
        st.download_button(
            "Export CSV report",
            csv,
            file_name="monthly_summary.csv",
            mime="text/csv",
        )
    else:
        st.info("No application history to summarize.")
else:
    csv = export_df.to_csv(index=False)
    st.download_button(
        "Export CSV report",
        csv,
        file_name="applicant_report.csv",
        mime="text/csv",
    )

