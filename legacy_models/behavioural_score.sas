/* ===========================================================================
   MODEL_ID:     CR-BH-004
   MODEL_NAME:   Behavioural Credit Score (Existing Customers)
   OWNER:        Retail Credit Risk Analytics
   PURPOSE:      Monthly re-scoring of existing borrowers' probability of default
   USE:          Limit management and provisioning inputs
   LANGUAGE:     SAS
   LAST_REVIEW:  2017-05 (documentation out of date)
   NOTE:         DOCUMENTATION-ONLY in this prototype. No SAS licence is used;
                 the factory reads and documents this code but does not run it.
   =========================================================================== */

libname crd '/data/credit/prod';

/* Derive behavioural features */
data work.beh_base;
    set crd.monthly_accounts;
    where snapshot_month >= '01JAN2016'd;
    util_ratio      = balance / max(credit_limit, 1);
    months_on_book  = intck('month', open_date, snapshot_month);
    if months_on_book < 6 then delete;          /* exclude new accounts */
    max_arrears_6m  = max(of arrears_m1-arrears_m6);
    default_flag    = (days_past_due_next12 >= 90);
run;

/* Coarse classing of utilisation */
data work.beh_base;
    set work.beh_base;
    length util_band $10;
    if util_ratio < 0.3 then util_band = 'LOW';
    else if util_ratio < 0.8 then util_band = 'MEDIUM';
    else util_band = 'HIGH';
run;

proc logistic data=work.beh_base descending outmodel=crd.beh_score_model;
    class util_band (ref='LOW') / param=ref;
    model default_flag = util_band max_arrears_6m months_on_book age
          / selection=stepwise slentry=0.05 slstay=0.05;
    output out=work.beh_scored p=pd_behavioural;
run;

proc rank data=work.beh_scored out=crd.beh_scored_ranked groups=10;
    var pd_behavioural;
    ranks score_decile;
run;
