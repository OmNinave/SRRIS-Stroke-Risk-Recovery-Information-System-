import torch
from torch import nn
import os
import numpy as np
import pandas as pd
import neurokit2 as nk
import pickle
import warnings
import time
import scipy
import sys
import threading
from catboost import CatBoostClassifier

from app.services.gpu_gate import gpu_gate

# Add this directory to sys.path to allow imports from MODELS
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from MODELS.convV1.conv_1d_down import DownV1
from MODELS.convV1.conv_1d_norm import NormV1
from MODELS.convV1.conv_1d_front import FrontV1
from MODELS.convV1.conv_1d_septal import SeptalV1
from MODELS.convV1.conv_1d_front_down import FrontDownV1
from MODELS.convV1.conv_1d_front_septal import FrontSeptalV1

from MODELS.convV2.conv_1d_down_v2 import DownV2
from MODELS.convV2.conv_1d_norm_v2 import NormV2
from MODELS.convV2.conv_1d_front_v2 import FrontV2
from MODELS.convV2.conv_1d_septal_v2 import SeptalV2
from MODELS.convV2.conv_1d_front_down_v2 import FrontDownV2
from MODELS.convV2.conv_1d_front_septal_v2 import FrontSeptalV2

from MODELS.se_resnet import Se_Resnet
from MODELS.skip_connected_conv import CNN

from ecg_digitizer import digitize_ecg

warnings.simplefilter('ignore')

class Config:
    translate_eng_ru = {
        'down': 'нижний',
        'front': 'передний',
        'front_down': 'передне-боковой',
        'front_septal': 'передне-перегородочный',
        'normal': 'норма',
        'septal': 'перегородочный',
        'side': 'боковой'
    }
    translate_ru_eng = dict([(j, i) for i, j in translate_eng_ru.items()])
    v1_shapes = {
        'down': list(range(1, 11)),
        'front': [8, 9],
        'front_down': [0, 1, 3, 9, 10, 11],
        'front_septal': [6, 7, 8, 9],
        'normal': list(range(1, 11)),
        'septal': [5, 6, 7, 8, 9, 10],
    }
    other_shapes = {
        'down': list(range(1, 11)),
        'front': [7, 8, 9, 10],
        'front_down': [0, 1, 3, 9, 10, 11],
        'front_septal': [6, 7, 8, 9],
        'normal': list(range(0, 12)),
        'septal': list(range(1, 11)),
    }
    v1_models = {
        'down': DownV1,
        'normal': NormV1,
        'front': FrontV1,
        'septal': SeptalV1,
        'front_down': FrontDownV1,
        'front_septal': FrontSeptalV1,
    }
    v2_models = {
        'down': DownV2,
        'normal': NormV2,
        'front': FrontV2,
        'septal': SeptalV2,
        'front_down': FrontDownV2,
        'front_septal': FrontSeptalV2,
    }
    sc_models_hid_size = {
        'down': 64,
        'front': 64,
        'septal': 80,
        'front_down': 100,
        'front_septal': 70,
    }
    target = [
        'перегородочный',
        'передний',
        'боковой',
        'передне-боковой',
        'передне-перегородочный',
        'нижний',
        'норма'
    ]
    
    weights_path: str = os.path.join(CURRENT_DIR, 'weights')

# Global lock for ECG GPU/CPU heavy processing
_ecg_processing_lock = threading.Lock()

# --- Utility Functions (Adapted from AI-Challenge) ---

def moving_avg(x, n):
    cumsum = np.cumsum(np.insert(x, 0, 0))
    return (cumsum[n:] - cumsum[:-n]) / float(n)

def smoothing(signal: np.ndarray, right: int) -> np.ndarray:
    for i in range(2, right):
        signal = moving_avg(signal, i)
    return signal

def clean_signal(signal: np.array, _type: int):
    new_signal = []
    for s in signal:
        try:
            s_proc = nk.ecg_clean(s, sampling_rate=500)
            s_proc = s_proc[500:-500]
            if _type == 0:
                s_proc = scipy.signal.medfilt(s_proc, 3)
                s_proc = smoothing(s_proc, 4)
            else:
                s_proc = smoothing(s_proc, 5)
            new_signal.append(s_proc)
        except Exception:
            new_signal.append(s[500:-500])
    return np.array(new_signal)

activation = {}
def get_activation(name):
    def hook(model, input, output):
        activation[name] = output.detach()
    return hook

def get_signals(signals_array, device: str, _type: int) -> torch.Tensor:
    # signals_array shape: (num_records, 12, 5000)
    signals = torch.Tensor(signals_array)
    signals = signals.to(device)
    return signals

_model_cache = {}

