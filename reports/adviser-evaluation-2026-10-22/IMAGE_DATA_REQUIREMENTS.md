# Pending: active v10-1 held-out image evaluation

No held-out image dataset or split provenance is confirmed. No image test accuracy has been measured in this evaluation.

Provide original, labeled test images and a CSV with columns:

`image_path,label,split,subject_id,source_id`

Use relative paths under a dataset root. Labels: atopic_dermatitis, contact_dermatitis, lichen_planus, normal_skin, psoriasis, rosacea, or unsupported. Set split=test. Supply patient IDs where available and an acquisition/source grouping ID that permits meaningful leakage checks; a broad website name alone is not sufficient. Include all six supported diseases and independently labeled unsupported images. Preserve consent and de-identification. Do not substitute generated images for a diagnostic test set.

Also provide a provenance JSON describing dataset origins, consent, annotation, sample counts, split dates, patient/source grouping, augmentation and deduplication. It must truthfully declare test_frozen_before_model_selection=true and not_used_for_training_or_calibration=true. Include a training manifest for content and supplied subject/source overlap checks. Declarations alone do not prove independence.

Run from the workspace root:

```powershell
.\Flamma\venv\Scripts\python.exe -B Flamma\eval\adviser\evaluate_images.py --manifest "C:\dataset\test.csv" --dataset-root "C:\dataset" --split-provenance "C:\dataset\provenance.json" --training-manifest "C:\dataset\train.csv" --output reports\adviser-evaluation-2026-10-22\image-heldout-results.json
```

Outputs include raw accuracy, precision, recall, macro F1, confusion matrix and per-disease results; gate coverage and per-class rejections; accepted-only metrics; correct accepted predictions divided by all supported images; unsupported rejection; and CPU inference timing. Accepted-only accuracy must always be presented alongside coverage. This does not include Grad-CAM/HTTP latency or establish clinical validation.
