# Flamma: current models and training results

Prepared for adviser review — 22 October 2026 (Asia/Manila). Source: the local project at C:\flamma chatbot. Text benchmark scores below were rerun for this report; historical training results and checkpoint values are explicitly identified.

## Summary for presentation

Flamma is an English-first educational skin-information and screening prototype. Its configured text pipeline uses pretrained all-MiniLM-L6-v2 sentence embeddings and a trained logistic-regression intent classifier (v5). Conversation rules and a curated knowledge library produce replies. A separate ResNet-50 image service screens six supported classes and produces Grad-CAM heatmaps.

The active-by-manifest text classifier scored 123/130 (94.62%) with macro F1 0.9478 on the reused authored text-intent benchmark. The configured image checkpoint is v10-1; its test_accuracy is null. Only the archived image v3 checkpoint stores a test accuracy (95.19%), which must be attributed to v3.

At the initial local health check during this review, neither port 5000 nor port 8000 accepted a connection. Model selection below is verified from files and checksums; a live service model identity was not observed. No services were started and no models were retrained.

## 1. Complete saved text-model inventory and fresh benchmark

| Artifact | Selection | Correct / 130 | Accuracy | Macro F1 |
| --- | --- | --- | --- | --- |
| semantic_classifier.pkl | Archived | 80 | 61.54% | 0.5754 |
| semantic_classifier_balanced.pkl | Archived | 97 | 74.62% | 0.7273 |
| semantic_classifier_balanced_v2.pkl | Archived | 107 | 82.31% | 0.7905 |
| intent_v3.pkl | Archived | 119 | 91.54% | 0.9081 |
| intent_v4.pkl | Archived | 120 | 92.31% | 0.9259 |
| intent_v5.pkl | Configured active | 123 | 94.62% | 0.9478 |

All six artifacts are logistic-regression classifiers with 384 input features and 13 output categories. The original classifier has no class weighting; the other five use class_weight=balanced. The two balanced legacy artifacts have no accompanying saved training metadata in this checkout; their numbers above are fresh evaluation results, not recovered training scores. Full parameters, iterations, hashes, predictions, and confusion matrices are in model-audit.json.

The MiniLM sentence encoder is pretrained and is not fine-tuned by this project training pipeline. It generates normalized sentence vectors. There is no evidence here of a locally trained generative language model.

## 2. Saved training and validation results

| Version | Training completed (Manila) | Unique examples | Split: train / validation | Validation accuracy | Validation macro F1 | Saved benchmark accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| intent_v3 | 2026-10-14 12:55 | 5401 | 4293 / 1108 | 97.56% | 0.9436 | 91.54% |
| intent_v4 | 2026-10-14 21:50 | 5881 | 4705 / 1176 | 97.28% | 0.9580 | 92.31% |
| intent_v5 | 2026-10-16 01:37 | 6405 | 5110 / 1295 | 98.30% | 0.9664 | 94.62% |

Validation uses fold 0 of a five-way StratifiedGroupKFold split with seed 42 and no overlapping template groups recorded. These are single-fold results, not five-fold averages. Grouping logic evolved between versions, so validation rows are not identical evaluation sets. C values 0.5, 1.0, and 2.0 were compared; each version selected C=2.0 by validation macro F1. The selected classifier was then refit on all unique examples. Training uses max_iter=2000, balanced class weights, and random_state=42. Logistic-regression iterations are not neural-network training epochs.

| Version | C | Validation accuracy | Validation macro F1 |
| --- | --- | --- | --- |
| intent_v3 | 0.5 | 96.57% | 0.9274 |
| intent_v3 | 1.0 | 96.93% | 0.9369 |
| intent_v3 | 2.0 | 97.56% | 0.9436 |
| intent_v4 | 0.5 | 96.43% | 0.9460 |
| intent_v4 | 1.0 | 96.77% | 0.9491 |
| intent_v4 | 2.0 | 97.28% | 0.9580 |
| intent_v5 | 0.5 | 97.76% | 0.9561 |
| intent_v5 | 1.0 | 98.07% | 0.9607 |
| intent_v5 | 2.0 | 98.30% | 0.9664 |

v5 training recorded 6,484 input examples, 6,405 unique examples, 79 removed duplicates, no conflicting labels, and 1,918 template groups. The parameter-selection split contained 5,110 training and 1,295 validation examples. Its four sources are intents.json, training_supplement.json, english_location_supplement.json, and english_intent_supplement.json. v4 added 480 location examples over v3; v5 added 524 broader intent examples over v4.

