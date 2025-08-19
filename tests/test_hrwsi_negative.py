
import pathlib, pytest
from .conftest import load_schema_by_name, match_example

def _neg(schema_fname, bad_examples):
    repo_root = pathlib.Path(__file__).parents[1]
    src_root = repo_root / "src"
    schema, path = load_schema_by_name(str(src_root), schema_fname)
    patt = schema["filename_pattern"]
    for ex in bad_examples:
        assert not match_example(patt, ex), f"Unexpected match in {path}: {ex}"

def test_wic_s2_negatives():
    _neg("wic_s2_filename_structure.json", [
        "CLMS_WSI_WIC_020m_T31TCH_20160720T105547_S1A_V100_WIC-QA.tif",
        "CLMS_WSI_WIC_060m_T31TCH_20160720T105547_S2A_V100_WIC.tif",
        "CLMS_WSI_XXX_020m_T31TCH_20160720T105547_S2A_V100_WIC.tif",
    ])

def test_wic_s1_negatives():
    _neg("wic_s1_filename_structure.json", [
        "CLMS_WSI_WIC_060m_T34UEG_20170214T044301_S2A_V100_WIC.tif",
        "CLMS_WSI_WIC_060m_T34UEG_20170214T044301_S1A_V100_PRB.tif",
    ])

def test_wic_comb_negatives():
    _neg("wic_comb_filename_structure.json", [
        "CLMS_WSI_WIC_020m_T31TCH_20160720T060000P12H_COMB_V100_WIC-QA.tif",
        "CLMS_WSI_WIC_020m_T31TCH_20160720T120000P12H_S2_V100_WIC-QA.tif",
    ])

def test_icd_negatives():
    _neg("icd_filename_structure.json", [
        "CLMS_WSI_ICD_020m_E70NX0_20160901P1Y_COMB_V100_ICD-QA.tif",
        "CLMS_WSI_ICD_020m_T31TCH_20160901P1Y_S2_V100_ICD-QA.tif",
    ])

def test_fsc_negatives():
    _neg("fsc_filename_structure.json", [
        "CLMS_WSI_FSC_020m_T32TNS_20211018T103021_S1A_V100_FSCOG.tif",
        "CLMS_WSI_FSC_020m_T32TNS_20211018T103021_S2A_V100_WIC.tif",
    ])

def test_gfsc_negatives():
    _neg("gfsc_filename_structure.json", [
        "CLMS_WSI_GFSC_020m_T32TNS_20211018P7D_COMB_V100_GF-QA.tif",
        "CLMS_WSI_GFSC_060m_T32TNS_20211018P7D_V100_GF-QA.tif",
    ])

def test_sws_negatives():
    _neg("sws_filename_structure.json", [
        "CLMS_WSI_SWS_060m_T32TNS_20210217T053159_S1B_V100_SSC.tif",
    ])

def test_wds_negatives():
    _neg("wds_filename_structure.json", [
        "CLMS_WSI_WDS_060m_T32TNS_20210217T053159_S1B_V100_WSM.tif",
    ])

def test_sp_s2_negatives():
    _neg("sp_s2_filename_structure.json", [
        "CLMS_WSI_SP_020m_T38TKL_20200901P1Y_COMB_V100_SCD.tif",
    ])

def test_sp_comb_negatives():
    _neg("sp_comb_filename_structure.json", [
        "CLMS_WSI_SP_060m_T38TKL_20200901P1Y_S2_V100_SCD-QA.tif",
    ])

def test_cc_negatives():
    _neg("cc_filename_structure.json", [
        "CLMS_WSI_WIC_020m_T32TNS_20211018T103021_S2A_V100_CC.tif",
        "CLMS_WSI_CC_020m_T32TNS_20211018T103021_S1B_V100_CC.tif",
    ])


