#!/usr/bin/env python3
"""Test gateway: runs all tests, prints PASS/FAIL per file. Exit 1 on fail."""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
TESTS = ["test_theme", "test_theme_mode", "test_hijri", "test_database", "test_pdf", "test_auth", "test_currency", "test_world", "test_prescriptions", "test_medications_full", "test_phrases", "test_arch", "test_telemetry", "test_no_activation", "test_specialties", "test_scans", "test_clipboard_multi", "test_sync_roles", "test_password_change", "test_username_rename", "test_clinical_cost", "test_screenshot_fixes", "test_finance_permissions", "test_finance_sync", "test_finance_sync_nurse", "test_salaries", "test_user_management", "test_net_consistency", "test_sync_button", "test_dark_contrast", "test_name_colors", "test_name_column", "test_birth_date", "test_language_persist", "test_dental_chart", "test_appointments_calendar", "test_finance_bg", "test_bak_restore", "test_settings_bundle", "test_settings_overflow", "test_app_icon", "test_data_location", "test_clinical_redesign", "test_clinical_contrast", "test_add_drug", "test_toggle_speed", "test_i18n_shell", "test_i18n_clinical", "test_i18n_ops", "test_sync_prompt", "test_edit_24h", "test_last_login", "test_scans_upload", "test_appointments_quickbook", "test_wheel_scroll", "test_wheel_audit", "test_wheel_app", "test_wheel_chart", "test_wheel_native", "test_wheel_native2", "test_clinical_save_gate", "test_clinical_history_edit", "test_patient_alerts", "test_patient_alerts_form", "test_finance_totals", "test_finance_lock", "test_perm_tree", "test_templates_edit", "test_templates_gui", "test_finance_totals_gui", "test_perm_tree_gui", "test_last_login_list", "test_login_privacy", "test_payments_e2e", "test_payments_form", "test_payments_default_doctor", "test_dental_chart_order", "test_teeth_regen", "test_r34_teeth_refine", "test_r35_teeth_anatomy", "test_rounded", "test_rounded_finance", "test_rounded_all", "test_rounded_all_static", "test_paper_texture", "test_paper_texture_tree", "test_round13_item4", "test_panel_paper", "test_about_dev", "test_templates_r15", "test_patient_save", "test_teeth_flip", "test_teeth_flip_gui", "test_clinical_tables_r15", "test_clinical_panels", "test_teeth_contrast", "test_rx_r16", "test_rx_print_r16", "test_rx_pdf_r16", "test_telemetry_firebase", "test_no_white_bg", "test_lang_purity",
 "test_r16_patients", "test_r16_patients_search", "test_r16_patients_dup", "test_r16_clinical_save", "test_r16_clinical_panels", "test_r16_chart_status", "test_r16_strings", "test_r16_print", "test_r16_print_files", "test_r16_print_gui", "test_settings_storage_r16", "test_users_layout_r16", "test_clinic_name_r16", "test_print_preview_shell_r16",
 "test_r17_no_login_modal", "test_r17_lang_templates", "test_r17_new_patient_modal", "test_r17_chart_state", "test_r17_teeth_notes", "test_r17_finance_boxes",
 "test_r18_notes_templates", "test_r18_template_caps", "test_r18_search_phone", "test_r18_patient_edit_delete", "test_r18_patient_delete", "test_r18_clinical_layout", "test_r18_rx_layout", "test_r18_attendance", "test_r18_invoice", "test_r18_info_panel_visible", "test_r19_birth_date", "test_r19_diseases", "test_r19_rx_print", "test_r19_currency_view", "test_r19_currency_gui", "test_r19_debtors", "test_r19_referrals", "test_r19_layout", "test_r20_alerts", "test_r21_medications_audit", "test_r21_pdf_header", "test_r21_template_search", "test_r21_layout_red", "test_r21_allergy_templates", "test_r21_refer_dialog", "test_r21_perm_gating", "test_r21_finance_currencies", "test_r21_dark_zebra", "test_r21_toggle_perf", "test_r22_layout", "test_r22_shell_rx",
 "test_r23_table_order", "test_r23_history_money", "test_r23_chart_treated", "test_r23_meds_doses", "test_r23_pdf_no_sadaqah", "test_r23_referral_nurse", "test_r23_referral_sync", "test_r23_payment_entry", "test_r23_currencies_e2e", "test_r23_rx_strength",
 "test_r24_session_money", "test_r24_attendance_board", "test_r24_referral_print", "test_r24_meds_lang", "test_r24_expense_icons", "test_r24_category_picker", "test_r24_unified_table", "test_r24_session_edit", "test_r24_zebra_audit", "test_r24_zebra_lists", "test_r24_toggle_perf", "test_r24_login_role",
 "test_r25_hijri_lang", "test_r25_scans_multi", "test_r25_currency_search", "test_r25_name_order", "test_r25_no_paths",
 "test_r26_searchable_pickers", "test_r27_thumb_grid",
 "test_r28_radius", "test_r28_finance_narrow", "test_r28_drug_diseases",
 "test_r28_interactions", "test_r29_allergy_fix", "test_r30_logo",
 "test_r30_user_drug_alerts", "test_r30_user_drug_gui", "test_r31_pdf_footer", "test_r31_radius", "test_r31_finance_colours", "test_r31_template_lang", "test_r31_toggle_perf", "test_r31_db_init_cache",
 "test_r32_search_equiv", "test_r32_norms_writepaths",
 "test_r37_micro_text_8pt",
 "test_r38_country", "test_r38_templates", "test_r38_credit",
 "test_r38_payment_layout", "test_r38_image_viewer",
 "test_r39_delta_sync", "test_r39_delta_sync2",
 "test_r40_single_payment_place", "test_r40_single_payment_flows",
 "test_r40_vivid_rows", "test_r41_owner_feedback", "test_r41_teeth", "test_r42_license",
 "test_r43_field_lang", "test_r43_jaw_vivid_radius",
 "test_r44_update", "test_r44_update_gui", "test_r45_contact", "test_r45_centre_phone",
 "test_r46_purge", "test_r48_palette", "test_r48_nationality",
 "test_r49_meds_data", "test_r49_meds_engine", "test_r49_meds_scope",
 "test_r49_" + "whats" + "app",
 "test_r49_templates_clean", "test_r49_date_edit", "test_r49_statistics",
 "test_r50_meds_fixes", "test_r51_perf", "test_r51_charts", "test_r52_about_lang", "test_r52_toggle_ops", "test_r52_charts_scaling", "test_r52_month_names", "test_r52_centre_contact", "test_r52_tree_rows", "test_r53_main_fit", "test_r53_topbar",
 "test_r54_clinical_header", "test_r54_referral_contact", "test_r54_centre_mobile2",
 "test_r54_finance_scroll",
 "test_r55_header_adherence", "test_r55_adherence_model", "test_r55_charts_bidi",
 "test_r56_font_revert", "test_r56_wheel_page",
 "test_r57_settings_preview", "test_r57_meds_templates"]
def main():
    failed = 0
    for name in TESTS:
        try:
            mod = __import__(f"tests.{name}", fromlist=["x"])
            for fn in sorted([a for a in dir(mod) if a.startswith("test_")]):
                getattr(mod, fn)()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(TESTS)-failed}/{len(TESTS)} test files passed")
    sys.exit(1 if failed else 0)
if __name__ == "__main__":
    main()
