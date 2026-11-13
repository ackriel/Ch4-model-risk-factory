"""Model Risk Factory - Streamlit dashboard.

Run:  streamlit run app.py

Every number shown is read from files in outputs/ written by the agents. The Run,
Approve and Reject buttons call the same pipeline functions as main.py, so they
genuinely control the pipeline (a stage cannot run until the previous one is approved).
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from agents import discover, document, monitor, redevelop, validate
from core import config, data, impact, llm, pipeline, portfolio, state

st.set_page_config(page_title="Model Risk Factory", page_icon="🏦", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 1.6rem;}
  .mrf-header {background: #0b2545; color: #fff; padding: 18px 24px; border-radius: 8px; margin-bottom: 18px;}
  .mrf-header h1 {color: #fff; font-size: 1.6rem; margin: 0;}
  .mrf-header p {margin: 2px 0 0; opacity: .8; font-size: .9rem;}
  .pill {display:inline-block; padding:2px 10px; border-radius:10px; font-size:.78rem; font-weight:600; color:#fff;}
  .not_started {background:#8a96a3;} .completed {background:#1f6fb2;} .approved {background:#2e7d32;}
  .rejected {background:#c62828;} .failed {background:#c62828;}
  .FAILING {background:#c62828;} .BLOCKED {background:#6a1b9a;} .NEEDS-ATTENTION {background:#ef8f00;}
  .PENDING {background:#8a96a3;} .OK {background:#2e7d32;}
  .RED {background:#c62828;} .AMBER {background:#ef8f00;} .GREEN {background:#2e7d32;}
  .src {font-size:.72rem; padding:1px 8px; border-radius:4px; background:#e3f2e6; color:#1b5e20;}
  .src.ai {background:#fde7c8; color:#8a4b00;}
</style>""", unsafe_allow_html=True)

STAGE_LABELS = {"discover": "1 · Discover", "document": "2 · Document", "redevelop": "3 · Redevelop",
                "validate": "4 · Validate", "monitor": "5 · Monitor"}


def pill(text: str, cls: str) -> str:
    return f'<span class="pill {cls}">{text}</span>'


def src_label(source: str) -> str:
    return f'<span class="src {"ai" if str(source).startswith("ai") else ""}">source: {source}</span>'


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🏦 Model Risk Factory")
    st.caption("Fictional UK bank · prototype")
    reviewer = st.text_input("Reviewer name (for approvals)", value=st.session_state.get("reviewer", ""))
    st.session_state["reviewer"] = reviewer
    page = st.radio("Navigate", ["Overview", "Estate health", "Model inventory", "Documentation", "Redevelopment",
                                 "Validation", "Monitoring", "Approvals & audit trail"])
    st.divider()
    st.markdown("**Pipeline status**")
    s_now = state.load()
    for s in config.PIPELINE_STAGES:
        stt = s_now["stages"][s]["status"]
        st.markdown(f"{STAGE_LABELS[s]} &nbsp; {pill(stt.replace('_', ' '), stt)}", unsafe_allow_html=True)
    st.divider()
    st.caption(f"Claude API: {'connected' if llm.available() else 'not configured - rule-based text used'}")


def stage_control(stage: str, run_kwargs: dict | None = None) -> None:
    """Run / approve / reject panel shown at the top of each stage page."""
    s = state.load()["stages"][stage]
    ok, reason = state.can_run(stage)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 1.1, 1.1, 1.1])
        with c1:
            st.markdown(f"**Stage {STAGE_LABELS[stage]}** &nbsp; {pill(s['status'].replace('_', ' '), s['status'])}",
                        unsafe_allow_html=True)
            if s.get("run_at"):
                st.caption(f"Last run {s['run_at']} by {s['run_by']} in {s['duration_seconds']} s")
            if s.get("review"):
                rv = s["review"]
                st.caption(f"{rv['decision'].capitalize()} by {rv['reviewer']} at {rv['at']}"
                           + (" (AUTOMATED)" if rv.get("automated") else "")
                           + (f" - “{rv['comment']}”" if rv.get("comment") else ""))
            if not ok:
                st.warning(reason, icon="🔒")
        with c2:
            if st.button("▶ Run" if s["status"] == "not_started" else "↻ Re-run", key=f"run_{stage}",
                         disabled=not ok, width="stretch", type="primary"):
                with st.spinner(f"Running {stage} agent..."):
                    try:
                        pipeline.run_stage(stage, actor=reviewer or state.default_user(), **(run_kwargs or {}))
                        st.toast(f"{stage} completed - review the output, then approve or reject.")
                    except Exception as exc:  # shown in UI, also logged to audit
                        st.error(f"{stage} failed: {exc}")
                st.rerun()
        reviewable = s["status"] in ("completed", "approved", "rejected")
        comment = c1.text_input("Review comment", key=f"comment_{stage}", disabled=not reviewable,
                                placeholder="What did you check?")
        with c3:
            if st.button("✔ Approve", key=f"approve_{stage}", disabled=not reviewable or not reviewer,
                         width="stretch"):
                state.record_review(stage, "approved", reviewer, comment)
                st.rerun()
        with c4:
            if st.button("✖ Reject", key=f"reject_{stage}", disabled=not reviewable or not reviewer,
                         width="stretch"):
                state.record_review(stage, "rejected", reviewer, comment)
                st.rerun()
        if reviewable and not reviewer:
            st.caption("Enter your name in the sidebar to approve or reject.")


