import streamlit as st
import sqlite3, hashlib, hmac, os, io, calendar
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px

# ===================== MTTS | My Task Tracker System =====================
APP_TITLE = "My Task Tracker System"
DB_PATH = os.environ.get("MTTS_DB_PATH", os.path.join(os.path.dirname(__file__), "mtts.db"))
DEFAULT_USERNAME = os.environ.get("MTTS_USERNAME", "rajvineeth7@gmail.com")
DEFAULT_PASSWORD = os.environ.get("MTTS_PASSWORD", "@Rajvineeth7")

st.set_page_config(page_title="MTTS | My Task Tracker", page_icon="📘", layout="wide", initial_sidebar_state="auto")

# ---------- Styling ----------
def apply_theme(theme):
    palettes = {
        "Midnight Blue": ("#10243A", "#1E3A5F", "#4F8EF7", "#F4F7FB"),
        "Emerald": ("#12372A", "#1D5B45", "#27AE80", "#F3F8F5"),
        "Purple": ("#30234A", "#4B367C", "#9B7BF5", "#F7F5FC"),
        "Slate": ("#263238", "#455A64", "#26A69A", "#F4F6F7"),
    }
    primary, secondary, accent, bg = palettes.get(theme, palettes["Midnight Blue"])
    st.markdown(f"""
    <style>
      :root {{ --mtts-primary:{primary}; --mtts-secondary:{secondary}; --mtts-accent:{accent}; }}
      .stApp {{ background: {bg}; }}
      [data-testid="stSidebar"] {{ background: linear-gradient(180deg,{primary},{secondary}); }}
      [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
      .mtts-brand {{ display:flex; align-items:center; gap:14px; padding:8px 0 18px; }}
      .mtts-logo {{ width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,{accent},{secondary});
                    display:flex;align-items:center;justify-content:center;color:white;font-size:28px;
                    box-shadow:0 8px 20px #0002; }}
      .mtts-title {{ font-size:27px;font-weight:800;color:{primary};letter-spacing:-.6px; }}
      .mtts-sub {{ color:#64748b;font-size:13px;margin-top:-4px; }}
      .metric-card {{ background:white;border:1px solid #e6edf5;border-radius:16px;padding:18px 20px;
                      box-shadow:0 4px 16px #0f172a08; }}
      .metric-label {{ color:#64748b;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px; }}
      .metric-value {{ color:{primary};font-size:30px;font-weight:800;margin-top:4px; }}
      .section-head {{ font-size:20px;font-weight:750;color:{primary};margin:10px 0 6px; }}
      div[data-testid="stMetric"] {{ background:white;padding:15px;border:1px solid #e6edf5;border-radius:14px; }}
      .stButton>button {{ border-radius:10px;font-weight:650; }}
      div[data-testid="stForm"] {{ background:white;border:1px solid #e6edf5;border-radius:14px;padding:18px; }}
      footer {{ visibility:hidden; }}
      /* Tablet + Android phone responsive layout */
      @media (max-width: 900px) {{
        .block-container {{ padding-left:1rem !important; padding-right:1rem !important; }}
        [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap !important; gap:.65rem !important; }}
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
          min-width: min(100%, 260px) !important; flex: 1 1 260px !important;
        }}
        .mtts-brand {{ gap:10px; }}
        .mtts-logo {{ width:46px;height:46px;font-size:23px;border-radius:13px; }}
        .mtts-title {{ font-size:22px; line-height:1.2; }}
        .metric-card {{ padding:13px; }}
        div[data-testid="stMetric"] {{ padding:11px; }}
        [data-testid="stMetricValue"] {{ font-size:22px !important; }}
        .stButton>button, [data-testid="stDownloadButton"] button {{ min-height:44px; white-space:normal; }}
        div[data-testid="stForm"] {{ padding:12px; }}
        [data-testid="stDataFrame"], [data-testid="stTable"] {{ max-width:100%; overflow-x:auto; }}
        input, textarea {{ font-size:16px !important; }} /* prevents Android/iOS input zoom */
      }}
      @media (max-width: 600px) {{
        .block-container {{ padding:.7rem .65rem 4rem .65rem !important; }}
        .mtts-title {{ font-size:19px; letter-spacing:-.3px; }}
        .mtts-sub {{ font-size:12px; }}
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
          min-width:100% !important; flex:1 1 100% !important; width:100% !important;
        }}
        [data-testid="stMetric"] {{ padding:9px; }}
        [data-testid="stMetricLabel"] {{ font-size:11px !important; }}
        [data-testid="stMetricValue"] {{ font-size:20px !important; }}
        .stButton>button, [data-testid="stDownloadButton"] button {{ width:100%; min-height:46px; }}
        div[data-testid="stForm"] {{ padding:10px; }}
        [data-testid="stExpander"] {{ border-radius:10px; }}
        [data-testid="stDataFrame"] {{ font-size:12px; }}
        /* Keep wide tables usable with horizontal swipe rather than squeezing text */
        [data-testid="stDataFrame"] > div {{ overflow-x:auto !important; }}
      }}
    </style>
    """, unsafe_allow_html=True)

