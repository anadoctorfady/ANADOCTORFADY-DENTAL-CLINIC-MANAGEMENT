"""R23 medications audit #3: doses / strengths (عيارات).

Round-23 item 4. The seed list had 231 of 315 entries (every entry
from Cefixime onward) with an EMPTY strength and a blanket "Tablet"
form, plus 3 defects in the curated head: Mefenamic Acid as a
500 mg CAPSULE (500 mg is the tablet; capsules are 250 mg), and
Heparin / Vitamin D3 (Vidrop) strengths missing their "/ml"
denominator. EXPECTED_* below pin every corrected value; the full
reasoning is in round23_gate/meds_doses_audit.md. Pure file reads:
no app imports, no display, no live DB.
"""
import json, re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "src" / "data"
# number, optional /number (combination or per-volume), unit, and an
# optional denominator: 500 mg, 800/160 mg, 125 mcg, 0.005%,
# 100 IU/ml, 100,000 IU/ml, 3.35 g/5 ml, 25 mcg/h, 100 mcg/dose.
# R50: the audited FDC corrections added three legitimate shapes --
# multi-component chains sharing one unit (4/5/1.25 mg,
# 150/75/400/275 mg), per-component units (50 mg/200 mcg,
# 600 mg/400 IU), and " + "-joined concentrations
# (100 IU/ml + 33 mcg/ml) -- so the pattern accepts those too.
_NUM = r"[0-9][0-9,]*(\.[0-9]+)?"
_UNIT = r"(mg|mcg|g|IU|%)"
_DEN = r"(/(ml|5 ml|0\.5 ml|dose|h))?"
_DOSE = _NUM + r"\s*" + _UNIT + _DEN
STRENGTH_RE = re.compile(
    r"^(" + _DOSE + r"|" + _NUM + r"(/" + _NUM + r")+\s*" + _UNIT + _DEN
    + r"|" + _DOSE + r"(/" + _DOSE + r")+"
    + r"|" + _DOSE + r"( \+ " + _DOSE + r")+)$")