All recorded source checksum comparisons passed: True. Reprocessing the current v5 sources yields 6,405 unique examples. Saved chats and photos were not training sources in these reports. The corpus contains authored fictional examples; its size does not represent patient counts. Class weighting addresses unequal class counts without making the dataset numerically balanced.

Training runtime recorded for v5: Python 3.14.4; scikit-learn 1.9.1; sentence-transformers 6.1.0; torch 2.14.0; numpy 2.5.3.

## 3. Active v5 results by intent

| Intent | Training examples | Test messages | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| bot_identity | 108 | 10 | 1.0000 | 1.0000 | 1.0000 |
| confirmation | 144 | 10 | 1.0000 | 1.0000 | 1.0000 |
| duration | 463 | 10 | 1.0000 | 0.9000 | 0.9474 |
| emergency | 196 | 10 | 1.0000 | 1.0000 | 1.0000 |
| goodbye | 134 | 10 | 1.0000 | 1.0000 | 1.0000 |
| greeting | 110 | 10 | 1.0000 | 1.0000 | 1.0000 |
| image_upload | 162 | 10 | 1.0000 | 0.7000 | 0.8235 |
| location | 1022 | 10 | 0.6429 | 0.9000 | 0.7500 |
| medication | 501 | 10 | 1.0000 | 1.0000 | 1.0000 |
| severity | 195 | 10 | 1.0000 | 1.0000 | 1.0000 |
| symptom | 3096 | 10 | 0.8000 | 0.8000 | 0.8000 |
| thanks | 125 | 10 | 1.0000 | 1.0000 | 1.0000 |
| unknown | 149 | 10 | 1.0000 | 1.0000 | 1.0000 |

Macro F1 gives each intent equal weight. Accuracy counts the fraction of correctly categorized messages. The 130-message benchmark contains ten examples per intent. It was excluded from fitting but has been reused across development versions, so it is not an untouched independent final test.

### Incorrect v5 benchmark predictions

| Authored message | Expected | Predicted |
| --- | --- | --- |
| there is an irritated patch that keeps itching | symptom | location |
| I've noticed some new irritated areas | symptom | location |
| the skin issue appears near my right shoulder | location | symptom |
| the irritation has been present for several days | duration | symptom |
| I've attached a picture of the affected skin | image_upload | location |
| here is an image showing the skin problem | image_upload | location |
| I uploaded an image showing the affected spot | image_upload | location |

## 4. Other saved text and conversation evaluations

Additional authored intent comparison: v4 96.92% (63/65), v5 100.00% (65/65), with v5 macro F1 1.0000. The saved report records zero exact training overlap and zero template-group overlap. This small authored set remains an engineering evaluation.

| Saved result file | Scenarios | Passed / turns | Interpretation |
| --- | --- | --- | --- |
| course-core-conversations.json | 19 | 68/68 | Authored conversation regression |
| course-all-followups.json | 87 | 221/221 | Authored conversation regression |
| course-questions-after.json | 5 | 11/11 | Authored conversation regression |

These are saved results from 16 October 2026 by local file timestamps, not fresh runs for this report. Some scenarios overlap across suites; their counts must not be added as independent samples. They measure specified conversation behavior, not image recognition or medical correctness. model-audit.json indexes every saved evaluation JSON in eval/results, including historical before/after reports.

## 5. Complete image-model inventory

| Checkpoint | Selection in source | Classes | Saved test accuracy | Outlier exposure |
| --- | --- | --- | --- | --- |
| resnet50_skin_disease_classification_v10-1_oe.pth | Configured active | 6 | Unavailable | Yes |
| resnet50_skin_disease_classification_v10_oe.pth | Archived | 6 | Unavailable | Yes |
| resnet50_skin_disease_classification_v11c_oe.pth | Archived | 6 | Unavailable | Yes |
| resnet50_skin_disease_classification_v3_oe.pth | Archived | 6 | 95.19% | Yes |

All four checkpoints identify architecture=resnet50 and the same six classes: atopic dermatitis, contact dermatitis, lichen planus, normal skin, psoriasis, and rosacea. The final linear layer has 2,048 inputs and six outputs. The newer filename v11c is present but is not selected by inference/classifier.py.

