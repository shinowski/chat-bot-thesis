# ============================================================
# CONDITION METADATA
# ============================================================
# Maps the classifier's raw class names to frontend-facing content:
# display name, short description, and the three "Prediction
# Breakdown" sections (summary / why this result / recommendations).
#
# IMPORTANT: the "why" text intentionally does NOT claim the model
# identified specific named clinical features (e.g. "silvery scales,"
# "purplish bumps"). The classifier is an end-to-end CNN trained on
# image-label pairs — it never learned discrete, named clinical
# features as separate concepts. It only learned statistical pixel
# patterns (color, texture, structure) that happened to correlate
# with each class label during training. Grad-CAM shows WHERE the
# model looked, not WHAT clinical feature it "recognized" there.
# Describing outputs in named-feature language overstates what the
# model actually does and should be avoided throughout this app and
# any thesis writeup.
#
# NOTE: descriptions here are placeholder clinical copy (from
# general medical knowledge, not model output) — have them reviewed
# before this goes anywhere near real users.

CONDITION_INFO = {
    "atopic_dermatitis": {
        "display_name": "Atopic Dermatitis",
        "description": (
            "A chronic inflammatory skin condition that commonly causes "
            "dryness, itching, redness, and irritated patches. It often "
            "appears on areas such as the face, hands, elbows, and knees "
            "and may flare periodically."
        ),
        "summary": (
            "The image was classified as Atopic Dermatitis based on "
            "overall visual similarity to atopic dermatitis images in "
            "the model's training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of atopic dermatitis it was trained on. This reflects "
            "overall color, texture, and structural similarity across "
            "the image — the model does not identify or name specific "
            "clinical features, only statistical patterns."
        ),
        "recommendations": (
            "Consider using fragrance-free moisturizers, avoiding known "
            "triggers such as harsh soaps or extreme temperatures, and "
            "scheduling a visit with a dermatologist to confirm the "
            "diagnosis and discuss treatment options."
        ),
    },

    "contact_dermatitis": {
        "display_name": "Contact Dermatitis",
        "description": (
            "An inflammatory skin reaction that can occur after contact "
            "with an irritating substance or an allergen. It may cause "
            "redness, itching, swelling, dryness, or a rash in the area "
            "that was exposed."
        ),
        "summary": (
            "The image was classified as Contact Dermatitis based on "
            "overall visual similarity to contact dermatitis images in "
            "the model's training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of contact dermatitis it was trained on. This reflects "
            "overall color, texture, and structural similarity, the "
            "model does not identify or name specific clinical features, "
            "only statistical patterns."
        ),
        "recommendations": (
            "Try to identify and avoid the substance that may have "
            "triggered the reaction, keep the area clean and moisturized, "
            "and see a dermatologist if the irritation persists or worsens."
        ),
    },

    "lichen_planus": {
        "display_name": "Lichen Planus",
        "description": (
            "An inflammatory skin condition that can cause itchy, "
            "purplish, flat-topped bumps or patches. It commonly affects "
            "the wrists, ankles, lower back, and other areas of the skin."
        ),
        "summary": (
            "The image was classified as Lichen Planus based on overall "
            "visual similarity to lichen planus images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of lichen planus it was trained on. This reflects overall "
            "color, texture, and structural similarity, the model does "
            "not identify or name specific clinical features, only "
            "statistical patterns."
        ),
        "recommendations": (
            "Avoid scratching the affected area, note whether the "
            "patches spread or change over time, and consult a "
            "dermatologist for confirmation and treatment options."
        ),
    },

    "psoriasis": {
        "display_name": "Psoriasis",
        "description": (
            "A chronic inflammatory skin condition that causes areas of "
            "the skin to become red, thickened, and covered with "
            "silvery-white scales. It commonly affects the elbows, knees, "
            "scalp, and other areas, although it can occur elsewhere."
        ),
        "summary": (
            "The image was classified as Psoriasis based on overall "
            "visual similarity to psoriasis images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of psoriasis it was trained on. This reflects overall "
            "color, texture, and structural similarity, the model does "
            "not identify or name specific clinical features (such as "
            "plaque type or scale texture), only statistical patterns "
            "learned from the training images available to it."
        ),
        "recommendations": (
            "Moisturize regularly, avoid known triggers such as stress "
            "and skin trauma, and schedule a visit with a dermatologist "
            "to confirm the diagnosis and discuss treatment options."
        ),
    },

    "rosacea": {
        "display_name": "Rosacea",
        "description": (
            "A chronic skin condition that commonly affects the face and "
            "may cause persistent redness, flushing, visible blood vessels, "
            "and sometimes small red bumps or pustules. Symptoms may become "
            "more noticeable after certain triggers."
        ),
        "summary": (
            "The image was classified as Rosacea based on overall "
            "visual similarity to rosacea images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of rosacea it was trained on. This reflects overall color, "
            "texture, and structural similarity, the model does not "
            "identify or name specific clinical features, only "
            "statistical patterns."
        ),
        "recommendations": (
            "Identify and avoid common triggers such as sun exposure, "
            "spicy food, or alcohol, use gentle skincare products, and "
            "consult a dermatologist for confirmation and treatment "
            "options."
        ),
    },

    "normal_skin": {
        "display_name": "No Condition Detected",
        "description": (
            "The image does not show clear visual characteristics matching "
            "the skin conditions included in this tool's screening scope. "
            "This result does not confirm that the skin is completely "
            "healthy or rule out other conditions. If you have persistent "
            "or concerning symptoms, consult a qualified healthcare "
            "professional."
        ),
        "summary": (
            "The image's overall visual pattern was most similar to the "
            "healthy/normal skin images in the model's training data, "
            "rather than any of the conditions it screens for."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of normal, unaffected skin rather than any of the "
            "conditions in its training data. This is a pattern match, "
            "not a clinical clearance."
        ),
        "recommendations": (
            "If you have no symptoms, no action is needed. If you have "
            "concerns about your skin that aren't reflected here, "
            "consult a dermatologist directly rather than relying on "
            "this result."
        ),
    },
}