# ---------- Database ----------
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS work_roles(
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
          created_at TEXT NOT NULL, UNIQUE(user_id,name),
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, role_id INTEGER,
          task_date TEXT NOT NULL, sno INTEGER NOT NULL DEFAULT 1, task TEXT NOT NULL,
          work_by TEXT DEFAULT '', deadline TEXT, status TEXT NOT NULL DEFAULT 'Pending', completed_date TEXT,
          priority TEXT NOT NULL DEFAULT 'Medium', notes TEXT DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          deleted_at TEXT, deleted_by TEXT DEFAULT '', delete_reason TEXT DEFAULT '',
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(role_id) REFERENCES work_roles(id)
        );
        CREATE TABLE IF NOT EXISTS task_events(
          id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
          event_type TEXT NOT NULL, event_date TEXT NOT NULL, snapshot TEXT NOT NULL,
          FOREIGN KEY(task_id) REFERENCES tasks(id)
        );
        CREATE TABLE IF NOT EXISTS settings(
          user_id INTEGER PRIMARY KEY, theme TEXT DEFAULT 'Midnight Blue',
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        # Safe schema migration for existing MTTS databases
        cols = [r["name"] for r in c.execute("PRAGMA table_info(tasks)").fetchall()]
        if "completed_date" not in cols:
            c.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
        for col, ddl in [("deleted_at", "ALTER TABLE tasks ADD COLUMN deleted_at TEXT"),
                          ("deleted_by", "ALTER TABLE tasks ADD COLUMN deleted_by TEXT DEFAULT ''"),
                          ("delete_reason", "ALTER TABLE tasks ADD COLUMN delete_reason TEXT DEFAULT ''")]:
            if col not in cols:
                c.execute(ddl)
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_date ON tasks(user_id, task_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_deleted ON tasks(user_id, deleted_at)")
        row=c.execute("SELECT id FROM users WHERE username=?", (DEFAULT_USERNAME,)).fetchone()
        if not row:
            ph=hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
            c.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                      (DEFAULT_USERNAME,ph,datetime.now().isoformat(timespec="seconds")))
            uid=c.execute("SELECT id FROM users WHERE username=?", (DEFAULT_USERNAME,)).fetchone()["id"]
            c.execute("INSERT OR IGNORE INTO settings(user_id) VALUES(?)",(uid,))

def get_user(username):
    with db() as c: return c.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()

def event(task_id, user_id, typ, snapshot, conn=None):
    """Write an audit event. Reuse the caller's connection inside transactions."""
    sql = "INSERT INTO task_events(task_id,user_id,event_type,event_date,snapshot) VALUES(?,?,?,?,?)"
    params = (task_id, user_id, typ, datetime.now().isoformat(timespec="seconds"), snapshot)
    if conn is not None:
        conn.execute(sql, params)
    else:
        with db() as c:
            c.execute(sql, params)

def task_snapshot(row):
    return " | ".join(f"{k}={row[k]}" for k in row.keys())

def roles(uid):
    with db() as c: return c.execute("SELECT * FROM work_roles WHERE user_id=? ORDER BY name",(uid,)).fetchall()

def tasks_for(uid, start=None, end=None, role_id=None, include_deleted=False):
    """Fetch tasks for this user; archive records are hidden by default."""
    q="""SELECT t.*, r.name AS work_role FROM tasks t LEFT JOIN work_roles r ON r.id=t.role_id
         WHERE t.user_id=?"""
    args=[uid]
    if not include_deleted:
        q += " AND t.deleted_at IS NULL"
    if start: q+=" AND t.task_date>=?"; args.append(str(start))
    if end: q+=" AND t.task_date<=?"; args.append(str(end))
    if role_id and role_id!="All": q+=" AND t.role_id=?"; args.append(int(role_id))
    q+=" ORDER BY COALESCE(t.deadline,t.task_date), t.priority, t.task_date, t.sno"
    with db() as c: return pd.read_sql_query(q,c,params=args)

def effective_status(row, selected_date=None):
    status=str(row["status"])
    today=selected_date or date.today()
    deadline=row.get("deadline")
    if status not in ("Completed","Hold") and deadline and str(deadline)<today.isoformat():
        return "Overdue"
    return status

def add_task(uid, role_id, task_date, sno, task, work_by, deadline, status, priority, notes, completed_date=None):
    now=datetime.now().isoformat(timespec="seconds")
    if status == "Completed" and not completed_date:
        completed_date = str(task_date)
    with db() as c:
        cur=c.execute("""INSERT INTO tasks(user_id,role_id,task_date,sno,task,work_by,deadline,status,priority,completed_date,notes,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (uid,role_id,task_date,sno,task,work_by,deadline,status,priority,completed_date,notes,now,now))
        tid=cur.lastrowid
        row=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
    event(tid,uid,"Created",task_snapshot(row))

def update_task(tid, uid, values):
    """Update a task and its audit events atomically using one SQLite connection."""
    now = datetime.now().isoformat(timespec="seconds")
    with db() as c:
        old = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=? AND deleted_at IS NULL",
                        (tid, uid)).fetchone()
        if not old:
            return False
        event(tid, uid, "Before edit", task_snapshot(old), conn=c)
        c.execute("""UPDATE tasks SET role_id=?,task_date=?,sno=?,task=?,work_by=?,deadline=?,status=?,priority=?,completed_date=?,notes=?,updated_at=?
                     WHERE id=? AND user_id=? AND deleted_at IS NULL""",
                  (*values, now, tid, uid))
        new = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, uid)).fetchone()
        event(tid, uid, "Updated", task_snapshot(new), conn=c)
    return True


def delete_task(tid, uid, reason=""):
    """Soft-delete atomically; task update and audit events share one connection."""
    now = datetime.now().isoformat(timespec="seconds")
    with db() as c:
        # Acquire the write lock early; timeout/busy_timeout lets concurrent sessions finish.
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=? AND deleted_at IS NULL",
                        (tid, uid)).fetchone()
        if not row:
            return False
        event(tid, uid, "Deleted", task_snapshot(row), conn=c)
        c.execute("""UPDATE tasks SET deleted_at=?, deleted_by=?, delete_reason=?, updated_at=?
                     WHERE id=? AND user_id=? AND deleted_at IS NULL""",
                  (now, DEFAULT_USERNAME, reason.strip(), now, tid, uid))
        archived = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, uid)).fetchone()
        event(tid, uid, "Delete details", task_snapshot(archived), conn=c)
    return True


def restore_task(tid, uid):
    """Restore a task and log the restoration atomically."""
    now = datetime.now().isoformat(timespec="seconds")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=? AND deleted_at IS NOT NULL",
                        (tid, uid)).fetchone()
        if not row:
            return False
        c.execute("""UPDATE tasks SET deleted_at=NULL, deleted_by='', delete_reason='',
                     updated_at=? WHERE id=? AND user_id=? AND deleted_at IS NOT NULL""",
                  (now, tid, uid))
        restored = c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, uid)).fetchone()
        event(tid, uid, "Restored", task_snapshot(restored), conn=c)
    return True


def deleted_task_count(uid):
    with db() as c:
        row = c.execute("SELECT COUNT(*) AS n FROM tasks WHERE user_id=? AND deleted_at IS NOT NULL",
                        (uid,)).fetchone()
    return int(row["n"] if row else 0)


def active_task_count(uid):
    with db() as c:
        row = c.execute("SELECT COUNT(*) AS n FROM tasks WHERE user_id=? AND deleted_at IS NULL",
                        (uid,)).fetchone()
    return int(row["n"] if row else 0)


def get_deleted_tasks(uid, start=None, end=None):
    frame = tasks_for(uid, start, end, include_deleted=True)
    return frame[frame["deleted_at"].notna()].copy() if not frame.empty else frame


def html_escape(value):
    import html
    return html.escape(str(value if value is not None else ""))


def render_task_cards(frame):
    """Readable task cards for compact/mobile layouts."""
    if frame.empty:
        st.caption("No tasks to display.")
        return
    for _, row in frame.iterrows():
        status = row.get("Effective Status", row.get("status", "Pending"))
        st.markdown(
            f"<div style='border:1px solid #e6edf5;border-radius:12px;background:white;padding:12px;margin:8px 0'>"
            f"<b>{int(row.get('sno',1))}. {html_escape(row.get('task','Untitled'))}</b><br>"
            f"Status: {html_escape(status)} · Priority: {html_escape(row.get('priority','Medium'))}<br>"
            f"<small>Created: {html_escape(row.get('task_date','—'))} · Deadline: "
            f"{html_escape(row.get('deadline') or '—')} · Completed: "
            f"{html_escape(row.get('completed_date') or '—')}</small></div>",
            unsafe_allow_html=True
        )


def export_task_columns(frame):
    mapping = {"id":"Task ID","sno":"S.No","task":"Task","work_role":"Work role",
               "work_by":"Work by","task_date":"Task created date","deadline":"Deadline",
               "status":"Stored status","completed_date":"Task completed date",
               "priority":"Priority","notes":"Notes","created_at":"Record created",
               "updated_at":"Last updated","deleted_at":"Deleted at",
               "deleted_by":"Deleted by","delete_reason":"Deletion reason"}
    return frame.rename(columns={k:v for k,v in mapping.items() if k in frame.columns})


def make_excel_bytes(sheets):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, index=False, sheet_name=name[:31])
    output.seek(0)
    return output.getvalue()


def task_search(frame, query):
    if frame.empty or not str(query or "").strip():
        return frame.copy()
    term = str(query).strip().lower()
    cols = [c for c in ["task","work_by","notes","work_role"] if c in frame.columns]
    mask = pd.Series(False, index=frame.index)
    for col in cols:
        mask |= frame[col].fillna("").astype(str).str.lower().str.contains(term, regex=False)
    return frame[mask].copy()


def validate_task_values(task, sno, status, priority):
    errors=[]
    if not str(task or "").strip(): errors.append("Task description is required.")
    if int(sno)<1: errors.append("S.No must be at least 1.")
    if status not in {"Pending","Hold","Completed"}: errors.append("Invalid status.")
    if priority not in {"High","Medium","Low","Ease"}: errors.append("Invalid priority.")
    return errors


def database_integrity():
    with db() as c:
        integrity = c.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = c.execute("PRAGMA foreign_key_check").fetchall()
    return [r[0] for r in integrity], foreign_keys

init_db()

# ---------- Login ----------
if "user" not in st.session_state:
    st.session_state.user=None

def logo(title="My Task Tracker System", subtitle="Plan • Track • Achieve"):
    st.markdown(f"""<div class="mtts-brand"><div class="mtts-logo">📘</div>
      <div><div class="mtts-title">{title}</div><div class="mtts-sub">{subtitle}</div></div></div>""",
      unsafe_allow_html=True)

if not st.session_state.user:
    apply_theme("Midnight Blue")
    _, center, _ = st.columns([1,1.15,1])
    with center:
        st.markdown("<div style='height:7vh'></div>",unsafe_allow_html=True)
        logo("MTTS","MY TASK TRACKER SYSTEM")
        st.markdown("### Welcome back")
        st.caption("Sign in to access your personal workspace.")
        with st.form("login_form"):
            username=st.text_input("Username",placeholder="Enter your email")
            password=st.text_input("Password",type="password",placeholder="Enter your password")
            submitted=st.form_submit_button("Sign in",use_container_width=True)
        if submitted:
            u=get_user(username.strip())
            hashed=hashlib.sha256(password.encode()).hexdigest()
            if u and hmac.compare_digest(u["password_hash"],hashed):
                st.session_state.user={"id":u["id"],"username":u["username"]}
                st.rerun()
            else: st.error("Invalid username or password.")
        st.markdown("<div style='text-align:center;color:#64748b;margin-top:35px;font-size:12px'>Powered by <b>TVR</b> · © 2026</div>",unsafe_allow_html=True)
    st.stop()

uid=st.session_state.user["id"]
with db() as c:
    settings=c.execute("SELECT theme FROM settings WHERE user_id=?",(uid,)).fetchone()
theme=settings["theme"] if settings else "Midnight Blue"
apply_theme(theme)

# ---------- Sidebar navigation ----------
with st.sidebar:
    st.markdown("## 📘 MTTS")
    st.caption("My Task Tracker System")
    st.divider()
    page=st.radio("WORKSPACE",["My Task Tracking Dashboard","My Task Entries","My Task History","Settings"],index=0)
    st.divider()
    st.caption(f"Signed in as\n{st.session_state.user['username']}")
    st.caption(f"Active: {active_task_count(uid)} · Deleted: {deleted_task_count(uid)}")
    if st.button("↪ Sign out",use_container_width=True):
        st.session_state.user=None
        st.rerun()

logo(subtitle="Your personal productivity workspace")
st.caption(f"Today · {date.today().strftime('%A, %d %B %Y')}")

# ---------- Dashboard ----------
if page=="My Task Tracking Dashboard":
    st.markdown("## My Task Tracking Dashboard")
    c1,c2,c3=st.columns([1,1,1])
    with c1: start=st.date_input("From date",value=date.today().replace(day=1),key="dash_start")
    with c2: end=st.date_input("To date",value=date.today(),key="dash_end")
    with c3:
        role_opts={"All work roles":"All"}
        role_opts.update({r["name"]:str(r["id"]) for r in roles(uid)})
        selected_role=st.selectbox("Work role",list(role_opts.keys()),key="dash_role")
    if start>end: st.error("From date must be on or before To date."); st.stop()
    df=tasks_for(uid,start,end,role_opts[selected_role])
    if not df.empty:
        df["Effective Status"]=df.apply(lambda r: effective_status(r,end),axis=1)
    total=len(df); completed=int((df["Effective Status"]=="Completed").sum()) if total else 0
    overdue=int((df["Effective Status"]=="Overdue").sum()) if total else 0
    pending=int((df["Effective Status"]=="Pending").sum()) if total else 0
    held=int((df["Effective Status"]=="Hold").sum()) if total else 0
    a,b,c,d,e=st.columns(5)
    for col,label,val in zip([a,b,c,d,e],["Total tasks","Completed","Pending","On hold","Overdue"],[total,completed,pending,held,overdue]):
        col.metric(label,val)
    st.progress(completed/total if total else 0, text=f"Completion rate: {completed/total:.0%}" if total else "No tasks in this period")
    st.markdown("### Task calendar")
    cal_month=st.date_input("Choose calendar month",value=date.today().replace(day=1),key="cal_month")
    cal=calendar.Calendar(firstweekday=0)
    month_days=cal.monthdatescalendar(cal_month.year,cal_month.month)
    month_df=tasks_for(uid,date(cal_month.year,cal_month.month,1),date(cal_month.year,cal_month.month,calendar.monthrange(cal_month.year,cal_month.month)[1]))
    count_map=month_df.groupby("task_date").size().to_dict() if not month_df.empty else {}
    cols=st.columns(7)
    for i,dayname in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): cols[i].markdown(f"**{dayname}**")
    for week in month_days:
        cols=st.columns(7)
        for i,day in enumerate(week):
            n=count_map.get(day.isoformat(),0)
            label=f"{day.day}\n• {n} task" if n==1 else (f"{day.day}\n• {n} tasks" if n else str(day.day))
            if day.month!=cal_month.month: cols[i].markdown(f"<span style='color:#a0a8b3'>{day.day}</span>",unsafe_allow_html=True)
            elif cols[i].button(label,key=f"cal_{day.isoformat()}",use_container_width=True):
                st.session_state["selected_task_date"]=day
                st.session_state["page_from_calendar"]=True
                st.rerun()
    selected_day=st.session_state.get("selected_task_date",date.today())
    st.markdown(f"### Tasks for {selected_day.strftime('%d %B %Y')}")
    daily=tasks_for(uid,selected_day,selected_day)
    if daily.empty:
        st.info("No tasks entered for this date.")
    else:
        daily["Effective Status"]=daily.apply(lambda r: effective_status(r,selected_day),axis=1)
        st.dataframe(daily[["sno","task","work_role","work_by","task_date","deadline","Effective Status","priority","completed_date","notes"]].rename(
            columns={"sno":"S.No","task":"Task","work_role":"Work role","work_by":"Work by","task_date":"Task created date","deadline":"Deadline","priority":"Priority","completed_date":"Task completed date","notes":"Notes"}),
            use_container_width=True,hide_index=True)
    if not df.empty:
        left,right=st.columns(2)
        with left:
            st.markdown("### Status distribution")
            chart=df["Effective Status"].value_counts().rename_axis("Status").reset_index(name="Tasks")
            st.plotly_chart(px.pie(chart,names="Status",values="Tasks",hole=.55),use_container_width=True)
        with right:
            st.markdown("### Priority distribution")
            p=df["priority"].value_counts().rename_axis("Priority").reset_index(name="Tasks")
            st.plotly_chart(px.bar(p,x="Priority",y="Tasks",color="Priority"),use_container_width=True)
        st.markdown("### Daily task volume")
        trend=df.groupby("task_date").size().reset_index(name="Tasks")
        trend["task_date"]=pd.to_datetime(trend["task_date"])
        st.plotly_chart(px.line(trend,x="task_date",y="Tasks",markers=True),use_container_width=True)
        st.markdown("### Work role summary")
        role_summary=df.groupby("work_role").agg(Tasks=("id","count")).reset_index()
        st.dataframe(role_summary,use_container_width=True,hide_index=True)
    else: st.info("Add tasks in My Task Entries to populate your dashboard.")

# ---------- Entries ----------
elif page=="My Task Entries":
    st.markdown("## My Task Entries")
    with st.expander("＋ Add a work role / project",expanded=False):
        with st.form("role_form"):
            role_name=st.text_input("Work role / company / project",placeholder="e.g. Granules – Supply Chain")
            save_role=st.form_submit_button("Save work role")
        if save_role:
            if role_name.strip():
                try:
                    with db() as c: c.execute("INSERT INTO work_roles(user_id,name,created_at) VALUES(?,?,?)",
                        (uid,role_name.strip(),datetime.now().isoformat(timespec="seconds")))
                    st.success("Work role saved."); st.rerun()
                except sqlite3.IntegrityError: st.warning("This work role already exists.")
            else: st.warning("Enter a work role name.")
    role_list=roles(uid)
    if not role_list:
        st.info("First create a work role, such as Granules, then add tasks.")
        st.stop()
    role_map={r["name"]:r["id"] for r in role_list}
    selected_role_name=st.selectbox("Select work role",list(role_map.keys()),key="entry_role")
    selected_role_id=role_map[selected_role_name]
    task_day=st.date_input("Select task date",value=st.session_state.get("selected_task_date",date.today()),key="entry_date")
    # Include unfinished tasks whose deadline is before this date as carried-over overdue items.
    all_role_tasks=tasks_for(uid,role_id=str(selected_role_id))
    if not all_role_tasks.empty:
        carry=all_role_tasks[(all_role_tasks["status"].isin(["Pending","Overdue"])) &
            all_role_tasks["deadline"].notna() & (all_role_tasks["deadline"]<task_day.isoformat())]
        carry=carry[carry["status"]!="Completed"]
    else: carry=pd.DataFrame()
    day_tasks=tasks_for(uid,task_day,task_day, str(selected_role_id))
    st.markdown(f"### Task list · {task_day.strftime('%d %b %Y')}")
    if not carry.empty:
        st.warning(f"{len(carry)} unfinished task(s) from earlier deadlines are carried forward and shown as overdue. They remain linked to their original entry; no duplicate task is created.")
        carry["Effective Status"]="Overdue"
        st.dataframe(carry[["sno","task","task_date","deadline","priority","Effective Status","completed_date"]].rename(columns={"sno":"S.No","task":"Task","task_date":"Task created date","deadline":"Deadline","priority":"Priority","completed_date":"Task completed date"}),use_container_width=True,hide_index=True)
    if not day_tasks.empty:
        day_tasks["Effective Status"]=day_tasks.apply(lambda r: effective_status(r,task_day),axis=1)
        st.dataframe(day_tasks[["id","sno","task","work_by","task_date","deadline","Effective Status","priority","completed_date","notes"]].rename(
            columns={"id":"ID","sno":"S.No","task":"Task","work_by":"Work by","task_date":"Task created date","deadline":"Deadline","priority":"Priority","completed_date":"Task completed date","notes":"Notes"}),
            use_container_width=True,hide_index=True)
    else: st.caption("No tasks entered for this work role and date yet.")
    st.markdown("### Add a task")
    with st.form("add_task_form",clear_on_submit=True):
        x1,x2=st.columns(2)
        with x1:
            sno=st.number_input("S.No",min_value=1,step=1,value=(int(day_tasks["sno"].max())+1 if not day_tasks.empty else 1))
            task=st.text_input("Task *",placeholder="Describe the task")
            work_by=st.text_input("Work by",placeholder="Owner / team / person")
            deadline=st.date_input("Deadline (optional)",value=None)
        with x2:
            status=st.selectbox("Status",["Pending","Hold","Completed"])
            completed_date = st.date_input("Task completed date", value=task_day if status=="Completed" else None,
                                           key="new_completed_date") if status=="Completed" else None
            priority=st.selectbox("Priority",["High","Medium","Low","Ease"],index=1)
            notes=st.text_area("Notes / details",placeholder="Additional context")
        add=st.form_submit_button("＋ Add task",type="primary")
    if add:
        if not task.strip(): st.error("Task description is required.")
        else:
            add_task(uid,selected_role_id,task_day,int(sno),task.strip(),work_by.strip(),deadline.isoformat() if deadline else None,status,priority,notes.strip(),completed_date.isoformat() if completed_date else None)
            st.success("Task added and saved to the database."); st.rerun()
    st.markdown("### Edit or delete a task")
    if not day_tasks.empty:
        ids=day_tasks["id"].tolist()
        chosen=st.selectbox("Choose task ID",ids,format_func=lambda x: f"#{x} · {day_tasks.loc[day_tasks.id==x,'task'].iloc[0]}")
        row=day_tasks[day_tasks.id==chosen].iloc[0]
        with st.form("edit_task_form"):
            e1,e2=st.columns(2)
            with e1:
                esno=st.number_input("S.No ",min_value=1,value=int(row["sno"]),key="esno")
                etask=st.text_input("Task ",value=row["task"],key="etask")
                ework=st.text_input("Work by ",value=row["work_by"] or "",key="ework")
                edeadline=st.date_input("Deadline ",value=date.fromisoformat(row["deadline"]) if row["deadline"] else None,key="edeadline")
            with e2:
                estatus=st.selectbox("Status ",["Pending","Hold","Completed"],index=["Pending","Hold","Completed"].index(row["status"]) if row["status"] in ["Pending","Hold","Completed"] else 0,key="estatus")
                default_completed = date.fromisoformat(row["completed_date"]) if row.get("completed_date") else (task_day if estatus=="Completed" else None)
                ecompleted = st.date_input("Task completed date ",value=default_completed,key="ecompleted") if estatus=="Completed" else None
                epriority=st.selectbox("Priority ",["High","Medium","Low","Ease"],index=["High","Medium","Low","Ease"].index(row["priority"]) if row["priority"] in ["High","Medium","Low","Ease"] else 1,key="epriority")
                enotes=st.text_area("Notes ",value=row["notes"] or "",key="enotes")
            save=st.form_submit_button("Save changes")
        if save:
            update_task(int(chosen),uid,(selected_role_id,task_day.isoformat(),int(esno),etask.strip(),ework.strip(),edeadline.isoformat() if edeadline else None,estatus,epriority,ecompleted.isoformat() if ecompleted else None,enotes.strip()))
            st.success("Task updated."); st.rerun()
        with st.expander("🗑 Delete / archive selected task", expanded=False):
            st.caption("Soft delete removes it from active views while preserving the task and audit history.")
            reason = st.text_input("Reason (optional)", placeholder="Duplicate, cancelled, entered by mistake", key="delete_reason")
            confirmed = st.checkbox("Confirm move to Deleted Tasks", key="confirm_delete_task")
            if st.button("Move to Deleted Tasks", type="secondary", disabled=not confirmed):
                if delete_task(int(chosen), uid, reason):
                    st.success("Task archived. Its history is preserved.")
                    st.rerun()
                else:
                    st.warning("Task was already deleted or could not be found.")

# ---------- History ----------
elif page=="My Task History":
    st.markdown("## My Task History")
    history_mode = st.radio("History view", ["Activity on a date", "All task records", "Deleted tasks"],
                            horizontal=True, key="history_mode")
    h1, h2 = st.columns(2)
    with h1: hist_start = st.date_input("From date", value=date.today().replace(day=1), key="hist_start")
    with h2: hist_end = st.date_input("To date", value=date.today(), key="hist_end")
    hist_date=st.date_input("Activity date",value=date.today(),key="history_date")
    if hist_start > hist_end:
        st.error("From date must be on or before end date."); st.stop()
    if history_mode == "Activity on a date":
        hist=tasks_for(uid,hist_date,hist_date,include_deleted=True)
    else:
        hist=tasks_for(uid,hist_start,hist_end,include_deleted=True)
        if history_mode == "Deleted tasks" and not hist.empty:
            hist=hist[hist["deleted_at"].notna()]
        elif history_mode == "All task records" and not hist.empty:
            hist=hist[hist["deleted_at"].isna()]
    if hist.empty: st.info("No tasks recorded for this date.")
    else:
        hist["Effective Status"]=hist.apply(lambda r: effective_status(r,hist_date),axis=1)
        hist["Effective Status"] = hist.apply(
            lambda r: "Deleted" if pd.notna(r.get("deleted_at")) else effective_status(r, hist_date), axis=1)
        cols = ["sno","task","work_role","work_by","task_date","deadline","Effective Status",
                "priority","completed_date","notes","created_at","updated_at","deleted_at","delete_reason"]
        cols = [col for col in cols if col in hist.columns]
        st.dataframe(hist[cols].rename(columns={
            "sno":"S.No","task":"Task","work_role":"Work role","work_by":"Work by",
            "task_date":"Task created date","deadline":"Deadline","priority":"Priority",
            "completed_date":"Task completed date","notes":"Notes","created_at":"Record created",
            "updated_at":"Last updated","deleted_at":"Deleted at","delete_reason":"Deletion reason"
        }), use_container_width=True, hide_index=True)
    if history_mode == "Deleted tasks" and not hist.empty:
        st.markdown("### Restore a deleted task")
        restore_id = st.selectbox("Choose deleted task", hist["id"].tolist(),
            format_func=lambda x: f"#{x} · {hist.loc[hist.id==x,'task'].iloc[0]}")
        if st.button("♻ Restore selected task", type="primary"):
            if restore_task(int(restore_id), uid):
                st.success("Task restored to active entries.")
                st.rerun()

    st.markdown("### Task audit trail")
    with db() as c:
        sql = """SELECT e.event_date,e.event_type,e.snapshot,e.task_id,t.task,t.deleted_at
                 FROM task_events e LEFT JOIN tasks t ON t.id=e.task_id WHERE e.user_id=?"""
        args=[uid]
        if history_mode == "Activity on a date":
            sql += " AND date(e.event_date)=?"; args.append(hist_date.isoformat())
        else:
            sql += " AND date(e.event_date)>=? AND date(e.event_date)<=?"
            args.extend([hist_start.isoformat(),hist_end.isoformat()])
        sql += " ORDER BY e.event_date DESC LIMIT 500"
        events=pd.read_sql_query(sql,c,params=args)
    if events.empty:
        st.caption("Task changes will appear here.")
    else:
        st.dataframe(events.rename(columns={"event_date":"Timestamp","event_type":"Action",
            "snapshot":"Task snapshot","task":"Current task title","task_id":"Task ID",
            "deleted_at":"Currently deleted"}),use_container_width=True,hide_index=True)

# ---------- Settings ----------
elif page=="Settings":
    st.markdown("## Settings")
    st.markdown("### Appearance")
    themes=["Midnight Blue","Emerald","Purple","Slate"]
    new_theme=st.selectbox("Theme colour",themes,index=themes.index(theme) if theme in themes else 0)
    if st.button("Apply theme"):
        with db() as c: c.execute("INSERT INTO settings(user_id,theme) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET theme=excluded.theme",(uid,new_theme))
        st.success("Theme saved."); st.rerun()
    st.markdown("### Export reports")
    c1,c2=st.columns(2)
    with c1: export_start=st.date_input("Report from",value=date.today().replace(day=1),key="export_start")
    with c2: export_end=st.date_input("Report to",value=date.today(),key="export_end")
    export_df=tasks_for(uid,export_start,export_end)
    if not export_df.empty: export_df["Effective Status"]=export_df.apply(lambda r: effective_status(r,export_end),axis=1)
    if export_start>export_end: st.error("Report start date must be on or before end date.")
    else:
        output=io.BytesIO()
        with pd.ExcelWriter(output,engine="openpyxl") as writer:
            if export_df.empty: pd.DataFrame(columns=["No tasks in selected range"]).to_excel(writer,index=False,sheet_name="Tasks")
            else:
                export_df.rename(columns={"sno":"S.No","task":"Task","work_role":"Work role","work_by":"Work by","deadline":"Deadline","status":"Stored status","priority":"Priority","notes":"Notes","task_date":"Task created date","completed_date":"Task completed date"}).to_excel(writer,index=False,sheet_name="Tasks")
                summary=export_df.groupby(["Effective Status","priority"]).size().reset_index(name="Task count")
                summary.to_excel(writer,index=False,sheet_name="Summary")
        st.download_button("⬇ Download Excel report",data=output.getvalue(),file_name=f"MTTS_Report_{export_start}_{export_end}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")
    st.markdown("### Deleted task archive export")
    deleted_export = get_deleted_tasks(uid, export_start, export_end)
    if deleted_export.empty:
        st.caption("No deleted tasks in this report range.")
    else:
        st.download_button("⬇ Download deleted-task archive (.xlsx)",
            data=make_excel_bytes({"Deleted Tasks": export_task_columns(deleted_export)}),
            file_name=f"MTTS_Deleted_Tasks_{export_start}_{export_end}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("### Database")
    st.caption(f"SQLite database path: `{DB_PATH}`")
    if os.path.exists(DB_PATH):
        with open(DB_PATH,"rb") as f: db_bytes=f.read()
        st.download_button("⬇ Download database backup (.db)",data=db_bytes,file_name="mtts_backup.db",mime="application/octet-stream")
    st.warning("Deleted tasks are archived, not physically removed. Restore them from My Task History; keep regular backups.")
    st.warning("For Streamlit Community Cloud, local files can reset during app maintenance/redeployment. For reliable cloud persistence, use a hosted database such as Supabase/PostgreSQL. The SQLite file is persistent on your own computer/server.")
    st.markdown("### Account")
    st.write(f"Username: **{st.session_state.user['username']}**")
    st.caption("This starter version uses a single-owner login. Change the default credentials through MTTS_USERNAME and MTTS_PASSWORD environment variables before deployment.")


# ===================== MTTS OPERATING NOTES =====================
# 1. Task deletion is intentionally implemented as a soft delete.
# 2. Soft-deleted rows remain in the tasks table and retain their IDs.
# 3. task_events references task IDs; keeping rows prevents FK failures.
# 4. Active views call tasks_for(..., include_deleted=False) by default.
# 5. History can request include_deleted=True to inspect archived rows.
# 6. Restore clears deletion metadata but never removes audit events.
# 7. Deletion reason is optional and stored in delete_reason.
# 8. deleted_at is an ISO timestamp, useful for sorting and filtering.
# 9. deleted_by records the account responsible for the action.
# 10. completed_date remains separate from task_date.
# 11. task_date is the original creation/entry date.
# 12. completed_date is the date the task was marked complete.
# 13. updated_at changes on edits, deletion, and restoration.
# 14. event snapshots preserve values before and after lifecycle changes.
# 15. All user-facing task queries are scoped by user_id.
# 16. All SQL values are passed as parameters, not interpolated.
# 17. Foreign-key enforcement remains enabled for each SQLite connection.
# 18. Schema migration adds new fields without dropping existing data.
# 19. Existing databases can be opened with this updated application.
# 20. Keep a downloaded database backup before replacing app versions.
# 21. For cloud hosting, use a persistent hosted database when required.
# 22. Do not manually delete rows from tasks while task_events reference them.
# 23. If permanent purge is ever added, it must handle audit retention explicitly.
# 24. A deleted task can be restored from My Task History.
# 25. Deleted task exports include deletion metadata and original task details.
# 26. Dashboard counts exclude archived tasks unless explicitly queried.
# 27. This file is a flexible starter; adapt fields as the workflow evolves.
# 28. Use environment variables for deployment credentials.
# 29. Rotate the default password before exposing the app publicly.
# 30. SQLite is appropriate for a single-user local application.
# 31. Concurrent multi-user deployments should use a server database.
# 32. Maintain periodic backups to protect task and audit history.
# 33. Audit timestamps use local system time with ISO formatting.
# 34. Date filters are inclusive at both ends.
# 35. Task status values are Pending, Hold, and Completed.
# 36. Effective overdue status is calculated for display, not stored.
# 37. Priority values are High, Medium, Low, and Ease.
# 38. Work roles are owned by a user account.
# 39. Unique role names are enforced per user.
# 40. The app retains the existing login and theme workflow.
# 41. The app retains dashboard, entries, history, settings, and Excel export.
# 42. The database file path can be configured using MTTS_DB_PATH.
# 43. User login can be configured using MTTS_USERNAME and MTTS_PASSWORD.
# 44. Always test changes on a copy of the database first.
# 45. Report issues with the traceback and relevant function for precise fixes.