The archived v3 checkpoint stores test_accuracy=0.9519230769230769 (95.19%). No test sample count, test-set definition, per-class report, confusion matrix, optimizer settings, epoch history, or training/validation curves are included in these checkpoints. No image dataset or image-training notebook was found in the project folders inspected. A 2,400-image dataset is mentioned in a skin-filter source comment, but its size and split cannot be verified from local data. No new image accuracy was measured for this report.

Each checkpoint records outlier exposure and 12 auxiliary category names. Those auxiliary categories are not additional supported diagnostic classes. The names are preserved in model-audit.json.

### Configured image pipeline

| Setting | Verified value |
| --- | --- |
| Input | RGB, resized to 224 x 224 |
| Normalization mean | 0.485, 0.456, 0.406 |
| Normalization standard deviation | 0.229, 0.224, 0.225 |
| Skin-content prefilter | YCrCb OR HSV color heuristic; minimum skin-like pixel ratio 0.15 |
| OOD score | Entropy; reject when score > 0.9399791955947876 |
| OOD target_tpr setting | 0.95 (configuration target, not an observed result in this review) |
| Confidence threshold | 0.55 |
| Explanation | Grad-CAM on ResNet layer4[-1] |

The color filter and OOD/confidence gates are screening mechanisms. Their thresholds do not establish measured sensitivity, specificity, clinical calibration, or the ability to rule out unsupported disease. The OOD configuration does not identify which checkpoint it was calibrated against; calibration correspondence with v10-1 cannot be verified here.

## 6. Legacy and supporting components

| Component | Current evidence |
| --- | --- |
| Custom bag-of-words neural network | model_weights.json contains 636 inputs, 8 hidden neurons, and 10 output neurons. train.py requests 1,000 epochs with SGD learning rate 0.01 and cross-entropy; no saved actual epoch/loss history or accuracy is present. It is not used by the current SemanticChatbot app path. |
| Embedding cache | Three NPZ training-embedding caches are present; these are intermediate vectors, not additional trained classifiers. |
| Conversation and knowledge layer | Rules, context tracking, warning checks, and curated JSON information. They are software/knowledge components rather than independently trained models. |
| Optional Gemini endpoint | Image backend includes a separate optional /api/chat endpoint. The current Flamma chat interface uses the local semantic chatbot; Gemini is not part of the local training results. |

## 7. Evidence files and remaining results to obtain

Primary evidence: Flamma/artifacts/active_intent_model.json; Flamma/artifacts/intent_v3.metadata.json; intent_v4.metadata.json; intent_v5.metadata.json; Flamma/eval/results; Image/thesis-backend/inference/classifier.py; Image/thesis-backend/models/*.pth; Image/thesis-backend/models/ood_config.json; and Flamma/DEFENSE_NOTES.md.

To report complete image training results, obtain the original image-training notebook, dataset provenance and counts by class, patient/source-level splits, preprocessing and augmentation settings, optimizer and learning-rate schedule, actual epoch logs, checkpoint selection rule, independent test labels, per-class precision/recall/F1, confusion matrix, and OOD calibration/evaluation evidence. An independently authored text test is also needed for a stronger final generalization claim.

Suggested adviser statement: "Our active v5 text-intent classifier was trained on 6,405 unique fictional English examples across 13 intents. It achieved 98.30% accuracy and 0.9664 macro F1 on one grouped validation fold, and 94.62% accuracy with 0.9478 macro F1 on a reused 130-message benchmark. The configured image classifier is ResNet-50 v10-1 with six output classes; its checkpoint does not include test accuracy. Archived image v3 stores 95.19%, which we attribute only to v3. These are prototype engineering results, not established clinical diagnostic accuracy."

## 8. Reproduce this report

From C:\flamma chatbot, run: .\Flamma\venv\Scripts\python.exe -B reports\2026-10-22\build_report.py. This reads local checkpoints, evaluates authored text cases with cached MiniLM embeddings, checks recorded checksums, and rewrites the report artifacts. It does not train or activate a model.

Companion files: model-audit.json (complete extracted model evidence and saved evaluation index); text-model-comparison.csv; image-model-comparison.csv; active-model-per-intent.csv; active-model-predictions.csv; active-model-confusion-matrix.csv. The HTML version is self-contained and can be printed or saved to PDF from a browser.