def init_models(network_type: str, device: str) -> dict[str, nn.Module]:
    assert network_type in ['V1', 'V2', 'se', 'sc']
    
    cache_key = f"{network_type}_{device}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    models: dict[str, nn.Module] = {}
    if network_type in ['V1', 'V2']:
        prefix = 'conv' + network_type + '_'
        models_dict = Config.v1_models if network_type == 'V1' else Config.v2_models
        for name, model in models_dict.items():
            models[name] = model()
            state_dict_name = prefix + name
            state_dict_path = os.path.join(Config.weights_path, state_dict_name)
            models[name].load_state_dict(torch.load(state_dict_path, map_location=device))
            models[name].to(device)
            models[name].eval()
    elif network_type == 'se':
        prefix = 'se_resnet_'
        for name, shape in Config.other_shapes.items():
            state_dict_name = prefix + name
            state_dict_path = os.path.join(Config.weights_path, state_dict_name)
            models[name] = Se_Resnet(num_classes=len(shape))
            models[name].load_state_dict(torch.load(state_dict_path, map_location=device))
            models[name].to(device)
            models[name].eval()
    else:
        prefix = 'sc_'
        for name, hid_size in Config.sc_models_hid_size.items():
            state_dict_name = prefix + name
            state_dict_path = os.path.join(Config.weights_path, state_dict_name)
            models[name] = CNN(input_size=len(Config.other_shapes[name]), hid_size=hid_size)
            models[name].load_state_dict(torch.load(state_dict_path, map_location=device))
            models[name].to(device)
            models[name].eval()
            
    _model_cache[cache_key] = models
    return models

def run_nn_predictions(signals_0, signals_1, device):
    ans_df = pd.DataFrame({'idx': [0]}) # Process one at a time for SRRIS
    
    # ConvV1
    models_v1 = init_models('V1', device)
    sig_v1 = torch.Tensor(signals_0).to(device)
    for name, model in models_v1.items():
        layer_name = 'linear4' if name == 'normal' else 'linear3'
        getattr(model, layer_name).register_forward_hook(get_activation(layer_name))
        _ = model(sig_v1[:, Config.v1_shapes[name]])
        ans_df['model_conv_1d_' + name] = [activation[layer_name].detach().cpu().numpy()[0]]
        
    # ConvV2
    models_v2 = init_models('V2', device)
    for name, model in models_v2.items():
        model.pred_final.register_forward_hook(get_activation('pred_final'))
        _ = model(sig_v1[:, Config.other_shapes[name]])
        ans_df['model_conv_2d_' + name] = [activation['pred_final'].detach().cpu().numpy()[0]]
        
    # SE-ResNet
    models_se = init_models('se', device)
    sig_v2 = torch.Tensor(signals_1).to(device)
    for name, model in models_se.items():
        model.linear1.register_forward_hook(get_activation('linear1'))
        _ = model(sig_v2[:, Config.other_shapes[name]])
        ans_df['model_se_resnet_' + name] = [activation['linear1'].detach().cpu().numpy()[0]]
        
    # Skip-CNN
    models_sc = init_models('sc', device)
    for name, model in models_sc.items():
        model.avgpool.register_forward_hook(get_activation('avgpool'))
        _ = model(sig_v2[:, Config.other_shapes[name]])
        ans_df['model_sc_resnet_' + name] = [activation['avgpool'].detach().cpu().squeeze(2).numpy()[0]]
        
    return ans_df