EXPECTED_STRENGTH = {
    "Cefixime": "400 mg", "Cefpodoxime": "200 mg", "Ceftriaxone": "1 g", "Cefazolin": "1 g",
    "Cefdinir": "300 mg", "Meropenem": "1 g", "Imipenem": "500 mg", "Ertapenem": "1 g",
    "Vancomycin": "125 mg", "Gentamicin": "40 mg/ml", "Tobramycin": "0.3%", "Amikacin": "250 mg/ml",
    "Neomycin": "500 mg", "Nitrofurantoin": "100 mg", "Fosfomycin": "3 g", "Linezolid": "600 mg",
    "Rifampicin": "300 mg", "Isoniazid": "300 mg", "Pyrazinamide": "500 mg", "Ethambutol": "400 mg",
    "Dapsone": "100 mg", "Chloramphenicol": "250 mg", "Trimethoprim": "200 mg", "Minocycline": "100 mg",
    "Moxifloxacin": "400 mg", "Ofloxacin": "400 mg", "Tinidazole": "500 mg", "Itraconazole": "100 mg",
    "Voriconazole": "200 mg", "Ketoconazole": "2%", "Terbinafine": "250 mg", "Clotrimazole": "1%",
    "Ketoprofen": "100 mg", "Meloxicam": "15 mg", "Piroxicam": "20 mg", "Indomethacin": "25 mg",
    "Etoricoxib": "90 mg", "Morphine": "30 mg", "Oxycodone": "10 mg", "Fentanyl": "25 mcg/h",
    "Buprenorphine": "2 mg", "Methadone": "10 mg", "Gabapentin": "300 mg", "Pregabalin": "75 mg",
    "Duloxetine": "60 mg", "Baclofen": "10 mg", "Tizanidine": "4 mg", "Orphenadrine": "100 mg",
    "Ramipril": "5 mg", "Enalapril": "10 mg", "Perindopril": "4 mg", "Captopril": "25 mg",
    "Candesartan": "8 mg", "Irbesartan": "150 mg", "Olmesartan": "20 mg", "Metoprolol": "50 mg",
    "Bisoprolol": "5 mg", "Carvedilol": "25 mg", "Propranolol": "40 mg", "Nebivolol": "5 mg",
    "Verapamil": "80 mg", "Diltiazem": "60 mg", "Nifedipine": "30 mg", "Felodipine": "5 mg",
    "Chlorthalidone": "25 mg", "Indapamide": "1.5 mg", "Spironolactone": "25 mg", "Eplerenone": "25 mg",
    "Rosuvastatin": "10 mg", "Pravastatin": "40 mg", "Fenofibrate": "200 mg", "Gemfibrozil": "600 mg",
    "Ezetimibe": "10 mg", "Dabigatran": "150 mg", "Edoxaban": "60 mg", "Ticagrelor": "90 mg",
    "Prasugrel": "10 mg", "Ticlopidine": "250 mg", "Dipyridamole": "100 mg", "Nitroglycerin": "0.4 mg",
    "Isosorbide Dinitrate": "20 mg", "Digoxin": "125 mcg", "Amiodarone": "200 mg", "Flecainide": "100 mg",
    "Sotalol": "80 mg", "Hydralazine": "25 mg", "Glipizide": "5 mg", "Glyburide": "5 mg",
    "Linagliptin": "5 mg", "Saxagliptin": "5 mg", "Empagliflozin": "10 mg", "Dapagliflozin": "10 mg",
    "Canagliflozin": "100 mg", "Liraglutide": "6 mg/ml", "Semaglutide": "1 mg", "Dulaglutide": "1.5 mg/0.5 ml",
    "Insulin Aspart": "100 IU/ml", "Insulin Lispro": "100 IU/ml", "Insulin Regular": "100 IU/ml", "Insulin NPH": "100 IU/ml",
    "Insulin Detemir": "100 IU/ml", "Insulin Degludec": "100 IU/ml", "Pioglitazone": "30 mg", "Repaglinide": "1 mg",
    "Acarbose": "50 mg", "Salbutamol": "100 mcg/dose", "Terbutaline": "5 mg", "Salmeterol": "25 mcg/dose",
    "Formoterol": "12 mcg/dose", "Budesonide": "200 mcg/dose", "Fluticasone": "250 mcg/dose", "Beclomethasone": "250 mcg/dose",
    "Tiotropium": "18 mcg", "Ipratropium": "20 mcg/dose", "Montelukast": "10 mg", "Theophylline": "300 mg",
    "Fexofenadine": "120 mg", "Desloratadine": "5 mg", "Diphenhydramine": "25 mg", "Pseudoephedrine": "60 mg",
    "Dextromethorphan": "15 mg/5 ml", "Guaifenesin": "600 mg", "Ranitidine": "150 mg", "Famotidine": "20 mg",
    "Lansoprazole": "30 mg", "Esomeprazole": "20 mg", "Rabeprazole": "20 mg", "Metoclopramide": "10 mg",
    "Ondansetron": "8 mg", "Domperidone": "10 mg", "Loperamide": "2 mg", "Bisacodyl": "5 mg",
    "Lactulose": "3.35 g/5 ml", "Senna": "7.5 mg", "Mesalazine": "500 mg", "Sulfasalazine": "500 mg",
    "Aluminium Hydroxide": "500 mg", "Fluoxetine": "20 mg", "Sertraline": "50 mg", "Paroxetine": "20 mg",
    "Citalopram": "20 mg", "Escitalopram": "10 mg", "Venlafaxine": "75 mg", "Mirtazapine": "30 mg",
    "Bupropion": "150 mg", "Amitriptyline": "25 mg", "Nortriptyline": "25 mg", "Imipramine": "25 mg",
    "Phenelzine": "15 mg", "Tranylcypromine": "10 mg", "Haloperidol": "5 mg", "Risperidone": "2 mg",
    "Olanzapine": "10 mg", "Quetiapine": "100 mg", "Aripiprazole": "10 mg", "Chlorpromazine": "25 mg",
    "Clozapine": "100 mg", "Lithium": "400 mg", "Lamotrigine": "100 mg", "Levetiracetam": "500 mg",
    "Topiramate": "50 mg", "Lorazepam": "1 mg", "Alprazolam": "0.5 mg", "Clonazepam": "0.5 mg",
    "Zolpidem": "10 mg", "Donepezil": "10 mg", "Memantine": "10 mg", "Levodopa": "100 mg",  # R50 F14: was "25/100 mg" (Sinemet FDC notation on a single)
    "Selegiline": "10 mg", "Methylprednisolone": "4 mg", "Betamethasone": "0.5 mg", "Triamcinolone": "40 mg/ml",
    "Ethinyl Estradiol": "30 mcg", "Levonorgestrel": "1.5 mg", "Medroxyprogesterone": "150 mg/ml", "Testosterone": "1%",
    "Desmopressin": "0.2 mg", "Azathioprine": "50 mg", "Cyclosporine": "100 mg", "Tacrolimus": "1 mg",
    "Mycophenolate": "250 mg", "Adalimumab": "40 mg", "Etanercept": "50 mg", "Infliximab": "100 mg",
    "Hydroxychloroquine": "200 mg", "Mometasone": "0.1%", "Timolol": "0.5%", "Latanoprost": "0.005%",
    "Dorzolamide": "2%", "Vitamin B12": "1000 mcg", "Vitamin C": "500 mg", "Zinc": "50 mg",
    "Magnesium": "250 mg", "Omega-3": "1000 mg", "Cholecalciferol": "200,000 IU", "Sildenafil": "50 mg",
    "Tadalafil": "10 mg", "Finasteride": "5 mg", "Tamsulosin": "0.4 mg", "Oxybutynin": "5 mg",
    "Tolterodine": "2 mg", "Mirabegron": "50 mg", "Rivastigmine": "3 mg", "Modafinil": "200 mg",
    "Methylphenidate": "10 mg", "Atomoxetine": "40 mg", "Clonidine": "100 mcg", "Methyldopa": "250 mg",
    "Prazosin": "1 mg", "Doxazosin": "4 mg", "Amphotericin B": "50 mg", "Oseltamivir": "75 mg",
    "Ritonavir": "100 mg", "Tenofovir": "300 mg", "Entecavir": "0.5 mg", "Albendazole": "200 mg",
    "Mebendazole": "100 mg", "Ivermectin": "3 mg", "Praziquantel": "600 mg", "Misoprostol": "200 mcg",
    "Oxytocin": "10 IU/ml", "Tranexamic Acid": "500 mg", "Vitamin K": "10 mg/ml", "Naloxone": "0.4 mg/ml",
    "Epinephrine": "1 mg/ml", "Atropine": "1 mg/ml", "Isotretinoin": "20 mg", "Adapalene": "0.1%",
    "Benzoyl Peroxide": "5%", "Brimonidine": "0.2%", "Pilocarpine": "2%", "Mefenamic Acid": "500 mg",
    "Heparin": "5000 IU/ml", "Vitamin D3": "2800 IU/ml",
}
EXPECTED_FORM = {
    "Ceftriaxone": "Injection", "Cefazolin": "Injection", "Cefdinir": "Capsule", "Meropenem": "Injection",
    "Imipenem": "Injection", "Ertapenem": "Injection", "Vancomycin": "Capsule", "Gentamicin": "Injection",
    "Tobramycin": "Eye drops", "Amikacin": "Injection", "Nitrofurantoin": "Capsule", "Fosfomycin": "Granules",
    "Rifampicin": "Capsule", "Chloramphenicol": "Capsule", "Itraconazole": "Capsule", "Ketoconazole": "Cream",
    "Clotrimazole": "Cream", "Ketoprofen": "Capsule", "Piroxicam": "Capsule", "Indomethacin": "Capsule",
    "Fentanyl": "Patch", "Buprenorphine": "Sublingual tablet", "Gabapentin": "Capsule", "Pregabalin": "Capsule",
    "Duloxetine": "Capsule", "Ramipril": "Capsule", "Fenofibrate": "Capsule", "Dabigatran": "Capsule",
    "Nitroglycerin": "Sublingual tablet", "Liraglutide": "Injection", "Semaglutide": "Injection", "Dulaglutide": "Injection",
    "Insulin Aspart": "Injection", "Insulin Lispro": "Injection", "Insulin Regular": "Injection", "Insulin NPH": "Injection",
    "Insulin Detemir": "Injection", "Insulin Degludec": "Injection", "Salbutamol": "Inhaler", "Salmeterol": "Inhaler",
    "Formoterol": "Inhaler", "Budesonide": "Inhaler", "Fluticasone": "Inhaler", "Beclomethasone": "Inhaler",
    "Tiotropium": "Inhaler", "Ipratropium": "Inhaler", "Dextromethorphan": "Syrup", "Lansoprazole": "Capsule",
    "Loperamide": "Capsule", "Lactulose": "Syrup", "Fluoxetine": "Capsule", "Venlafaxine": "Capsule",
    "Nortriptyline": "Capsule", "Triamcinolone": "Injection", "Medroxyprogesterone": "Injection", "Testosterone": "Gel",
    "Cyclosporine": "Capsule", "Tacrolimus": "Capsule", "Mycophenolate": "Capsule", "Adalimumab": "Injection",
    "Etanercept": "Injection", "Infliximab": "Injection", "Mometasone": "Cream", "Timolol": "Eye drops",
    "Latanoprost": "Eye drops", "Dorzolamide": "Eye drops", "Omega-3": "Capsule", "Cholecalciferol": "Injection",
    "Tamsulosin": "Capsule", "Rivastigmine": "Capsule", "Atomoxetine": "Capsule", "Amphotericin B": "Injection",
    "Oseltamivir": "Capsule", "Oxytocin": "Injection", "Vitamin K": "Injection", "Naloxone": "Injection",
    "Epinephrine": "Injection", "Atropine": "Injection", "Isotretinoin": "Capsule", "Adapalene": "Gel",
    "Benzoyl Peroxide": "Gel", "Brimonidine": "Eye drops", "Pilocarpine": "Eye drops", "Mefenamic Acid": "Tablet",
}