def header(title: str, sub: str) -> None:
    st.markdown(f'<div class="mrf-header"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- pages
inv = read_json(config.INVENTORY_FILE)

if page == "Overview":
    header("Model Risk Factory", "AI-assisted documentation, redevelopment, validation and monitoring of a bank's model inventory")
    s = state.load()["stages"]
    val_sum = read_json(config.REPORTS_DIR / "validation_summary.json")
    mon = monitor.load_latest()
    n_models = inv["n_models"] if inv else 0
    n_docs = len(list(config.MODEL_CARDS_DIR.glob("*.json"))) if s["document"]["status"] != "not_started" else 0
    par = redevelop.load_parity("CR-PD-001") if s["redevelop"]["status"] != "not_started" else None
    n_val = sum(v["rag"] != "NOT VALIDATED" for v in val_sum["models"].values()) if val_sum and s["validate"]["status"] != "not_started" else 0
    n_alerts = len(mon["alerts"]) if mon and s["monitor"]["status"] != "not_started" else 0
    k = st.columns(5)
    k[0].metric("Models discovered", n_models)
    k[1].metric("Models documented", n_docs)
    k[2].metric("Redevelopment parity", (par["verdict"].split(" ")[0] if par else "-"))
    k[3].metric("Models validated", n_val)
    k[4].metric("Monitoring alerts", n_alerts)

    st.subheader("Pipeline")
    cols = st.columns(5)
    for c, stg in zip(cols, config.PIPELINE_STAGES):
        info = s[stg]
        c.markdown(f"**{STAGE_LABELS[stg]}**<br>{pill(info['status'].replace('_', ' '), info['status'])}",
                   unsafe_allow_html=True)
        if info.get("duration_seconds") is not None:
            c.caption(f"{info['duration_seconds']} s machine time")

    if val_sum and s["validate"]["status"] != "not_started":
        st.subheader("Validation results")
        rows = []
        for mid, v in val_sum["models"].items():
            m = next(x for x in inv["models"] if x["model_id"] == mid)
            rows.append({"Model": mid, "Name": m["model_name"], "Language": m["language"],
                         "RAG": v["rag"], "Test AUC": v.get("test_auc"), "Score PSI": v.get("score_psi"),
                         "Findings": v.get("findings")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Business impact (estimate)")
    imp = impact.estimate()
    c = st.columns(3)
    c[0].metric("Validation effort per model - today", f"{imp['per_model_days']['manual'][0]}-{imp['per_model_days']['manual'][1]} days")
    c[1].metric("With factory (assumed human review)", f"{imp['per_model_days']['with_factory']} days")
    c[2].metric("Effort reduction", f"{imp['effort_reduction_range'][0]:.0%}-{imp['effort_reduction_range'][1]:.0%}")
    st.caption(f"Measured: {imp['measured']['models_processed']} models processed in "
               f"{imp['measured']['machine_time_seconds_all_stages']} s of machine time across all stages. "
               f"Estate of {imp['assumptions']['estate_size']} models: ~{imp['estate_person_years']['manual'][0]:.0f}-"
               f"{imp['estate_person_years']['manual'][1]:.0f} person-years manually vs "
               f"~{imp['estate_person_years']['with_factory']:.0f} with the factory. {imp['caveat']}")
    with st.expander("Dataset"):
        st.json(data.describe())

elif page == "Estate health":
    header("Estate health", "One verdict per model - which R, Python or SAS models are failing, blocked or need attention")
    p = portfolio.build()
    if p is None:
        st.info("Run the Discover stage first (Model inventory page).")
    else:
        st.markdown(src_label("rule-based on computed results - no AI"), unsafe_allow_html=True)
        cols = st.columns(len(portfolio.STATUS_ORDER))
        for c, s_ in zip(cols, portfolio.STATUS_ORDER):
            c.metric("OK" if s_ == "OK" else s_.title(), p["status_counts"][s_])
        st.markdown("**By language**")
        st.dataframe(pd.DataFrame(p["by_language"]).T.rename_axis("Language")[portfolio.STATUS_ORDER],
                     width="stretch")
        st.markdown("**Every model, worst first**")
        for r in p["models"]:
            with st.container(border=True):
                c1, c2 = st.columns([1.1, 3])
                c1.markdown(f"{pill(r['status'], r['status'].replace(' ', '-'))}<br>**{r['model_id']}** · {r['language']}"
                            f"<br><span style='font-size:.85rem'>{r['model_name']}</span>", unsafe_allow_html=True)
                c2.markdown(f"Validation **{r['validation_rating']}**"
                            + (f" · AUC {r['test_auc']:.3f}" if r["test_auc"] is not None else "")
                            + f" · Parity {r['parity']} · Monitoring **{r['monitoring_status']}**"
                            + f" · Documented: {'yes' if r['documented'] else 'no'}")
                if r["reasons"]:
                    c2.markdown("\n".join(f"- {x}" for x in r["reasons"]))
        with st.expander("How the status is decided"):
            st.dataframe(pd.DataFrame({"Status": list(p["status_rules"]), "Rule": list(p["status_rules"].values())}),
                         hide_index=True, width="stretch")
        html_file = config.REPORTS_DIR / "portfolio_report.html"
        if html_file.exists():
            st.download_button("Download estate health report (HTML)", html_file.read_text(),
                               "portfolio_report.html", mime="text/html")
            with st.expander("Preview HTML report"):
                components.html(html_file.read_text(), height=900, scrolling=True)

elif page == "Model inventory":
    header("Model inventory", "Stage 1 - the Discover agent scans legacy code (R, Python, SAS) without executing it")
    stage_control("discover")
    if inv and state.load()["stages"]["discover"]["status"] != "not_started":
        st.markdown(src_label("extracted - deterministic static analysis"), unsafe_allow_html=True)
        df = pd.DataFrame([{
            "Model ID": m["model_id"], "Name": m["model_name"], "Language": m["language"],
            "Methodology": m["methodology"], "Target": m["target_variable"], "# inputs": m["n_features"],
            "Risk tier": m["risk_tier"].split(" - ")[0], "Docs age (yrs)": m["documentation_age_years"],
            "Executable": "✔" if m["executable"] else "✖", "Owner": m["owner"]} for m in inv["models"]])
        st.dataframe(df, hide_index=True, width="stretch")
        for m in inv["models"]:
            with st.expander(f"{m['model_id']} - {m['model_name']}"):
                st.write(f"**Source:** `{m['source_file']}` · SHA-256 `{m['sha256'][:16]}...` · "
                         f"{m['lines_of_code']} lines · {m['execution_note']}")
                st.write("**Inputs:** " + ", ".join(m["input_features"]))
                st.json(m, expanded=False)
        st.download_button("Download inventory.json", config.INVENTORY_FILE.read_text(), "inventory.json")

elif page == "Documentation":
    header("Model documentation", "Stage 2 - the Document agent writes a draft model card for every model")
    stage_control("document")
    if inv and state.load()["stages"]["document"]["status"] != "not_started":
        mid = st.selectbox("Model", [m["model_id"] for m in inv["models"]],
                           format_func=lambda x: f"{x} - {next(m['model_name'] for m in inv['models'] if m['model_id'] == x)}")
        card = document.load_card(mid)
        if card:
            st.markdown(src_label("facts: extracted") + " &nbsp; " + src_label(f"narrative: {card['narrative']['source']}"),
                        unsafe_allow_html=True)
            st.markdown((config.MODEL_CARDS_DIR / f"{mid}.md").read_text())
            st.download_button("Download model card (Markdown)", (config.MODEL_CARDS_DIR / f"{mid}.md").read_text(), f"{mid}.md")

elif page == "Redevelopment":
    header("Redevelopment", "Stage 3 - the Redevelop agent migrates the R scorecard to Python and proves parity")
    stage_control("redevelop")
    par = redevelop.load_parity("CR-PD-001")
    if par and state.load()["stages"]["redevelop"]["status"] != "not_started":
        mode_txt = {"GENUINE_R_LIVE": "Genuine - R executed now",
                    "GENUINE_R_RECORDED": "Genuine - recorded R outputs",
                    "SIMULATED": "SIMULATED - no R available"}[par["legacy_mode"]]
        k = st.columns(4)
        k[0].metric("Verdict", par["verdict"].split(" ")[0])
        k[1].metric("Max |Δ| test PD", f"{par['test_predictions']['max_abs_diff']:.1e}")
        k[2].metric("Max |Δ| coefficient", f"{par['coefficients']['max_abs_diff']:.1e}")
        k[3].metric("Legacy source", mode_txt)
        st.caption(f"Tolerance {par['tolerance']:g} · {par['test_predictions']['n_compared']} test + "
                   f"{par['train_predictions']['n_compared']} train records compared · {par['legacy_note']} "
                   + (f"R: {par['r_run_info'].get('r_version', '')}, run {par['r_run_info'].get('run_utc', '')}" if par["r_run_info"] else ""))
        if par["legacy_mode"] == "SIMULATED":
            st.error("Parity shown here is SIMULATED and does not prove an R-to-Python migration.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Coefficients: R vs Python**")
            coef = pd.DataFrame(par["coefficients"]["table"])
            coef.columns = ["Term", "R estimate", "Python estimate", "|Δ|"]
            st.dataframe(coef.style.format({"R estimate": "{:.8f}", "Python estimate": "{:.8f}", "|Δ|": "{:.1e}"}),
                         hide_index=True, width="stretch", height=420)
        with c2:
            st.markdown("**Test predictions: R vs Python**")
            r = pd.read_csv(config.LEGACY_ARTIFACTS / "CR-PD-001_r_test_scores.csv")
            p = pd.read_csv(config.REDEVELOPED_DIR / "CR-PD-001_python_test_scores.csv")
            both = r.merge(p, on="customer_id", suffixes=("_R", "_Python"))
            st.scatter_chart(both, x="pd_R", y="pd_Python", height=400)
        with st.expander(f"Generated Python code: {par['generated_python_module']}"):
            st.code((config.ROOT / par["generated_python_module"]).read_text(), language="python")
        with st.expander("Legacy R source"):
            st.code((config.ROOT / par["legacy_source"]).read_text(), language="r")

elif page == "Validation":
    header("Validation", "Stage 4 - performance, stability and fairness, all calculated by deterministic Python")
    stage_control("validate")
    if inv and state.load()["stages"]["validate"]["status"] != "not_started":
        ordered = sorted(inv["models"], key=lambda m: not m["executable"])
        mid = st.selectbox("Model", [m["model_id"] for m in ordered],
                           format_func=lambda x: f"{x} - {next(m['model_name'] for m in inv['models'] if m['model_id'] == x)}")
        r = validate.load_validation(mid)
        if not r:
            st.info("This model was not validated: it cannot be executed in the factory (SAS documentation-only). "
                    "See its model card for the documented risks.")
        else:
            t = r["performance"]["test"]
            st.markdown(f"Overall rating {pill(r['rag_rating'], r['rag_rating'])} &nbsp; {src_label('computed')}",
                        unsafe_allow_html=True)
            k = st.columns(6)
            k[0].metric("AUC", f"{t['auc']:.3f}", f"{t['auc'] - r['performance']['train']['auc']:+.3f} vs train")
            k[1].metric("Gini", f"{t['gini']:.3f}")
            k[2].metric("KS", f"{t['ks']:.3f}")
            k[3].metric("Brier", f"{t['brier']:.3f}")
            k[4].metric("Score PSI", f"{r['stability']['score_psi']:.3f}", r["stability"]["score_psi_status"], delta_color="off")
            k[5].metric("Approval rate", f"{t['cost']['approval_rate']:.0%}")
            st.markdown(f"**Commentary** {src_label(r['commentary']['source'])}", unsafe_allow_html=True)
            st.write(r["commentary"]["text"])
            tabs = st.tabs(["Findings", "Performance", "Stability", "Fairness", "Full HTML report"])
            with tabs[0]:
                st.dataframe(pd.DataFrame(r["findings"]), hide_index=True, width="stretch")
            with tabs[1]:
                cal = pd.DataFrame(t["calibration_table"])
                c1, c2 = st.columns(2)
                c1.markdown("**Calibration by decile**")
                c1.line_chart(cal.set_index("bin")[["predicted_pd", "observed_dr"]])
                c2.markdown("**Cost at cut-off (approve if PD < %.3f)**" % t["cost"]["threshold"])
                c2.json({k2: t["cost"][k2] for k2 in ["approval_rate", "fn", "fp", "total_cost",
                                                      "baseline_cost_approve_all", "cost_saving_vs_no_model"]})
                c2.caption(f"Hosmer-Lemeshow p-value: {t['hosmer_lemeshow']['p_value']:.3f}")
            with tabs[2]:
                st.dataframe(pd.DataFrame(r["stability"]["feature_psi"]), hide_index=True, width="stretch")
            with tabs[3]:
                for dim, res in r["fairness"].items():
                    st.markdown(f"**{validate.FAIRNESS_DIMENSIONS[dim]}** - reference group: _{res['reference_group']}_")
                    if dim in r["fairness_notes"]:
                        st.caption(r["fairness_notes"][dim])
                    g = pd.DataFrame(res["groups"])[["group", "n", "approval_rate", "true_approval_rate",
                                                     "observed_default_rate", "mean_pd", "disparate_impact_ratio",
                                                     "equal_opportunity_gap", "small_sample"]]
                    st.dataframe(g, hide_index=True, width="stretch")
            with tabs[4]:
                html_path = config.REPORTS_DIR / f"{mid}_validation_report.html"
                html = html_path.read_text()
                st.download_button("Download HTML report", html, html_path.name, mime="text/html")
                components.html(html, height=900, scrolling=True)

elif page == "Monitoring":
    header("Monitoring", "Stage 5 - the Monitor agent scores a simulated production batch and checks for drift")
    c1, c2 = st.columns(2)
    scenario = c1.selectbox("Scenario for the next run", ["drift", "stable"])
    severity = c2.slider("Drift severity", 0.0, 1.0, 0.6, 0.1, disabled=scenario == "stable")
    stage_control("monitor", {"scenario": scenario, "severity": severity if scenario == "drift" else 0.0})
    mon = monitor.load_latest()
    if mon and state.load()["stages"]["monitor"]["status"] != "not_started":
        st.caption(f"Last run: scenario **{mon['scenario']}**, severity {mon['severity']}, "
                   f"{mon['batch_size']} applications. {mon['note']}")
        if mon["alerts"]:
            st.error(f"{len(mon['alerts'])} alerts · re-validation recommended for: "
                     + (", ".join(mon["models_needing_revalidation"]) or "none"))
        else:
            st.success("No alerts - all monitored models within thresholds.")
        rows = []
        for mid, v in mon["models"].items():
            if v.get("monitored"):
                rows.append({"Model": mid, "Status": v["status"], "Score PSI": round(v["score_psi"], 3),
                             "AUC at validation": round(v["auc_validation"], 3) if v["auc_validation"] else None,
                             "AUC new batch": round(v["auc_new_batch"], 3),
                             "Approval rate (validation)": v["approval_rate_validation"],
                             "Approval rate (new)": round(v["approval_rate_new_batch"], 3),
                             "Action": v["action"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.bar_chart(pd.DataFrame(rows).set_index("Model")["Score PSI"])
        st.caption(f"PSI thresholds: WARN ≥ {config.PSI_WARN}, ALERT ≥ {config.PSI_ALERT}")
        st.markdown("**Alerts**")
        if mon["alerts"]:
            st.dataframe(pd.DataFrame(mon["alerts"]), hide_index=True, width="stretch")
        for mid, v in mon["models"].items():
            if v.get("monitored"):
                with st.expander(f"Input drift - {mid}"):
                    st.dataframe(pd.DataFrame(v["feature_psi"]), hide_index=True, width="stretch")

elif page == "Approvals & audit trail":
    header("Approvals & audit trail", "Human oversight: every run, approval and rejection is recorded")
    s = state.load()["stages"]
    rows = []
    for stg in config.PIPELINE_STAGES:
        info, rv = s[stg], s[stg].get("review", {})
        rows.append({"Stage": STAGE_LABELS[stg], "Status": info["status"], "Run at": info.get("run_at"),
                     "Run by": info.get("run_by"), "Reviewer": rv.get("reviewer"),
                     "Decision at": rv.get("at"), "Automated": rv.get("automated"), "Comment": rv.get("comment")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown("**Approve or reject any completed stage**")
    for stg in config.PIPELINE_STAGES:
        stage_control(stg) if s[stg]["status"] != "not_started" else None
    log = state.read_audit()
    st.markdown(f"**Audit log** ({len(log)} events, newest first)")
    if log:
        st.dataframe(pd.DataFrame([{k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                                    for k, v in e.items()} for e in reversed(log)]),
                     hide_index=True, width="stretch")
        st.download_button("Download audit_log.jsonl", config.AUDIT_LOG.read_text(), "audit_log.jsonl")
    if st.button("Reset pipeline statuses (outputs are kept)"):
        state.reset()
        st.rerun()