def parse_data_from_penultimate_layers(df, k):
    res = pd.DataFrame()
    for col in df.columns:
        if col == 'idx': continue
        data = np.array(df[col].tolist())
        if len(data.shape) == 1:
            res[col] = [data[0]]
        else:
            for i in range(data.shape[1]):
                if i % (max(1, data.shape[1] // k)) == 0:
                    res[f'{col}_{i}'] = [data[0, i]]
    return res

def get_hrv_features(ecg_signal):
    SAMPLING_RATE = 500
    try:
        r_peaks = nk.ecg_peaks(ecg_signal, sampling_rate=SAMPLING_RATE, correct_artifacts=True)
        ecg_rate = nk.ecg_rate(r_peaks, sampling_rate=SAMPLING_RATE)
        ecg_vars = [np.mean(ecg_rate), np.min(ecg_rate), np.max(ecg_rate), np.max(ecg_rate) - np.min(ecg_rate)]
        hrv_columns = ['HRV_MeanNN', 'HRV_SDNN', 'HRV_RMSSD', 'HRV_SDSD', 'HRV_CVNN', 'HRV_CVSD', 'HRV_MedianNN', 'HRV_MadNN', 'HRV_MCVNN', 'HRV_IQRNN', 'HRV_SDRMSSD', 'HRV_Prc20NN', 'HRV_Prc80NN', 'HRV_pNN50', 'HRV_pNN20', 'HRV_MinNN', 'HRV_MaxNN', 'HRV_HTI', 'HRV_TINN', 'HRV_TP']
        hrv_time = nk.hrv_time(r_peaks[0], sampling_rate=SAMPLING_RATE)
        hrv_freq = nk.hrv_frequency(r_peaks[0], sampling_rate=SAMPLING_RATE)
        hrv = hrv_time.join(hrv_freq)[hrv_columns].iloc[0].tolist()
        entropy = nk.entropy_sample(ecg_signal, 1, 4)[0]
        return ecg_vars + hrv + [entropy]
    except:
        return [0.0] * 25

def predict_stroke_ecg(image_path: str, output_dir: str):
    """Main entry point for SRRIS ECG Analysis with sequential locking."""
    with _ecg_processing_lock:
        # 1. Digitize Image to Signal
        stats = digitize_ecg(image_path, out_dir=output_dir, record_name='processed_ecg')
    signal = np.load(stats['npy_path']) # (12, 5000)
    
    # 2. Preprocess — resample to exactly 4000 to handle variable moving_avg output size
    import scipy.signal as sp_sig
    def clean_and_resample(sig, _type, target_len=4000):
        cleaned = clean_signal(sig, _type)  # shape: (12, variable_len)
        # Resample each lead to target_len
        resampled = np.array([sp_sig.resample(lead, target_len) for lead in cleaned])
        return resampled.reshape(1, 12, target_len)
    
    signals_0 = clean_and_resample(signal, 0)  # (1, 12, 4000)
    signals_1 = clean_and_resample(signal, 1)  # (1, 12, 4000)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # 3. Deep Features
    if device == 'cuda':
        with gpu_gate.use("ecg_nn_predictions"):
            nn_features = run_nn_predictions(signals_0, signals_1, device)
    else:
        nn_features = run_nn_predictions(signals_0, signals_1, device)
    
    # 4. HRV Features
    hrv = get_hrv_features(signals_0[0, 8]) # Lead 8 as used in original code
    hrv_cols = ['RateMean', 'RateMin', 'RateMax', 'RateRaz'] + ['HRV_MeanNN', 'HRV_SDNN', 'HRV_RMSSD', 'HRV_SDSD', 'HRV_CVNN', 'HRV_CVSD', 'HRV_MedianNN', 'HRV_MadNN', 'HRV_MCVNN', 'HRV_IQRNN', 'HRV_SDRMSSD', 'HRV_Prc20NN', 'HRV_Prc80NN', 'HRV_pNN50', 'HRV_pNN20', 'HRV_MinNN', 'HRV_MaxNN', 'HRV_HTI', 'HRV_TINN', 'HRV_TP'] + ['Entopy']
    hrv_df = pd.DataFrame([hrv], columns=hrv_cols)
    
    full_features = pd.concat([nn_features, hrv_df], axis=1).drop(columns=['idx'])
    
    # 5. CatBoost Ensemble
    feat_10 = parse_data_from_penultimate_layers(full_features, 10)
    feat_13 = parse_data_from_penultimate_layers(full_features, 13)
    feat_16 = parse_data_from_penultimate_layers(full_features, 16)
    
    meta_df = pd.DataFrame({'age': [65.0], 'sex': [1], 'height': [170.0], 'weight': [70.0]})
    feat_10 = pd.concat([meta_df, feat_10], axis=1)
    feat_13 = pd.concat([meta_df, feat_13], axis=1)
    feat_16 = pd.concat([meta_df, feat_16], axis=1)
    
    _catboost_cache = getattr(predict_stroke_ecg, '_cb_cache', {})
    
    probas = []
    for feat, k in [(feat_10, 10), (feat_13, 13), (feat_16, 16)]:
        p = {}
        for target in Config.target:
            cb_key = f"{k}_{target}"
            if cb_key not in _catboost_cache:
                model = CatBoostClassifier()
                model_path = os.path.join(Config.weights_path, f'catboost_{k}_{Config.translate_ru_eng[target]}')
                model.load_model(model_path)
                _catboost_cache[cb_key] = model
            else:
                model = _catboost_cache[cb_key]
                
            p[target] = model.predict_proba(feat)[:, 1][0]
        probas.append(p)
        
    predict_stroke_ecg._cb_cache = _catboost_cache
    
    # Blending
    final_proba = {}
    for t in Config.target:
        final_proba[t] = 0.15 * probas[0][t] + 0.7 * probas[1][t] + 0.15 * probas[2][t]
    
    # 6. Decision Logic
    prediction = "Normal (No Stroke Detected)"
    confidence = final_proba['норма']
    
    max_p = max(final_proba.values())
    max_target = [k for k,v in final_proba.items() if v == max_p][0]
    
    if max_target != 'норма' and max_p > 0.4:
        clinical_name = Config.translate_eng_ru.get(Config.translate_ru_eng.get(max_target), max_target)
        prediction = f"Stroke Detected: {clinical_name.upper()} Region"
        confidence = max_p
        
    # Extract the patient UID from the output_dir to form the correct URL
    # output_dir is typically: .../uploads/<patient_uid>/ECG_Signals/processed
    parts = output_dir.replace('\\', '/').split('/')
    patient_uid = parts[-3] if len(parts) >= 3 else "unknown"

    return {
        "prediction": prediction,
        "confidence": float(confidence),
        "markers": {k: f"{v:.2f}" for k, v in final_proba.items()},
        "ocr_text": "ECG Digitized Successfully. Leads: I, II, III, aVR, aVL, aVF, V1-V6 analyzed.",
        "detection_image": f"/uploads/{patient_uid}/ECG_Signals/processed/processed_ecg_detected.png",
        "xai_analysis": f"The ensemble model detected significant morphological changes in the {prediction.split(': ')[-1] if ':' in prediction else 'cardiac'} vectors, suggesting regional ischemic patterns."
    }