def _meds():
    return json.loads((DATA / "medications.json").read_text(encoding="utf-8"))

def _by_name():
    return {m["generic_en"]: m for m in _meds()}

def test_count_still_463_and_no_empty_strength():  # R49: 315 + 40 singles + 108 combos
    meds = _meds()
    assert len(meds) == 463, len(meds)  # R49 count pin (was 315)
    assert all(m["strength"].strip() for m in meds), (
        [m["generic_en"] for m in meds if not m["strength"].strip()])

def test_every_strength_parses_to_plausible_unit_pattern():
    for m in _meds():
        assert STRENGTH_RE.match(m["strength"].strip()), (
            m["generic_en"], m["strength"])

def test_r23_corrected_strengths():
    by_name = _by_name()
    assert len(EXPECTED_STRENGTH) == 234, len(EXPECTED_STRENGTH)
    for name, strength in EXPECTED_STRENGTH.items():
        assert by_name[name]["strength"] == strength, (
            name, by_name[name]["strength"], strength)

def test_r23_corrected_forms():
    by_name = _by_name()
    assert len(EXPECTED_FORM) == 84, len(EXPECTED_FORM)
    for name, form in EXPECTED_FORM.items():
        assert by_name[name]["form"] == form, (name, by_name[name]["form"])

def test_r23_no_tablet_only_impossible_forms_remain():
    by_name = _by_name()
    # Drugs with no oral-tablet presentation at all.
    for name in ["Ceftriaxone", "Meropenem", "Insulin Aspart",
                 "Liraglutide", "Adalimumab", "Oxytocin", "Naloxone",
                 "Salmeterol", "Fluticasone", "Lactulose", "Fentanyl",
                 "Latanoprost", "Adapalene", "Amphotericin B"]:
        assert by_name[name]["form"] != "Tablet", name

def test_dental_core_strengths_unchanged_and_correct():
    by_name = _by_name()
    assert by_name["Amoxicillin"]["strength"] == "500 mg"
    assert by_name["Amoxicillin-Clavulanate"]["strength"] == "625 mg"
    assert by_name["Metronidazole"]["strength"] == "500 mg"
    assert by_name["Ibuprofen"]["strength"] == "400 mg"
    assert by_name["Paracetamol"]["strength"] == "500 mg"
    assert by_name["Clindamycin"]["strength"] == "300 mg"
    assert by_name["Doxycycline"]["strength"] == "100 mg"
    assert by_name["Cephalexin"]["strength"] == "500 mg"
    assert by_name["Azithromycin"]["strength"] == "500 mg"
    assert by_name["Chlorhexidine"]["strength"] == "0.2%"
    assert by_name["Lidocaine"]["strength"] == "2%"
    assert by_name["Articaine"]["strength"] == "4%"
    assert by_name["Mepivacaine"]["strength"] == "3%"
    assert by_name["Benzocaine"]["strength"] == "20%"
    assert by_name["Diclofenac Potassium"]["strength"] == "50 mg"
    assert by_name["Etoricoxib"]["strength"] == "90 mg"  # dental-pain dose
